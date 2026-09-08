"""V3 photo submission: server-validated images, no raw image retention or fake AI success."""

from __future__ import annotations

import io
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from tortoise.transactions import in_transaction

from app.core import config
from app.models.health import Challenge, ChallengeCycle, ChallengeLog, ChallengeVerification, UserChallenge
from app.services.challenge_catalog import metadata_for
from app.vision.food_vision import FoodVisionError, get_food_vision_provider, sha256_digest


def challenge_today():
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


async def sanitized_photo(file: UploadFile) -> bytes:
    try:
        raw = await file.read(config.FOOD_PHOTO_MAX_BYTES + 1)
    finally:
        await file.close()
    if not raw or len(raw) > config.FOOD_PHOTO_MAX_BYTES:
        raise HTTPException(status_code=422, detail="사진은 비어 있지 않은 8MB 이하 파일이어야 합니다.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 12_000_000:
                raise HTTPException(status_code=422, detail="1200만 화소 이하 JPG·PNG·WEBP 사진을 사용해 주세요.")
            image.load()
            clean = image.convert("RGB")
            clean.thumbnail((1600, 1600))
            output = io.BytesIO()
            clean.save(output, format="JPEG", quality=85)
            return output.getvalue()  # EXIF/location and the original filename are not sent or retained.
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=422, detail="읽을 수 있는 사진 파일이 아닙니다.") from exc


async def _context(service, user, selected_id, proof_date, *, for_update=False):
    # Lock an existing parent row so simultaneous first submissions cannot both
    # create a proof, and a late rejected review cannot overwrite an acceptance.
    if for_update:
        selected = await UserChallenge.filter(id=selected_id, user_id=user.id).select_for_update().first()
    else:
        selected = await service.repo.get_user_challenge(selected_id, user.id)
    if selected is None:
        raise HTTPException(status_code=404, detail="선택한 챌린지를 찾을 수 없습니다.")
    if for_update:
        cycle = await ChallengeCycle.filter(id=selected.cycle_id, user_id=user.id).select_for_update().first()
    else:
        cycle = await service.repo.get_cycle(selected.cycle_id, user.id)
    await service._v3_health_permission(user)
    if cycle is None or cycle.status not in {"active", "scheduled"}:
        raise HTTPException(status_code=409, detail="진행 중인 챌린지가 아닙니다.")
    if not cycle.start_date <= proof_date <= min(cycle.end_date, challenge_today()):
        raise HTTPException(status_code=422, detail="챌린지 기간 안의 오늘 또는 과거 날짜만 기록할 수 있습니다.")
    challenge = await Challenge.get(id=selected.challenge_id)
    metadata = metadata_for(challenge.code)
    if not metadata or metadata["verification_type"] not in {1, 2}:
        raise HTTPException(status_code=422, detail="사진 제출형 챌린지가 아닙니다.")
    return metadata


async def _review(photo: bytes, verification_type: int) -> tuple[str, str]:
    if verification_type == 2:
        return "accepted", "사진 제출을 확인했습니다. 활동 시간·섭취량은 본인 기록이며 AI 검증이 아닙니다."
    if config.FOOD_VISION_PROVIDER != "openai" or not config.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503, detail="사진 검토 서비스가 연결되지 않았습니다. 완료로 처리하지 않았습니다."
        )
    try:
        provider = get_food_vision_provider()
        if provider.provider_kind != "openai_vision":
            raise FoodVisionError("A real image-review provider is required")
        result = await provider.analyze(photo, "image/jpeg", "challenge.jpg")
        if result.provider_kind != "openai_vision":
            raise FoodVisionError("The image-review result is not from a real provider")
    except FoodVisionError as exc:
        raise HTTPException(
            status_code=502, detail="사진 검토에 실패했습니다. 완료되지 않았으니 다시 시도해 주세요."
        ) from exc
    accepted = (
        result.contains_vegetable is True
        and type(result.vegetable_confidence) in (int, float)
        and 0.5 <= result.vegetable_confidence <= 1
        and math.isfinite(result.vegetable_confidence)
    )
    return (
        "accepted" if accepted else "needs_review",
        "대표 사진의 채소 포함을 확인했습니다. 끼니 수·섭취량은 본인 기록입니다."
        if accepted
        else "사진의 채소 포함 여부를 확인하지 못했습니다. 완료로 처리하지 않았습니다.",
    )


async def _accepted_submission(user_id, selected_id, proof_date):
    existing = await ChallengeVerification.get_or_none(
        user_id=user_id, user_challenge_id=selected_id, verification_date=proof_date
    )
    log = await ChallengeLog.get_or_none(user_id=user_id, user_challenge_id=selected_id, log_date=proof_date)
    if existing and log and log.is_completed and existing.review_status == "accepted":
        return {
            "challenge_completed": True,
            "review_status": "accepted",
            "already_recorded": True,
            "verification_id": existing.id,
            "notice": "이미 저장된 인증입니다. 보상을 추가 지급하지 않습니다.",
        }
    return None


async def verify_photo(service, user, selected_id, proof_date, file, actual_value):
    metadata = await _context(service, user, selected_id, proof_date)
    target = metadata["goal"]["target_minutes"] or metadata["goal"]["target_count"]
    if not math.isfinite(actual_value) or actual_value < target:
        raise HTTPException(status_code=422, detail=f"실제 실천량을 입력해 주세요. 완료 목표는 {target}입니다.")
    photo = await sanitized_photo(file)
    digest = sha256_digest(photo)
    try:
        existing = await _accepted_submission(user.id, selected_id, proof_date)
        if existing is not None:
            return existing
        review_status, notice = await _review(photo, metadata["verification_type"])
    finally:
        del photo
    completed = review_status == "accepted"
    async with in_transaction():
        # The external review can take time. Honor any consent, eligibility or
        # cycle changes before recording its result, then preserve a concurrent
        # successful submission without changing its evidence or quantity.
        await _context(service, user, selected_id, proof_date, for_update=True)
        existing = await _accepted_submission(user.id, selected_id, proof_date)
        if existing is not None:
            return existing
        verification = await service.repo.upsert_verification(
            user_challenge_id=selected_id,
            user_id=user.id,
            verification_date=proof_date,
            values={
                "verification_type": "photo",
                "evidence_digest": digest,
                "evidence_ref": "v3:server-photo",
                "review_status": review_status,
            },
        )
        await service.repo.record_verification_event(verification)
        if completed:
            await service.repo.upsert_log(
                user_challenge_id=selected_id,
                user_id=user.id,
                log_date=proof_date,
                values={
                    "is_completed": True,
                    "value": actual_value,
                    "source": "photo_v3",
                    "note": f"evidence-v3 type{metadata['verification_type']}; quantity self-reported",
                },
            )
    return {
        "verification_id": verification.id,
        "challenge_completed": completed,
        "review_status": review_status,
        "already_recorded": False,
        "notice": notice,
    }
