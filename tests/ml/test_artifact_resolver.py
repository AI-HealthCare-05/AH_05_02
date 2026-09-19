from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.ml.inference.artifact_resolver import ArtifactResolverError, resolve_artifact_uri


def test_local_artifact_path_is_not_copied(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"trusted-model")

    assert (
        resolve_artifact_uri(
            artifact,
            expected_sha256=hashlib.sha256(b"trusted-model").hexdigest(),
        )
        == artifact
    )


def test_s3_uri_requires_a_plain_bucket_and_key() -> None:
    with pytest.raises(ArtifactResolverError, match="plain s3"):
        resolve_artifact_uri("s3://bucket/model.joblib?versionId=unsafe", expected_sha256="a" * 64)
