from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/provision-models-google-drive.py"
SPEC = importlib.util.spec_from_file_location("google_drive_model_provisioning", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _manifest(digest: str) -> dict[str, object]:
    return {
        "model_key": "diabetes_incidence",
        "model_version": "test-v1",
        "artifact_sha256": digest,
        "artifact_local_path": "models/artifacts/test/model.joblib",
    }


def test_verify_delivery_requires_drive_and_registry_hashes_to_match(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"approved model")
    expected = _digest(artifact.read_bytes())
    manifest = _manifest(expected)
    delivery = tmp_path / "manifest.json"
    registry = tmp_path / "registry.json"
    delivery.write_text(json.dumps(manifest), encoding="utf-8")
    registry.write_text(json.dumps(manifest), encoding="utf-8")
    entry = {
        "name": "tomorrow",
        "artifact_sha256": expected,
        "registry_manifest": "registry.json",
    }
    original_root = MODULE.ROOT
    MODULE.ROOT = tmp_path
    try:
        loaded, destination = MODULE.verify_delivery(entry, delivery, artifact)
    finally:
        MODULE.ROOT = original_root

    assert loaded["model_version"] == "test-v1"
    assert destination == tmp_path / "models/artifacts/test/model.joblib"


def test_verify_delivery_rejects_tampered_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"tampered")
    manifest = _manifest("0" * 64)
    delivery = tmp_path / "manifest.json"
    registry = tmp_path / "registry.json"
    delivery.write_text(json.dumps(manifest), encoding="utf-8")
    registry.write_text(json.dumps(manifest), encoding="utf-8")
    entry = {
        "name": "tomorrow",
        "artifact_sha256": "0" * 64,
        "registry_manifest": "registry.json",
    }
    original_root = MODULE.ROOT
    MODULE.ROOT = tmp_path
    try:
        with pytest.raises(ValueError, match="SHA-256 계약 불일치"):
            MODULE.verify_delivery(entry, delivery, artifact)
    finally:
        MODULE.ROOT = original_root
