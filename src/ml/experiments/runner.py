from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.ml.experiments.manifest import ExperimentManifest, load_manifest

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = ROOT / "experiments" / "diabetes_incidence"
RUN_ROOT = ROOT / "outputs" / "ml"
LEADERBOARD_PATH = EXPERIMENT_ROOT / "leaderboard.csv"
METRIC_NAMES = ("recall", "specificity", "auroc", "auprc", "f1", "brier")


def discover_manifests() -> list[ExperimentManifest]:
    manifests: list[ExperimentManifest] = []
    for path in sorted(EXPERIMENT_ROOT.glob("*/*/experiment.json")):
        manifests.append(load_manifest(path))
    return manifests


def resolve_manifest(reference: str) -> ExperimentManifest:
    direct = Path(reference)
    if direct.is_dir():
        direct = direct / "experiment.json"
    if direct.is_file():
        return load_manifest(direct)

    matches = [manifest for manifest in discover_manifests() if manifest.experiment_id == reference]
    if len(matches) != 1:
        raise ValueError(f"실험 ID를 하나로 찾을 수 없습니다: {reference}")
    return matches[0]


def validate_repository() -> list[ExperimentManifest]:
    manifests = discover_manifests()
    ids = [manifest.experiment_id for manifest in manifests]
    duplicates = sorted({experiment_id for experiment_id in ids if ids.count(experiment_id) > 1})
    if duplicates:
        raise ValueError(f"중복 experiment_id가 있습니다: {', '.join(duplicates)}")
    return manifests


def create_experiment(experiment_id: str, kind: str, owner: str) -> Path:
    category = {"baseline": "baselines", "candidate": "candidates", "ensemble": "ensembles"}.get(kind)
    if category is None:
        raise ValueError("kind는 baseline, candidate, ensemble 중 하나여야 합니다.")
    template_dir = ROOT / "experiments" / "_template"
    destination = EXPERIMENT_ROOT / category / experiment_id
    if destination.exists():
        raise FileExistsError(f"이미 존재하는 실험 폴더입니다: {destination}")
    shutil.copytree(template_dir, destination)
    manifest_path = destination / "experiment.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload.update({"experiment_id": experiment_id, "kind": kind, "owner": owner})
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    load_manifest(manifest_path)
    return destination


def _load_entrypoint(manifest: ExperimentManifest):
    module_file, function_name = manifest.entrypoint.split(":", maxsplit=1)
    module_path = manifest.directory / module_file
    module_name = f"team_experiment_{manifest.experiment_id}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"실험 모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, function_name, None)
    if not callable(function):
        raise ValueError(f"호출 가능한 {function_name} 함수를 찾을 수 없습니다.")
    return function


def _validate_metrics(metrics: Mapping[str, Any]) -> dict[str, float | None]:
    normalized: dict[str, float | None] = {}
    for name in METRIC_NAMES:
        value = metrics.get(name)
        if value is None:
            normalized[name] = None
            continue
        number = float(value)
        if not 0 <= number <= 1:
            raise ValueError(f"{name}은 0과 1 사이여야 합니다.")
        normalized[name] = number
    if normalized["recall"] is None or normalized["specificity"] is None:
        raise ValueError("metrics에는 recall과 specificity가 반드시 있어야 합니다.")
    return normalized


