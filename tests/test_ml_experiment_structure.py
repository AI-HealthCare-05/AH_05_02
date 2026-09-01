from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ml.experiments import runner
from src.ml.experiments.manifest import load_manifest
from src.ml.experiments.runner import validate_repository

ROOT = Path(__file__).resolve().parents[1]


def test_repository_experiment_manifests_are_valid_and_unique() -> None:
    manifests = validate_repository()
    assert len({manifest.experiment_id for manifest in manifests}) == len(manifests)


def test_template_manifest_contract(tmp_path: Path) -> None:
    template_dir = ROOT / "experiments" / "_template"
    (tmp_path / "pipeline.py").write_text((template_dir / "pipeline.py").read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads((template_dir / "experiment.json").read_text(encoding="utf-8"))
    payload.update({"experiment_id": "unit_test_v001", "owner": "tester"})
    manifest_path = tmp_path / "experiment.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    assert manifest.experiment_id == "unit_test_v001"
    assert manifest.primary_metric == "recall"
    assert manifest.minimum_specificity == pytest.approx(0.4)
    assert manifest.dataset_version == "replace_with_dataset_version"
    assert manifest.split_version == "replace_with_split_version"
    assert manifest.model_version == "replace_with_model_version"
    assert manifest.threshold_version == "replace_with_threshold_version"


def test_experiment_categories_exist() -> None:
    root = ROOT / "experiments" / "diabetes_incidence"
    assert (root / "baselines").is_dir()
    assert (root / "candidates").is_dir()
    assert (root / "ensembles").is_dir()


def test_new_experiment_is_created_from_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    experiment_root = tmp_path / "diabetes_incidence"
    monkeypatch.setattr(runner, "EXPERIMENT_ROOT", experiment_root)

    destination = runner.create_experiment("rf_unit_v001", "candidate", "tester")

    manifest = load_manifest(destination / "experiment.json")
    assert destination == experiment_root / "candidates" / "rf_unit_v001"
    assert manifest.experiment_id == "rf_unit_v001"
    assert manifest.owner == "tester"
    assert manifest.kind == "candidate"
