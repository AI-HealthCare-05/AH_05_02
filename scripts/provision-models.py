"""Provision Git-excluded model artifacts after verifying their manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def provision(source: Path, manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = str(manifest["artifact_sha256"]).lower()
    actual = sha256(source)
    if actual != expected:
        raise ValueError(f"SHA-256 불일치: {source} (expected={expected}, actual={actual})")
    destination = (ROOT / manifest["artifact_local_path"]).resolve()
    artifact_root = (ROOT / "models" / "artifacts").resolve()
    if artifact_root not in destination.parents:
        raise ValueError(f"허용되지 않은 모델 대상 경로: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"OK {manifest['model_key']}: {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=Path, help="오늘이 KNHANES model.joblib 경로")
    parser.add_argument("--tomorrow", type=Path, help="내일이 KLoSA model.joblib 경로")
    args = parser.parse_args()
    if not args.today and not args.tomorrow:
        parser.error("--today 또는 --tomorrow 중 하나 이상을 지정하세요.")
    if args.today:
        provision(
            args.today.resolve(),
            ROOT / "models/registry/diabetes_current_screening/candidates/knhanes-current-screening-v050.json",
        )
    if args.tomorrow:
        provision(
            args.tomorrow.resolve(),
            ROOT / "models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json",
        )


if __name__ == "__main__":
    main()