def run_experiment(manifest: ExperimentManifest) -> Path:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUN_ROOT / manifest.experiment_id / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    context = {
        "root": ROOT,
        "experiment_dir": manifest.directory,
        "run_dir": run_dir,
        "dataset_path": ROOT / manifest.dataset_path,
        "manifest": manifest.as_dict(),
    }
    try:
        result = _load_entrypoint(manifest)(context)
        if not isinstance(result, Mapping):
            raise TypeError("run_experiment은 dict 형태의 결과를 반환해야 합니다.")
        metrics = result.get("metrics")
        if not isinstance(metrics, Mapping):
            raise TypeError("반환값에는 metrics 객체가 있어야 합니다.")
        normalized_metrics = _validate_metrics(metrics)
        status = "constraint_passed"
        if (
            manifest.minimum_specificity is not None
            and normalized_metrics["specificity"] < manifest.minimum_specificity
        ):
            status = "constraint_failed"
        record = {
            "run_id": run_id,
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "manifest": manifest.as_dict(),
            "metrics": normalized_metrics,
            "artifact": result.get("artifact"),
            "notes": result.get("notes", ""),
        }
        (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return run_dir
    except Exception:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise


def build_leaderboard() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_path in RUN_ROOT.glob("*/*/run.json"):
        record = json.loads(run_path.read_text(encoding="utf-8"))
        manifest = record["manifest"]
        metrics = record["metrics"]
        rows.append(
            {
                "experiment_id": manifest["experiment_id"],
                "kind": manifest["kind"],
                "owner": manifest["owner"],
                "run_id": record["run_id"],
                "status": record["status"],
                **{name: metrics.get(name) for name in METRIC_NAMES},
                "feature_schema_version": manifest["feature_schema_version"],
            }
        )
    rows.sort(key=lambda row: (-(row["recall"] or -1), -(row["specificity"] or -1), row["experiment_id"]))
    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "experiment_id",
        "kind",
        "owner",
        "run_id",
        "status",
        *METRIC_NAMES,
        "feature_schema_version",
    ]
    with LEADERBOARD_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def register_candidate(run_dir: Path) -> Path:
    run_path = run_dir.resolve() / "run.json"
    if RUN_ROOT.resolve() not in run_path.parents or not run_path.is_file():
        raise ValueError("outputs/ml 아래의 유효한 run 디렉터리를 지정해야 합니다.")
    record = json.loads(run_path.read_text(encoding="utf-8"))
    if record["status"] != "constraint_passed":
        raise ValueError("운영 제약을 통과하지 못한 실행은 후보로 등록할 수 없습니다.")
    artifact_name = record.get("artifact")
    if not isinstance(artifact_name, str):
        raise ValueError("run.json에 artifact 파일명이 없습니다.")
    artifact_path = (run_dir / artifact_name).resolve()
    if run_dir.resolve() not in artifact_path.parents or not artifact_path.is_file():
        raise ValueError("artifact는 해당 run 디렉터리 안에 있어야 합니다.")
    checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    model_key = "diabetes_incidence"
    candidate_dir = ROOT / "models" / "registry" / model_key / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    destination = candidate_dir / f"{record['manifest']['experiment_id']}-{record['run_id']}.json"
    candidate = {
        "model_key": model_key,
        "promotion_status": "candidate_only",
        "experiment_id": record["manifest"]["experiment_id"],
        "run_id": record["run_id"],
        "artifact_local_path": str(artifact_path.relative_to(ROOT)).replace("\\", "/"),
        "artifact_sha256": checksum,
        "feature_schema_version": record["manifest"]["feature_schema_version"],
        "metrics": record["metrics"],
        "medical_review_required": True,
    }
    destination.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="팀 공통 ML 실험 조립기")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="모든 experiment.json 검사")
    subparsers.add_parser("list", help="등록된 실험 목록")
    new_parser = subparsers.add_parser("new", help="표준 실험 폴더 생성")
    new_parser.add_argument("experiment_id")
    new_parser.add_argument("--kind", choices=("baseline", "candidate", "ensemble"), required=True)
    new_parser.add_argument("--owner", required=True)
    run_parser = subparsers.add_parser("run", help="실험 실행")
    run_parser.add_argument("experiment")
    subparsers.add_parser("leaderboard", help="실행 결과로 리더보드 갱신")
    register_parser = subparsers.add_parser("register-candidate", help="검증 통과 모델을 후보 레지스트리에 등록")
    register_parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    if args.command == "validate":
        manifests = validate_repository()
        print(f"OK: {len(manifests)}개 실험 manifest")
    elif args.command == "list":
        for manifest in validate_repository():
            print(f"{manifest.experiment_id}\t{manifest.kind}\t{manifest.owner}")
    elif args.command == "new":
        print(create_experiment(args.experiment_id, args.kind, args.owner))
    elif args.command == "run":
        print(run_experiment(resolve_manifest(args.experiment)))
    elif args.command == "leaderboard":
        print(f"OK: {len(build_leaderboard())}개 실행 -> {LEADERBOARD_PATH}")
    elif args.command == "register-candidate":
        print(register_candidate(args.run_dir))


if __name__ == "__main__":
    main()
