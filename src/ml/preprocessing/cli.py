from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .harmonize import harmonize_klosa_wide, harmonize_knhanes
from .io import read_tabular, write_processed
from .pipeline import (
    add_age_cohorts,
    assign_group_split,
    build_klosa_incident_targets,
    clean_with_registry,
    validate_cohort_coverage,
)


def _clean_harmonized(
    harmonized: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    dataset: str,
    trace_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = registry[registry["dataset"] == dataset].copy()
    selected["source_column"] = selected["canonical_name"]
    cleaned, audit = clean_with_registry(harmonized, selected, require_approved=True)
    traces = harmonized[trace_columns].reset_index(drop=True)
    return pd.concat([traces, cleaned.reset_index(drop=True)], axis=1), audit


def main() -> None:
    parser = argparse.ArgumentParser(description="KLoSA·KNHANES 전처리 실행")
    parser.add_argument("dataset", choices=["klosa", "knhanes"])
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--registry", type=Path, default=Path("data/metadata/unified_variable_registry.csv"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--person-column", default="pid")
    args = parser.parse_args()

    registry = pd.read_csv(args.registry, encoding="utf-8-sig", low_memory=False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset == "klosa":
        if len(args.input) != 1:
            raise ValueError("KLoSA wide 자료는 입력 파일 하나를 지정합니다.")
        raw = read_tabular(args.input[0])
        harmonized, mapping_audit = harmonize_klosa_wide(
            raw, registry, person_column=args.person_column
        )
        processed, cleaning_audit = _clean_harmonized(
            harmonized,
            registry,
            dataset="KLoSA",
            trace_columns=["participant_id", "survey_wave", "survey_year"],
        )
        processed = add_age_cohorts(processed)
        processed = build_klosa_incident_targets(
            processed,
            person_column="participant_id",
            wave_column="survey_wave",
        )
        processed["split"] = assign_group_split(
            processed, group_column="participant_id"
        )
        cohort_report = validate_cohort_coverage(processed, dataset="KLoSA")
    else:
        if not args.year or len(args.year) != len(args.input):
            raise ValueError("KNHANES는 각 --input과 같은 순서의 --year가 필요합니다.")
        frames: list[pd.DataFrame] = []
        audits: list[pd.DataFrame] = []
        cleaning_audits: list[pd.DataFrame] = []
        for source, year in zip(args.input, args.year, strict=True):
            raw = read_tabular(source)
            frame, audit = harmonize_knhanes(
                raw, registry, survey_year=year, source_file=source.name
            )
            cleaned_frame, cleaning = _clean_harmonized(
                frame,
                registry,
                dataset="KNHANES",
                trace_columns=["record_key", "survey_year", "source_file", "source_row_number"],
            )
            frames.append(cleaned_frame)
            audits.append(audit)
            cleaning_audits.append(cleaning)
        processed = pd.concat(frames, ignore_index=True)
        mapping_audit = pd.concat(audits, ignore_index=True)
        cleaning_audit = pd.concat(cleaning_audits, ignore_index=True)
        processed = add_age_cohorts(processed)
        processed["split"] = assign_group_split(
            processed, group_column="record_key"
        )
        cohort_report = validate_cohort_coverage(processed, dataset="KNHANES")

    write_processed(processed, args.output_dir / f"{args.dataset}_cleaned.csv")
    write_processed(mapping_audit, args.output_dir / f"{args.dataset}_mapping_audit.csv")
    write_processed(cleaning_audit, args.output_dir / f"{args.dataset}_cleaning_audit.csv")
    write_processed(cohort_report, args.output_dir / f"{args.dataset}_cohort_report.csv")
    manifest = {
        "dataset": args.dataset,
        "input_files": [str(path) for path in args.input],
        "rows": int(len(processed)),
        "columns": int(len(processed.columns)),
        "note": "대치·인코딩·스케일링은 split 이후 각 train에서만 적합해야 함",
    }
    (args.output_dir / f"{args.dataset}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
