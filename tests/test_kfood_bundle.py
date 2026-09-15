from __future__ import annotations

import hashlib
import io
import zipfile
from email.message import Message
from pathlib import Path

import pytest

from app.core import config
from app.vision import kfood_bundle


class _Response(io.BytesIO):
    def __init__(self, payload: bytes):
        super().__init__(payload)
        self.headers = Message()
        self.headers["Content-Type"] = "application/zip"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _bundle() -> tuple[bytes, bytes, bytes]:
    classifier = b"classifier"
    segmenter = b"segmenter"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("models/artifacts/food_vision/kfood/best.pt", classifier)
        archive.writestr("models/artifacts/food_vision/kfood/meta.json", b"{}")
        archive.writestr("models/artifacts/food_vision/kfood/1.tflite", segmenter)
    return output.getvalue(), classifier, segmenter


def _configure(monkeypatch: pytest.MonkeyPatch, destination: Path, payload: bytes, classifier: bytes, segmenter: bytes):
    monkeypatch.setattr(config, "KFOOD_DRIVE_FILE_ID", "1KvCX9bU9GwZvcvZSl0eYHlZ-yg4UbAjQ")
    monkeypatch.setattr(config, "KFOOD_BUNDLE_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(config, "KFOOD_BUNDLE_DIR", destination)
    monkeypatch.setattr(config, "KFOOD_CLASSIFIER_SHA256", hashlib.sha256(classifier).hexdigest())
    monkeypatch.setattr(config, "KFOOD_CLASSIFIER_META_SHA256", hashlib.sha256(b"{}").hexdigest())
    monkeypatch.setattr(config, "KFOOD_SEGMENTER_SHA256", hashlib.sha256(segmenter).hexdigest())


def test_public_drive_bundle_is_verified_and_installed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload, classifier, segmenter = _bundle()
    destination = tmp_path / "kfood"
    _configure(monkeypatch, destination, payload, classifier, segmenter)
    monkeypatch.setattr(kfood_bundle, "urlopen", lambda *_args, **_kwargs: _Response(payload))

    assert kfood_bundle.prepare_kfood_bundle() == destination.resolve()
    assert (destination / "best.pt").read_bytes() == classifier
    assert (destination / "meta.json").read_bytes() == b"{}"
    assert (destination / "1.tflite").read_bytes() == segmenter


def test_bundle_digest_mismatch_installs_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload, classifier, segmenter = _bundle()
    destination = tmp_path / "kfood"
    _configure(monkeypatch, destination, payload, classifier, segmenter)
    monkeypatch.setattr(config, "KFOOD_BUNDLE_SHA256", "0" * 64)
    monkeypatch.setattr(kfood_bundle, "urlopen", lambda *_args, **_kwargs: _Response(payload))

    with pytest.raises(kfood_bundle.KFoodBundleError, match="bundle SHA-256"):
        kfood_bundle.prepare_kfood_bundle()
    assert not (destination / "best.pt").exists()


def test_unconfigured_drive_bundle_does_not_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "KFOOD_DRIVE_FILE_ID", "")
    monkeypatch.setattr(kfood_bundle, "urlopen", lambda *_args, **_kwargs: pytest.fail("unexpected download"))
    assert kfood_bundle.prepare_kfood_bundle() is None
