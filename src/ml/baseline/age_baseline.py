"""Run non-comparable KLoSA and KNHANES feasibility baselines.

The two sources are never concatenated. Only a small set of semantically
harmonized predictors is shared. All persisted outputs are aggregate metrics
or hashes; individual-level rows and identifiers are not written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FEATURES = ("age", "female", "bmi", "current_smoker", "physically_active")
AGE_GROUPS = ("19-44", "45-64", "65+")


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    target: str
    identifier: tuple[str, ...]
    target_description: str
    inclusion_criteria: str
    exclusion_criteria: str


SPECS = {
    "klosa": DatasetSpec(
        name="KLoSA",
        target="target_diabetes_incident_next_wave",
        identifier=("participant_id", "survey_wave"),
        target_description="t0 미진단자의 다음 인접 조사(약 2년) 신규 당뇨 진단",
        inclusion_criteria="기준시점까지 당뇨 진단 이력이 없고 바로 다음 인접 차수의 타깃이 관측된 패널 행",
        exclusion_criteria="기준시점 이전 진단; 인접 다음 차수 미응답; 타깃 결측",
    ),
    "knhanes": DatasetSpec(
        name="KNHANES",
        target="target_diabetes_clinical",
        identifier=("record_key",),
        target_description="현재 미진단 성인의 횡단면 당뇨 임상 기준 해당 여부",
        inclusion_criteria="만 19세 이상; 의사진단 문항이 명시적으로 아니오; 공식 당뇨 상태 타깃 관측",
        exclusion_criteria="만 19세 미만; 진단 이력 있음 또는 진단 문항 불명; 타깃 결측",
    ),
}


def age_group(age: float) -> str:
    """Map an adult age to the reporting groups used by the service review."""
    if age < 19:
        raise ValueError("The baseline cohort is restricted to adults aged 19 or older.")
    if age <= 44:
        return "19-44"
    if age <= 64:
        return "45-64"
    return "65+"


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    parsed = float(value)
    return None if math.isnan(parsed) else parsed


def _binary(value: str | None) -> float | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    if parsed not in {0.0, 1.0}:
        raise ValueError(f"Expected binary value, received {value!r}.")
    return parsed


def _row_identifier(row: dict[str, str], spec: DatasetSpec) -> str:
    return ":".join(row[column] for column in spec.identifier)


def harmonize_row(dataset: str, row: dict[str, str]) -> dict[str, Any]:
    """Convert one already-cleaned source row to the common feature contract."""
    spec = SPECS[dataset]
    age = _optional_float(row.get("age"))
    target = _optional_float(row.get(spec.target))
    if age is None or target is None:
        raise ValueError("Age and target must be present in model-ready inputs.")

    sex = _optional_float(row.get("sex"))
    if sex is None:
        female = None
    elif dataset == "klosa":
        female = 1.0 if sex == 5.0 else 0.0 if sex == 1.0 else None
    else:
        female = 1.0 if sex == 2.0 else 0.0 if sex == 1.0 else None

    activity_source = "regular_exercise" if dataset == "klosa" else "aerobic_activity"
    return {
        "row_id": _row_identifier(row, spec),
        "entity_id": row[spec.identifier[0]],
        "split": row["split"],
        "target": int(target),
        "age_group": age_group(age),
        "features": [
            age,
            female,
            _optional_float(row.get("bmi")),
            _binary(row.get("current_smoker")),
            _binary(row.get(activity_source)),
        ],
    }


def load_harmonized(path: Path, dataset: str) -> list[dict[str, Any]]:
    """Load a model-ready CSV without retaining source-specific extra fields."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {path}.")
        required = {
            "split",
            "age",
            "sex",
            "bmi",
            "current_smoker",
            SPECS[dataset].target,
            *SPECS[dataset].identifier,
            "regular_exercise" if dataset == "klosa" else "aerobic_activity",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
        for source_row in reader:
            rows.append(harmonize_row(dataset, source_row))
    return rows


def _rank(seed: int, dataset: str, split: str, stratum: str, row_id: str) -> str:
    token = f"{seed}|{dataset}|{split}|{stratum}|{row_id}".encode()
    return hashlib.sha256(token).hexdigest()


def _allocate_quotas(counts: dict[str, int], limit: int) -> dict[str, int]:
    total = sum(counts.values())
    if limit >= total:
        return counts.copy()
    if limit < len(counts):
        raise ValueError("Sample limit is too small to retain every non-empty age-label stratum.")

    ideals = {key: value * limit / total for key, value in counts.items()}
    quotas = {key: min(value, max(1, math.floor(ideals[key]))) for key, value in counts.items()}
    while sum(quotas.values()) > limit:
        candidates = [key for key, quota in quotas.items() if quota > 1]
        key = min(candidates, key=lambda item: (ideals[item] - quotas[item], item))
        quotas[key] -= 1
    while sum(quotas.values()) < limit:
        candidates = [key for key, quota in quotas.items() if quota < counts[key]]
        key = max(candidates, key=lambda item: (ideals[item] - quotas[item], item))
        quotas[key] += 1
    return quotas


def deterministic_stratified_sample(
    rows: list[dict[str, Any]], *, limit: int, seed: int, dataset: str, split: str
) -> list[dict[str, Any]]:
    """Sample deterministically while retaining each non-empty age-label stratum."""
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        stratum = f"{row['age_group']}|{row['target']}"
        strata[stratum].append(row)
    quotas = _allocate_quotas({key: len(value) for key, value in strata.items()}, limit)
    sampled: list[dict[str, Any]] = []
    for stratum, members in sorted(strata.items()):
        ranked = sorted(
            members,
            key=lambda row: _rank(seed, dataset, split, stratum, row["row_id"]),
        )
        sampled.extend(ranked[: quotas[stratum]])
    return sorted(sampled, key=lambda row: row["row_id"])


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_hash(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row_id in sorted(row["row_id"] for row in rows):
        digest.update(row_id.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _metric_row(y_true: list[int], probabilities: list[float], threshold: float) -> dict[str, Any]:
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        recall_score,
        roc_auc_score,
    )

    predictions = [int(probability >= threshold) for probability in probabilities]
    labels_present = len(set(y_true)) == 2
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "n": len(y_true),
        "positive_n": sum(y_true),
        "positive_rate": sum(y_true) / len(y_true),
        "auroc": roc_auc_score(y_true, probabilities) if labels_present else None,
        "auprc": average_precision_score(y_true, probabilities) if labels_present else None,
        "recall": recall_score(y_true, predictions, zero_division=0),
        "specificity": tn / (tn + fp) if tn + fp else None,
        "f1": f1_score(y_true, predictions, zero_division=0),
        "brier": brier_score_loss(y_true, probabilities),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def _build_models(seed: int) -> dict[str, Any]:
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    def pipeline(classifier: Any) -> Pipeline:
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("classifier", classifier),
            ]
        )

    return {
        "dummy": pipeline(DummyClassifier(strategy="prior", random_state=seed)),
        "logistic_regression": pipeline(LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed)),
        "random_forest": pipeline(
            RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=5,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=seed,
            )
        ),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_dataset(
    dataset: str, source_path: Path, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = load_harmonized(source_path, dataset)
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)

    seed = int(config["seed"])
    sampled: dict[str, list[dict[str, Any]]] = {}
    split_manifest: dict[str, Any] = {}
    for split in ("train", "validation", "test"):
        source_rows = by_split[split]
        limit = int(config["sample_limits"][split])
        sampled_rows = deterministic_stratified_sample(
            source_rows,
            limit=min(limit, len(source_rows)),
            seed=seed,
            dataset=dataset,
            split=split,
        )
        sampled[split] = sampled_rows
        split_manifest[split] = {
            "full_n": len(source_rows),
            "sample_n": len(sampled_rows),
            "full_positive_rate": sum(row["target"] for row in source_rows) / len(source_rows),
            "sample_positive_rate": sum(row["target"] for row in sampled_rows) / len(sampled_rows),
            "sample_id_sha256": _sample_hash(sampled_rows),
            "sample_age_label_counts": {
                f"{group}|{target}": sum(row["age_group"] == group and row["target"] == target for row in sampled_rows)
                for group in AGE_GROUPS
                for target in (0, 1)
            },
        }

    train_x = [row["features"] for row in sampled["train"]]
    train_y = [row["target"] for row in sampled["train"]]
    threshold = float(config["decision_threshold"])
    overall: list[dict[str, Any]] = []
    age_metrics: list[dict[str, Any]] = []
    for model_name, model in _build_models(seed).items():
        model.fit(train_x, train_y)
        for split in ("validation", "test"):
            split_rows = sampled[split]
            probabilities = model.predict_proba([row["features"] for row in split_rows])[:, 1].tolist()
            metrics = _metric_row([row["target"] for row in split_rows], probabilities, threshold)
            overall.append(
                {
                    "dataset": SPECS[dataset].name,
                    "target_definition": SPECS[dataset].target_description,
                    "model": model_name,
                    "split": split,
                    **metrics,
                }
            )
            if split != "test":
                continue
            for group in AGE_GROUPS:
                indices = [index for index, row in enumerate(split_rows) if row["age_group"] == group]
                if not indices:
                    age_metrics.append(
                        {
                            "dataset": SPECS[dataset].name,
                            "model": model_name,
                            "split": split,
                            "age_group": group,
                            "status": "not_observed",
                            **{key: None for key in _metric_row([0], [0.0], threshold)},
                        }
                    )
                    continue
                group_y = [split_rows[index]["target"] for index in indices]
                group_probabilities = [probabilities[index] for index in indices]
                age_metrics.append(
                    {
                        "dataset": SPECS[dataset].name,
                        "model": model_name,
                        "split": split,
                        "age_group": group,
                        "status": "evaluated",
                        **_metric_row(group_y, group_probabilities, threshold),
                    }
                )

    ages = [row["features"][0] for row in rows]
    full_age_groups = {}
    for group in AGE_GROUPS:
        group_rows = [row for row in rows if row["age_group"] == group]
        full_age_groups[group] = {
            "observation_n": len(group_rows),
            "positive_n": sum(row["target"] for row in group_rows),
            "positive_rate": (sum(row["target"] for row in group_rows) / len(group_rows) if group_rows else None),
        }
    manifest = {
        "dataset": SPECS[dataset].name,
        "target_definition": SPECS[dataset].target_description,
        "inclusion_criteria": SPECS[dataset].inclusion_criteria,
        "exclusion_criteria": SPECS[dataset].exclusion_criteria,
        "source_path_name": source_path.name,
        "source_size_bytes": source_path.stat().st_size,
        "source_sha256": _sha256_file(source_path),
        "full_observation_n": len(rows),
        "full_unique_entity_n": len({row["entity_id"] for row in rows}),
        "full_positive_n": sum(row["target"] for row in rows),
        "full_positive_rate": sum(row["target"] for row in rows) / len(rows),
        "full_age_groups": full_age_groups,
        "observed_age_min": min(ages),
        "observed_age_max": max(ages),
        "seed": seed,
        "strata": "split x age_group x target",
        "splits": split_manifest,
    }
    return overall, age_metrics, manifest


