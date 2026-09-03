"""Private local evidence; no OCR, URL fetching or external AI transmission."""

import hashlib
import io
import warnings
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from tortoise.transactions import in_transaction

from app.core import config
from app.models.challenge_v2 import ChallengeV2Review as Review
from app.services.challenge_v2 import (
    Assignment,
    Day,
    Evidence,
    Session,
    aggregate,
    day_payload,
    locked_user,
    now_kst,
    owned_assignment,
    preferences,
    require_enabled,
    review_available,
)
from app.services.challenge_v2_catalog import eligible

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 16_000_000
FORMATS = {"JPEG": ("image/jpeg", {".jpg", ".jpeg"}), "PNG": ("image/png", {".png"}), "WEBP": ("image/webp", {".webp"})}


def sanitize_photo(raw: bytes, filename: str, content_type: str):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "사진은 10MB 이하로 올려 주세요.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                spec = FORMATS.get(image.format)
                if not spec or spec[0] != content_type or Path(filename).suffix.lower() not in spec[1]:
                    raise ValueError("format")
                if image.width * image.height > MAX_PIXELS or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("dimensions")
                image.load()
                # Hash decoded, oriented pixels, not caller filenames/EXIF. Persist no metadata.
                pixels = ImageOps.exif_transpose(image).convert("RGB")
                digest = hashlib.sha256(str(pixels.size).encode() + pixels.tobytes()).hexdigest()
                pixels.thumbnail((2400, 2400))
                clean = Image.new("RGB", pixels.size)
                clean.paste(pixels)
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=88)
                return output.getvalue(), digest
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(422, "유효한 단일 JPEG·PNG·WebP 사진(1,600만 픽셀 이하)을 선택해 주세요.") from exc


async def upload(user, assignment_id, index, raw, filename, content_type):
    require_enabled()
    clean, digest = sanitize_photo(raw, filename, content_type)
    async with in_transaction():
        await locked_user(user.id)
        item, day = await owned_assignment(user.id, assignment_id)
        pref = await preferences(user.id)
        if not pref.photo_consent or not pref.photo_accessible:
            raise HTTPException(403, "사진 보관 동의와 촬영 가능 확인이 필요합니다. 체크형 대안도 선택할 수 있습니다.")
        if not eligible(item.goal, pref, await review_available()):
            raise HTTPException(409, "현재 조건에서 사진을 접수할 수 없습니다. 대체 카드를 선택해 주세요.")
        if not 1 <= index <= item.goal["required_uploads"]:
            raise HTTPException(422, "이 카드에 필요한 인증 회차가 아닙니다.")
        old = await Evidence.get_or_none(assignment_id=item.id, evidence_index=index)
        if old and old.content_hash == digest and old.content is not None:
            return await day_payload(day)
        if item.status == "completed" or (old and old.verification_status == "passed"):
            raise HTTPException(409, "완료된 인증은 바꿀 수 없습니다.")
        if await Evidence.filter(day_id=day.id, content_hash=digest).exclude(id=old.id if old else -1).exists():
            raise HTTPException(409, "같은 날짜의 다른 회차·슬롯에 이미 제출한 사진입니다.")
        await Evidence.update_or_create(
            assignment_id=item.id,
            evidence_index=index,
            defaults={
                "user_id": user.id,
                "day_id": day.id,
                "content_hash": digest,
                "content": clean,
                "deletion_due_at": now_kst() + timedelta(days=7),
                "submitted_at": now_kst(),
                "generation": old.generation + 1 if old else 1,
                "verification_status": "pending" if item.goal["proof_type"] == "T1" else "not_required",
            },
        )
        await aggregate(item, day, user)
        return await day_payload(day)


def is_reviewer(user):
    return user.is_active and user.is_admin and user.id in config.CHALLENGE_V2_REVIEWER_IDS


