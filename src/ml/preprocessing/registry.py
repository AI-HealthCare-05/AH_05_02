from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

OFFICIAL_SOURCES = {
    "KLoSA": "https://survey.keis.or.kr/klosa/klosadownload/List.jsp",
    "KNHANES": "https://knhanes.kdca.go.kr/knhanes/main.do",
}


CURATED_CONCEPTS = [
    # dataset, canonical, semantic, label, role, dtype, unit, min, max, leakage note
    ("KLoSA", "age", "w__A002_age", "응답자 연령", "feature", "integer", "year", 19, 120, ""),
    ("KLoSA", "sex", "w__gender1", "응답자 성별", "feature", "category", "code", "", "", ""),
    ("KLoSA", "bmi", "w__bmi", "체질량지수", "feature", "float", "kg/m2", 10, 80, ""),
    ("KLoSA", "current_smoking", "w__C117", "현재 흡연 여부", "feature", "category", "code", "", "", ""),
    ("KLoSA", "current_alcohol", "w__C122", "평소 음주 여부", "feature", "category", "code", "", "", ""),
    ("KLoSA", "regular_exercise", "w__C108", "규칙적 운동 여부", "feature", "category", "code", "", "", ""),
    ("KLoSA", "exercise_frequency", "w__C111", "운동 빈도", "feature_optional", "float", "day/week", 0, 7, ""),
    ("KLoSA", "exercise_duration", "w__C112", "운동 시간", "feature_optional", "float", "minute", 0, 1440, ""),
    (
        "KLoSA",
        "hypertension_dx",
        "w__C006",
        "고혈압 진단 여부",
        "target_source",
        "category",
        "code",
        "",
        "",
        "동시점 입력 금지; t+1 신규진단 타깃 생성에만 사용",
    ),
    (
        "KLoSA",
        "diabetes_dx",
        "w__C011",
        "당뇨병 또는 고혈당 진단 여부",
        "target_source",
        "category",
        "code",
        "",
        "",
        "동시점 입력 금지; t+1 신규진단 타깃 생성에만 사용",
    ),
    (
        "KLoSA",
        "survey_weight",
        "w__wgt_ac",
        "통합 횡단가중치",
        "survey_design",
        "float",
        "weight",
        0,
        "",
        "예측 특성으로 사용 금지",
    ),
    ("KNHANES", "age", "age", "만 나이", "feature", "integer", "year", 19, 120, ""),
    ("KNHANES", "sex", "sex", "성별", "feature", "category", "code", "", "", ""),
    ("KNHANES", "bmi", "HE_BMI", "체질량지수", "feature", "float", "kg/m2", 10, 80, ""),
    ("KNHANES", "waist_cm", "HE_WC", "허리둘레", "feature", "float", "cm", 30, 200, ""),
    ("KNHANES", "current_smoking", "BS3_1", "현재 흡연 여부", "feature", "category", "code", "", "", ""),
    ("KNHANES", "alcohol_frequency", "BD1_11", "1년간 음주 빈도", "feature", "category", "code", "", "", ""),
    ("KNHANES", "aerobic_activity", "pa_aerobic", "유산소 신체활동 실천", "feature", "category", "code", "", "", ""),
    ("KNHANES", "stress_level", "BP1", "평소 스트레스 정도", "feature", "category", "code", "", "", ""),
    (
        "KNHANES",
        "systolic_bp",
        "HE_SBP",
        "최종 수축기혈압",
        "target_component",
        "float",
        "mmHg",
        50,
        300,
        "고혈압 유병 타깃 정의에 포함될 수 있어 입력 금지",
    ),
    (
        "KNHANES",
        "diastolic_bp",
        "HE_DBP",
        "최종 이완기혈압",
        "target_component",
        "float",
        "mmHg",
        30,
        200,
        "고혈압 유병 타깃 정의에 포함될 수 있어 입력 금지",
    ),
    (
        "KNHANES",
        "fasting_glucose",
        "HE_GLU",
        "공복혈당",
        "target_component",
        "float",
        "mg/dL",
        20,
        800,
        "당뇨병 유병 타깃 정의에 포함될 수 있어 입력 금지",
    ),
    (
        "KNHANES",
        "hba1c",
        "HE_HbA1c",
        "당화혈색소",
        "target_component",
        "float",
        "%",
        2,
        25,
        "당뇨병 유병 타깃 정의에 포함될 수 있어 입력 금지",
    ),
    (
        "KNHANES",
        "hypertension_prevalence",
        "HE_HP",
        "고혈압 유병 여부",
        "target",
        "category",
        "code",
        "",
        "",
        "타깃 전용",
    ),
    ("KNHANES", "diabetes_prevalence", "HE_DM", "당뇨병 유병 여부", "target", "category", "code", "", "", "타깃 전용"),
    (
        "KNHANES",
        "survey_weight",
        "wt_itvex",
        "건강설문·검진 가중치",
        "survey_design",
        "float",
        "weight",
        0,
        "",
        "예측 특성으로 사용 금지",
    ),
    (
        "KNHANES",
        "strata",
        "kstrata",
        "분산추정층",
        "survey_design",
        "category",
        "code",
        "",
        "",
        "예측 특성으로 사용 금지",
    ),
    ("KNHANES", "psu", "psu", "조사구", "survey_design", "category", "code", "", "", "예측 특성으로 사용 금지"),
]


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def build_registry(
    klosa_semantic: Path,
    knhanes_semantic: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = {
        "KLoSA": _read(klosa_semantic),
        "KNHANES": _read(knhanes_semantic),
    }
    registry_rows: list[dict[str, object]] = []
    for dataset, canonical, semantic, label, role, dtype, unit, lower, upper, leakage in CURATED_CONCEPTS:
        source = frames[dataset]
        matched = source[source["semantic_column"] == semantic]
        row = matched.iloc[0].to_dict() if not matched.empty else {}
        raw_names = str(row.get("original_column_names", ""))
        source_column = raw_names.split(" | ")[0] if raw_names else ""
        registry_rows.append(
            {
                "dataset": dataset,
                "canonical_name": canonical,
                "semantic_column": semantic,
                "source_column": source_column,
                "source_columns_all": raw_names,
                "concept_label_ko": label,
                "role": role,
                "dtype": dtype,
                "unit": unit,
                "valid_min": lower,
                "valid_max": upper,
                "missing_codes": "",
                "available_waves_or_years": row.get("wave_or_years", ""),
                "merge_method": row.get("merge_method", ""),
                "review_status": "needs_codebook",
                "leakage_or_use_note": leakage,
                "official_source": OFFICIAL_SOURCES[dataset],
                "reviewer": "",
                "reviewed_at": "",
                "codebook_page_or_table": "",
                "review_note": "공식 코드북의 값 라벨·결측코드·단위 확인 전 사용 금지",
            }
        )

    review_frames: list[pd.DataFrame] = []
    for dataset, source in frames.items():
        review = source[source["merge_method"].fillna("") != "single"].copy()
        review.insert(0, "review_priority", "medium")
        label_count = review["variable_labels"].fillna("").str.count(r"\|") + 1
        canonical_count = pd.to_numeric(review["merged_canonical_count"], errors="coerce").fillna(1)
        review.loc[(label_count >= 3) | (canonical_count >= 3), "review_priority"] = "high"
        review.insert(0, "dataset_checked", dataset)
        review["review_status"] = "needs_review"
        review["decision_note"] = ""
        review_frames.append(review)
    return pd.DataFrame(registry_rows), pd.concat(review_frames, ignore_index=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
