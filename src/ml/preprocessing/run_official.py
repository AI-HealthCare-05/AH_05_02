from __future__ import annotations

import argparse
from pathlib import Path

from .official import (
    KLOSA_FEATURES,
    KNHANES_FEATURES,
    build_cohort_quality_table,
    build_missingness_table,
    build_quality_summary,
    build_selected_variable_registry,
    preprocess_klosa_directory,
    preprocess_knhanes_directory,
    save_summary,
    source_manifest,
    write_csv,
)


def _quality_report(summary: dict[str, object], cohort_table) -> str:
    display = cohort_table.copy()
    display["prevalence"] = display["prevalence"].map(lambda value: f"{value:.2%}")
    table = display.to_markdown(index=False)
    return f"""# KLoSA·KNHANES 전처리 품질보고서

생성 기준일: 2026-08-12

## 처리 결과

- KNHANES: {summary["knhanes_rows"]:,}건, 2016–2024년
- KLoSA: {summary["klosa_rows"]:,}개 패널 관측행, 1–10차
- 중복 키: KNHANES `연도:ID`, KLoSA `PID-차수` 기준 0건
- 두 조사는 행 단위로 합치지 않고 공통 개념의 통합 변수 명세로 연결함

## 모델별 분석 표본

{table}

## 핵심 전처리 원칙

- KNHANES는 현재 검사·설문 기반의 임상 위험 선별 타깃이다.
- KLoSA는 미진단 이력이 확인되고 인접한 다음 차수 응답이 있는 사람의 약 2년 신규 진단 타깃이다.
- 혈압, 공복혈당, HbA1c, 진단·복약 변수는 타깃 구성 또는 적합성 확인에만 사용하고 모델 입력에서 제외했다.
- KNHANES는 연도 기준 train(2016–2020), validation(2021–2022), test(2023–2024)로 분리했다.
- KLoSA는 동일 PID가 한 split에만 들어가도록 그룹 해시 분리했다.
- 결측치 대치·스케일링·범주 인코딩은 이 파일 생성 단계에서 학습하지 않는다. 향후 각 모델의 train split에서만 적합한다.
- KLoSA는 모집 특성을 반영해 연령별로 나누지 않고 하나의 패널 모델만 구성한다.

## 해석 제한

예측 결과는 의료 진단이나 처방이 아니라 위험 선별과 건강교육 목적으로만 사용한다. KNHANES와 KLoSA는 조사설계·관측단위·타깃 시점이 달라 행 단위 결합이나 성능의 단순 비교를 금지한다.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="공식 KLoSA·KNHANES 전처리")
    parser.add_argument("--knhanes-root", type=Path, default=Path("data/interim/source_extract/knhanes"))
    parser.add_argument("--klosa-root", type=Path, default=Path("data/interim/source_extract/klosa"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/official_v1"))
    parser.add_argument("--report-dir", type=Path, default=Path("outputs/preprocessing_20260812"))
    args = parser.parse_args()

    knhanes = preprocess_knhanes_directory(args.knhanes_root)
    klosa = preprocess_klosa_directory(args.klosa_root)
    write_csv(knhanes, args.processed_dir / "knhanes_cleaned_2016_2024.csv")
    write_csv(klosa, args.processed_dir / "klosa_panel_cleaned_1_10.csv")

    for disease in ("hypertension", "diabetes"):
        for threshold in (19, 40, 65):
            kn_mask = knhanes[f"cohort_{threshold}_plus"].fillna(False) & knhanes[
                f"eligible_{disease}_undiagnosed"
            ].fillna(False)
            kn_columns = ["record_key", "survey_year", "split", f"target_{disease}_clinical", *KNHANES_FEATURES]
            write_csv(
                knhanes.loc[kn_mask, kn_columns],
                args.processed_dir / f"knhanes_{disease}_undiagnosed_{threshold}plus.csv",
            )

        kl_mask = klosa[f"eligible_{disease}_incident"].fillna(False)
        kl_columns = [
            "participant_id",
            "survey_wave",
            "survey_year",
            "next_wave",
            "split",
            f"target_{disease}_incident_next_wave",
            *KLOSA_FEATURES,
        ]
        write_csv(
            klosa.loc[kl_mask, kl_columns],
            args.processed_dir / f"klosa_{disease}_incident_all.csv",
        )

    # Remove obsolete generated age-split KLoSA tables from earlier versions.
    for disease in ("hypertension", "diabetes"):
        for threshold in (19, 40, 65):
            stale = args.processed_dir / f"klosa_{disease}_incident_{threshold}plus.csv"
            if stale.exists():
                stale.unlink()

    summary = build_quality_summary(knhanes, klosa)
    save_summary(summary, args.report_dir / "quality_summary.json")
    cohort_table = build_cohort_quality_table(knhanes, klosa)
    missingness = build_missingness_table(knhanes, klosa)
    write_csv(cohort_table, args.report_dir / "cohort_target_summary.csv")
    write_csv(missingness, args.report_dir / "feature_missingness.csv")
    write_csv(
        build_selected_variable_registry(),
        Path("data/metadata/official_selected_variable_registry.csv"),
    )
    (args.report_dir / "QUALITY_REPORT.md").write_text(_quality_report(summary, cohort_table), encoding="utf-8")
    write_csv(
        source_manifest(
            [
                *Path("data/raw/knhanes").glob("*.zip"),
                Path("data/raw/klosa/KLoSA_1-10_SPSS.zip"),
            ]
        ),
        Path("data/metadata/official_raw_source_manifest.csv"),
    )
    print(summary)


if __name__ == "__main__":
    main()
