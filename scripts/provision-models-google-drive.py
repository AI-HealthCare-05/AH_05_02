"""Download Google Drive model deliveries and install only verified artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/model_delivery/google_drive_models.json"
DOWNLOAD_URL = "https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(file_id: str, destination: Path) -> None:
    request = urllib.request.Request(
        DOWNLOAD_URL.format(file_id=file_id),
        headers={"User-Agent": "AH-05-02-model-provisioner/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 객체가 아닙니다: {path}")
    return value


def _validated_destination(manifest: dict[str, Any]) -> Path:
    destination = (ROOT / str(manifest["artifact_local_path"])).resolve()
    artifact_root = (ROOT / "models/artifacts").resolve()
    if artifact_root not in destination.parents:
        raise ValueError(f"허용되지 않은 모델 대상 경로: {destination}")
    return destination


def verify_delivery(entry: dict[str, Any], downloaded_manifest: Path, artifact: Path) -> tuple[dict[str, Any], Path]:
    delivery = _load_json(downloaded_manifest)
    registry = _load_json((ROOT / str(entry["registry_manifest"])).resolve())
    expected = str(entry["artifact_sha256"]).lower()
    values = {
        "downloaded artifact": sha256(artifact),
        "delivery manifest": str(delivery.get("artifact_sha256", "")).lower(),
        "repository registry": str(registry.get("artifact_sha256", "")).lower(),
    }
    mismatches = {label: value for label, value in values.items() if value != expected}
    if mismatches:
        raise ValueError(f"SHA-256 계약 불일치 ({entry['name']}): {mismatches}")
    for key in ("model_key", "model_version"):
        if delivery.get(key) != registry.get(key):
            raise ValueError(f"{key} 계약 불일치: {entry['name']}")
    return delivery, _validated_destination(delivery)


def atomic_install(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def provision(config_path: Path, selected: set[str] | None = None) -> list[Path]:
    config = _load_json(config_path)
    entries = config.get("models")
    if not isinstance(entries, list) or not entries:
        raise ValueError("다운로드할 모델 계약이 없습니다.")
    installed: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="ah05-model-delivery-") as temporary_directory:
        staging = Path(temporary_directory)
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("모델 계약 항목은 JSON 객체여야 합니다.")
            name = str(entry["name"])
            if selected and name not in selected:
                continue
            model_staging = staging / name
            model_staging.mkdir()
            manifest_path = model_staging / "manifest.json"
            artifact_path = model_staging / "model.joblib"
            download(str(entry["manifest_file_id"]), manifest_path)
            download(str(entry["artifact_file_id"]), artifact_path)
            _, destination = verify_delivery(entry, manifest_path, artifact_path)
            atomic_install(artifact_path, destination)
            installed.append(destination)
            print(f"OK {name}: {destination} ({sha256(destination)})")
    if selected and len(installed) != len(selected):
        configured = {str(entry["name"]) for entry in entries if isinstance(entry, dict)}
        raise ValueError(f"등록되지 않은 모델 이름: {sorted(selected - configured)}")
    return installed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", action="append", choices=("today", "tomorrow"))
    args = parser.parse_args()
    provision(args.config.resolve(), set(args.model) if args.model else None)


if __name__ == "__main__":
    main()
