"""Resolve checksum-pinned model artifacts from a local path or private S3."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse


class ArtifactResolverError(RuntimeError):
    """A configured artifact could not be fetched or failed integrity verification."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact_uri(uri: str | Path, *, expected_sha256: str) -> Path:
    """Return a local, SHA-256-verified artifact path.

    S3 objects are downloaded only into the runtime cache. The caller must use
    an IAM role or other normal AWS credential provider; credentials are never
    accepted as function arguments or persisted by this module.
    """

    raw = str(uri)
    if not raw.startswith("s3://"):
        return Path(raw)

    parsed = urlparse(raw)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path or parsed.query or parsed.fragment:
        raise ArtifactResolverError("artifact URI must be a plain s3://bucket/key value")

    filename = Path(parsed.path).name
    if not filename:
        raise ArtifactResolverError("artifact S3 URI must name a file")
    cache_root = Path(os.getenv("MODEL_CACHE_DIR", "/tmp/ah05-model-cache"))
    cache_root.mkdir(parents=True, exist_ok=True)
    destination = cache_root / f"{expected_sha256[:16]}-{filename}"
    if destination.is_file() and sha256(destination) == expected_sha256:
        return destination
    destination.unlink(missing_ok=True)

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        import boto3

        boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-northeast-2")).download_file(
            parsed.netloc,
            parsed.path.lstrip("/"),
            str(temporary),
        )
        if sha256(temporary) != expected_sha256:
            raise ArtifactResolverError("downloaded artifact SHA-256 does not match its pinned manifest")
        temporary.replace(destination)
    except ArtifactResolverError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise ArtifactResolverError("unable to download private model artifact from S3") from exc
    return destination