def run_experiment(
    klosa_path: Path,
    knhanes_path: Path,
    config_path: Path,
    output_dir: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    all_overall: list[dict[str, Any]] = []
    all_age_metrics: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for dataset, source_path in (("klosa", klosa_path), ("knhanes", knhanes_path)):
        overall, age_metrics, manifest = run_dataset(dataset, source_path, config)
        all_overall.extend(overall)
        all_age_metrics.extend(age_metrics)
        manifests.append(manifest)
    _write_csv(output_dir / "overall_metrics.csv", all_overall)
    _write_csv(output_dir / "age_group_metrics.csv", all_age_metrics)
    _write_csv(
        output_dir / "cohort_summary.csv",
        [
            {
                "dataset": manifest["dataset"],
                "target_definition": manifest["target_definition"],
                "inclusion_criteria": manifest["inclusion_criteria"],
                "exclusion_criteria": manifest["exclusion_criteria"],
                "full_observation_n": manifest["full_observation_n"],
                "full_unique_entity_n": manifest["full_unique_entity_n"],
                "positive_n": manifest["full_positive_n"],
                "positive_rate": manifest["full_positive_rate"],
                "observed_age_min": manifest["observed_age_min"],
                "observed_age_max": manifest["observed_age_max"],
            }
            for manifest in manifests
        ],
    )
    (output_dir / "sample_manifest.json").write_text(
        json.dumps(
            {
                "purpose": "Reduced-sample pipeline feasibility check; not final model performance.",
                "cross_dataset_comparison_warning": (
                    "KLoSA predicts adjacent-wave incidence; KNHANES screens current cross-sectional status. "
                    "Their metrics must not be ranked as if they share one target."
                ),
                "features": list(FEATURES),
                "config": config,
                "datasets": manifests,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--klosa", type=Path, required=True)
    parser.add_argument("--knhanes", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/age_baseline.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/sp2_data_003"))
    args = parser.parse_args()
    run_experiment(args.klosa, args.knhanes, args.config, args.output_dir)


if __name__ == "__main__":
    main()