async def read_photo(user, evidence_id):
    require_enabled()
    item = await Evidence.get_or_none(id=evidence_id)
    if not item or (item.user_id != user.id and not is_reviewer(user)):
        raise HTTPException(404, "사진을 찾을 수 없습니다.")
    if not (await preferences(item.user_id)).photo_consent:
        raise HTTPException(410, "사진 동의가 철회되었습니다.")
    if item.deletion_due_at <= now_kst() or item.content is None:
        raise HTTPException(410, "사진 보관 기간이 만료되었습니다. 원본은 제공되지 않습니다.")
    return item.content


async def review_queue(user):
    require_enabled()
    if not is_reviewer(user):
        raise HTTPException(403, "지정된 검토 담당자만 접근할 수 있습니다.")
    result = []
    for proof in await Evidence.filter(verification_status="pending", deletion_due_at__gt=now_kst()).limit(50):
        item = await Assignment.get(id=proof.assignment_id)
        if item.status == "replaced" or proof.user_id == user.id or proof.content is None:
            continue
        result.append(
            {
                "evidence_id": proof.id,
                "assignment_id": item.id,
                "index": proof.evidence_index,
                "generation": proof.generation,
                "goal": item.goal,
                "sessions": await Session.filter(assignment_id=item.id).values("session_index", "values"),
                "notice": "보이는 조건·라벨 입력만 검토하세요. 실제 섭취·건강효과를 판정하지 않습니다.",
            }
        )
    return result


async def review_photo(reviewer, evidence_id, request):
    require_enabled()
    if not is_reviewer(reviewer):
        raise HTTPException(403, "지정된 검토 담당자만 판정할 수 있습니다.")
    proof = await Evidence.get_or_none(id=evidence_id)
    if not proof or proof.user_id == reviewer.id:
        raise HTTPException(404, "검토할 사진을 찾을 수 없습니다.")
    async with in_transaction():
        owner = await locked_user(proof.user_id)
        proof = await Evidence.get(id=proof.id)
        item = await Assignment.get(id=proof.assignment_id)
        day = await Day.get(id=item.day_id)
        if item.status == "replaced" or item.goal["proof_type"] != "T1":
            raise HTTPException(409, "현재 T1 사진만 검토할 수 있습니다.")
        if request.generation != proof.generation:
            raise HTTPException(409, "새 사진이 제출되었습니다. 최신 사진을 열어 다시 검토해 주세요.")
        if await Session.filter(assignment_id=item.id).count() != item.goal["target_sessions"]:
            raise HTTPException(409, "모든 회차 기록이 제출된 뒤 검토해 주세요.")
        await read_photo(reviewer, proof.id)
        old = await Review.get_or_none(evidence_id=proof.id, evidence_generation=proof.generation)
        if old:
            if (
                old.status == request.status
                and old.criteria_results == request.criteria_results
                and old.reason == request.reason
            ):
                return await day_payload(day)
            raise HTTPException(409, "이미 판정한 사진입니다. 재제출된 사진만 다시 판정합니다.")
        expected = set(item.goal["visual_criteria"])
        if set(request.criteria_results) != expected or (
            request.status == "passed" and not all(request.criteria_results.values())
        ):
            raise HTTPException(422, "명시된 모든 시각 조건을 기록해야 하며 통과는 모두 충족해야 합니다.")
        await Review.create(
            evidence_id=proof.id,
            evidence_generation=proof.generation,
            reviewer_id=reviewer.id,
            status=request.status,
            criteria_results=request.criteria_results,
            reason=request.reason,
        )
        proof.verification_status = request.status
        await proof.save()
        await aggregate(item, day, owner)
        return await day_payload(day)


async def purge_expired():
    """Erase bytes only; retain non-image audit and earned reward history."""
    expired = Evidence.filter(deletion_due_at__lte=now_kst()).exclude(content=None)
    await expired.filter(verification_status="pending").update(verification_status="inconclusive")
    count = await expired.update(content=None)
    ids = await Evidence.filter(content=None, verification_status="inconclusive").values_list(
        "assignment_id", flat=True
    )
    await (
        Assignment.filter(id__in=ids)
        .exclude(status__in=["completed", "replaced"])
        .update(verification_status="inconclusive")
    )
    return count
