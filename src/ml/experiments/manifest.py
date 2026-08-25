from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPERIMENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
ALLOWED_KINDS = {"baseline", "candidate", "ensemble"}
ALLOWED_PRIMARY_METRICS = {"recall", "specificity", "auroc", "auprc", "f1", "brier"}


@dataclass(frozen=True)
class ExperimentManifest:
    schema_version: int
    experiment_id: str
    owner: str
    kind: str
    problem: str
    dataset_path: str
    entrypoint: str
    primary_metric: str
    minimum_specificity: float | None
    feature_schema_version: str
    notes: str
    path: Path

    @property
    def directory(self) -> Path:
        return self.path.parent

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "owner": self.owner,
            "kind": self.kind,
            "problem": self.problem,
            "dataset_path": self.dataset_path,
            "entrypoint": self.entrypoint,
            "primary_metric": self.primary_metric,
            "minimum_specificity": self.minimum_specificity,
            "feature_schema_version": self.feature_schema_version,
            "notes": self.notes,
        }


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}는 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def load_manifest(path: Path) -> ExperimentManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("지원하는 experiment.json schema_version은 1입니다.")

    experiment_id = _required_text(payload, "experiment_id")
    if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
        raise ValueError("experiment_id는 영문 소문자·숫자·하이픈·밑줄만 사용할 수 있습니다.")

    kind = _required_text(payload, "kind")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"kind는 {sorted(ALLOWED_KINDS)} 중 하나여야 합니다.")

    primary_metric = _required_text(payload, "primary_metric")
    if primary_metric not in ALLOWED_PRIMARY_METRICS:
        raise ValueError(f"지원하지 않는 primary_metric입니다: {primary_metric}")

    minimum_specificity = payload.get("minimum_specificity")
    if minimum_specificity is not None:
        minimum_specificity = float(minimum_specificity)
        if not 0 <= minimum_specificity <= 1:
            raise ValueError("minimum_specificity는 0과 1 사이여야 합니다.")

    entrypoint = _required_text(payload, "entrypoint")
    if ":" not in entrypoint:
        raise ValueError("entrypoint는 pipeline.py:run_experiment 형식이어야 합니다.")
    module_name, function_name = entrypoint.split(":", maxsplit=1)
    module_path = (path.parent / module_name).resolve()
    if path.parent.resolve() not in module_path.parents or not module_path.is_file():
        raise ValueError(f"entrypoint 파일을 찾을 수 없습니다: {module_name}")
    if not function_name.isidentifier():
        raise ValueError("entrypoint 함수명이 올바르지 않습니다.")

    return ExperimentManifest(
        schema_version=1,
        experiment_id=experiment_id,
        owner=_required_text(payload, "owner"),
        kind=kind,
        problem=_required_text(payload, "problem"),
        dataset_path=_required_text(payload, "dataset_path"),
        entrypoint=entrypoint,
        primary_metric=primary_metric,
        minimum_specificity=minimum_specificity,
        feature_schema_version=_required_text(payload, "feature_schema_version"),
        notes=str(payload.get("notes", "")).strip(),
        path=path.resolve(),
    )
