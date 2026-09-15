"""Prepare checksum-pinned K-food model files from a public Google Drive blob."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core import config

_FILE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_MAX_BUNDLE_BYTES = 128 * 1024 * 1024
_MEMBERS = {
    "models/artifacts/food_vision/kfood/best.pt": ("best.pt", "KFOOD_CLASSIFIER_SHA256"),
    "models/artifacts/food_vision/kfood/meta.json": ("meta.json", "KFOOD_CLASSIFIER_META_SHA256"),
    "models/artifacts/food_vision/kfood/1.tflite": ("1.tflite", "KFOOD_SEGMENTER_SHA256"),
}


class KFoodBundleError(RuntimeError):
    """The configured food-vision bundle is unavailable or untrusted."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download(file_id: str, destination: Path) -> None:
    query = urlencode({"id": file_id, "export": "download", "confirm": "t"})
    request = Request(
        f"https://drive.usercontent.google.com/download?{query}",
        headers={"User-Agent": "AH05-model-bootstrap/1.0"},
    )
    try:
        with urlopen(request, timeout=config.KFOOD_BUNDLE_DOWNLOAD_TIMEOUT_SECONDS) as response:  # noqa: S310
            content_type = response.headers.get_content_type()
            if content_type == "text/html":
                raise KFoodBundleError("Google Drive returned an HTML page instead of the model bundle")
            total = 0
            with destination.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > _MAX_BUNDLE_BYTES:
                        raise KFoodBundleError("food-vision bundle exceeds the 128MB download limit")
                    target.write(chunk)
    except KFoodBundleError:
        raise
    except Exception as exc:
        raise KFoodBundleError("unable to download the food-vision bundle from Google Drive") from exc


def _already_ready(destination: Path) -> bool:
    checks = (
        (destination / "best.pt", config.KFOOD_CLASSIFIER_SHA256),
        (destination / "1.tflite", config.KFOOD_SEGMENTER_SHA256),
        (destination / "meta.json", config.KFOOD_CLASSIFIER_META_SHA256),
    )
    return all(path.is_file() and (not digest or _sha256(path) == digest) for path, digest in checks)


def _extract_verified(archive: Path, extracted: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            entries = {PurePosixPath(info.filename): info for info in bundle.infolist() if not info.is_dir()}
            for member, (filename, digest_setting) in _MEMBERS.items():
                info = entries.get(PurePosixPath(member))
                if info is None or info.file_size > _MAX_BUNDLE_BYTES:
                    raise KFoodBundleError(f"food-vision bundle member is missing or oversized: {member}")
                target = extracted / filename
                with bundle.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if digest_setting:
                    expected = str(getattr(config, digest_setting)).lower()
                    if _sha256(target) != expected:
                        raise KFoodBundleError(f"food-vision model SHA-256 mismatch: {filename}")
    except (OSError, zipfile.BadZipFile) as exc:
        raise KFoodBundleError("food-vision bundle is not a valid ZIP archive") from exc


def prepare_kfood_bundle() -> Path | None:
    """Download, verify and atomically install the optional public Drive bundle."""

    file_id = config.KFOOD_DRIVE_FILE_ID.strip()
    if not file_id:
        return None
    if not _FILE_ID.fullmatch(file_id):
        raise KFoodBundleError("KFOOD_DRIVE_FILE_ID has an invalid format")
    expected_bundle_sha = config.KFOOD_BUNDLE_SHA256.lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_bundle_sha):
        raise KFoodBundleError("KFOOD_BUNDLE_SHA256 must be a lowercase SHA-256 value")

    destination = Path(config.KFOOD_BUNDLE_DIR).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if _already_ready(destination):
        return destination

    with tempfile.TemporaryDirectory(prefix="kfood-bundle-", dir=destination.parent) as temporary_dir:
        temporary_root = Path(temporary_dir)
        archive = temporary_root / "bundle.zip"
        extracted = temporary_root / "extracted"
        extracted.mkdir()
        _download(file_id, archive)
        if _sha256(archive) != expected_bundle_sha:
            raise KFoodBundleError("food-vision bundle SHA-256 does not match KFOOD_BUNDLE_SHA256")

        _extract_verified(archive, extracted)

        for filename in ("best.pt", "meta.json", "1.tflite"):
            os.replace(extracted / filename, destination / filename)
    return destination


if __name__ == "__main__":
    prepare_kfood_bundle()
