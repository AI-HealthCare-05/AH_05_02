"""Official-source preprocessing for KLoSA and KNHANES public-use files.

The two surveys are intentionally processed separately. KNHANES supports
cross-sectional, laboratory-defined screening targets; KLoSA supports
two-year incident diagnosis targets from repeated panel interviews.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

from .pipeline import add_age_cohorts, assign_group_split

WAVE_YEARS = {1: 2006, 2: 2008, 3: 2010, 4: 2012, 5: 2014, 6: 2016, 7: 2018, 8: 2020, 9: 2022, 10: 2024}

KNHANES_FEATURES = [
    "age",
    "sex",
    "region",
    "urban",
    "education",
    "income_quartile",
    "household_income_quartile",
    "height_cm",
    "weight_kg",
    "waist_cm",
    "bmi",
    "hypertension_family_history",
    "diabetes_family_history",
    "current_smoker",
    "alcohol_frequency",
    "aerobic_activity",
    "walking_days",
    "energy_kcal",
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "sodium_mg",
]

KLOSA_FEATURES = [
    "age",
    "sex",
    "bmi",
    "self_rated_health",
    "regular_exercise",
    "current_smoker",
    "current_drinker",
    "meal_count_yesterday",
]


def knhanes_hypertension_codes(year: int) -> tuple[tuple[int, ...], int]:
    """Return official HE_HP valid codes and the hypertension code by year."""
    return ((1, 2, 3, 4), 4) if year >= 2022 else ((1, 2, 3), 3)


def knhanes_diabetes_source(year: int) -> str:
    """Return the official derived diabetes-status variable for a survey year."""
    return "HE_DM_HbA1c" if year >= 2019 else "HE_DM"


def _numeric(series: pd.Series, lower: float | None = None, upper: float | None = None) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if lower is not None:
        values = values.mask(values < lower)
    if upper is not None:
        values = values.mask(values > upper)
    return values


def _codes(series: pd.Series, valid: Iterable[int]) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values.isin(set(valid))).astype("Int64")


def _yes_no(series: pd.Series, *, yes: int = 1, no: int = 0) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    result.loc[values.eq(yes)] = 1
    result.loc[values.eq(no)] = 0
    return result


def _one_five(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    result.loc[values.eq(1)] = 1
    result.loc[values.eq(5)] = 0
    return result


def _family_history(frame: pd.DataFrame, prefix: str) -> pd.Series:
    columns = [f"{prefix}{index}" for index in (1, 2, 3)]
    values = pd.concat([_codes(frame[column], (0, 1)) for column in columns], axis=1)
    result = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    result.loc[values.eq(1).any(axis=1)] = 1
    result.loc[values.notna().any(axis=1) & ~values.eq(1).any(axis=1)] = 0
    return result


def preprocess_knhanes_file(path: Path, year: int) -> pd.DataFrame:
    """Read one official KNHANES ALL DB and create auditable canonical columns."""
    source_columns = [
        "ID",
        "year",
        "age",
        "sex",
        "region",
        "town_t",
        "edu",
        "incm",
        "ho_incm",
        "wt_itvex",
        "kstrata",
        "psu",
        "HE_ht",
        "HE_wt",
        "HE_wc",
        "HE_BMI",
        "HE_HPfh1",
        "HE_HPfh2",
        "HE_HPfh3",
        "HE_DMfh1",
        "HE_DMfh2",
        "HE_DMfh3",
        "sm_presnt",
        "BD1_11",
        "pa_aerobic",
        "BE3_31",
        "HE_sbp",
        "HE_dbp",
        "HE_glu",
        "HE_HbA1c",
        "DI1_dg",
        "DI1_2",
        "DE1_dg",
        "DE1_3",
        "HE_HP",
        "HE_DM",
        "HE_DM_HbA1c",
        "N_EN",
        "N_PROT",
        "N_FAT",
        "N_CHO",
        "N_NA",
    ]
    _, metadata = pyreadstat.read_sav(path, metadataonly=True)
    available = [column for column in source_columns if column in metadata.column_names]
    raw, _ = pyreadstat.read_sav(path, usecols=available, apply_value_formats=False)

    out = pd.DataFrame(index=raw.index)
    out["record_key"] = str(year) + ":" + raw["ID"].astype("string")
    out["survey_year"] = year
    out["age"] = _numeric(raw["age"], 0, 120).astype("Int64")
    out["sex"] = _codes(raw["sex"], (1, 2))
    out["region"] = _codes(raw["region"], range(1, 18))
    out["urban"] = _codes(raw["town_t"], (1, 2))
    out["education"] = _codes(raw["edu"], range(1, 8))
    out["income_quartile"] = _codes(raw["incm"], (1, 2, 3, 4))
    out["household_income_quartile"] = _codes(raw["ho_incm"], (1, 2, 3, 4))
    out["survey_weight"] = _numeric(raw["wt_itvex"], 0)
    out["survey_stratum"] = raw["kstrata"].astype("string")
    out["survey_cluster"] = raw["psu"].astype("string")
    out["height_cm"] = _numeric(raw["HE_ht"], 100, 230)
    out["weight_kg"] = _numeric(raw["HE_wt"], 20, 300)
    out["waist_cm"] = _numeric(raw["HE_wc"], 40, 200)
    out["bmi"] = _numeric(raw["HE_BMI"], 10, 80)
    out["hypertension_family_history"] = _family_history(raw, "HE_HPfh")
    out["diabetes_family_history"] = _family_history(raw, "HE_DMfh")

    # Use the official derived current-smoking indicator. BS3_1 alone is
    # structurally skipped for never-smokers and would create false missingness.
    out["current_smoker"] = _codes(raw["sm_presnt"], (0, 1))
    out["alcohol_frequency"] = _codes(raw["BD1_11"], (1, 2, 3, 4, 5, 6, 8))
    out["aerobic_activity"] = _codes(raw["pa_aerobic"], (0, 1))
    walking = pd.to_numeric(raw["BE3_31"], errors="coerce")
    # Official code 8 means no walking in the previous week, not missing.
    out["walking_days"] = walking.replace(8, 0).where(walking.replace(8, 0).between(0, 7))
    out["energy_kcal"] = _numeric(raw["N_EN"], 0, 15000)
    out["protein_g"] = _numeric(raw["N_PROT"], 0, 1000)
    out["fat_g"] = _numeric(raw["N_FAT"], 0, 1000)
    out["carbohydrate_g"] = _numeric(raw["N_CHO"], 0, 3000)
    out["sodium_mg"] = _numeric(raw["N_NA"], 0, 50000)

    # Target components are retained only for audit and never enter KNHANES_FEATURES.
    out["systolic_bp"] = _numeric(raw["HE_sbp"], 50, 300)
    out["diastolic_bp"] = _numeric(raw["HE_dbp"], 30, 200)
    out["fasting_glucose"] = _numeric(raw["HE_glu"], 20, 800)
    out["hba1c"] = _numeric(raw["HE_HbA1c"], 2, 25)
    out["hypertension_diagnosed"] = _yes_no(raw["DI1_dg"])
    out["diabetes_diagnosed"] = _yes_no(raw["DE1_dg"])
    out["hypertension_medication"] = _yes_no(raw["DI1_2"], yes=1, no=5)
    out["diabetes_medication"] = _yes_no(raw["DE1_3"], yes=1, no=2)

    hp = pd.to_numeric(raw["HE_HP"], errors="coerce")
    hp_valid_codes, hp_positive_code = knhanes_hypertension_codes(year)
    out["hypertension_state"] = hp.where(hp.isin(hp_valid_codes)).astype("Int64")
    out["target_hypertension_clinical"] = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    valid_hp = hp.isin(hp_valid_codes)
    out.loc[valid_hp, "target_hypertension_clinical"] = hp.loc[valid_hp].eq(hp_positive_code).astype(int)

    diabetes_column = knhanes_diabetes_source(year)
    dm = pd.to_numeric(raw[diabetes_column], errors="coerce")
    out["diabetes_state"] = dm.where(dm.isin((1, 2, 3))).astype("Int64")
    out["target_diabetes_clinical"] = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    valid_dm = dm.isin((1, 2, 3))
    out.loc[valid_dm, "target_diabetes_clinical"] = dm.loc[valid_dm].eq(3).astype(int)

    out["eligible_hypertension_undiagnosed"] = (
        out["age"].ge(19) & out["target_hypertension_clinical"].notna() & out["hypertension_diagnosed"].eq(0)
    ).astype("boolean")
    out["eligible_diabetes_undiagnosed"] = (
        out["age"].ge(19) & out["target_diabetes_clinical"].notna() & out["diabetes_diagnosed"].eq(0)
    ).astype("boolean")
    out = add_age_cohorts(out, thresholds=(19, 40, 65))
    out["split"] = np.select(
        [out["survey_year"].le(2020), out["survey_year"].between(2021, 2022)],
        ["train", "validation"],
        default="test",
    )
    return out


def preprocess_knhanes_directory(root: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(root.rglob("*.sav")):
        frames.append(preprocess_knhanes_file(path, int(path.parent.name)))
    if not frames:
        raise FileNotFoundError(f"KNHANES SAV files not found under {root}")
    return pd.concat(frames, ignore_index=True)


def _klosa_source_columns(wave: int, *, new_sample: bool = False) -> dict[str, str]:
    prefix = f"w{wave:02d}"
    # Wave 5 has a separate refresh-sample file. Like the wave-1 baseline,
    # its computed age is stored in A001_age rather than A002_age.
    age = f"{prefix}A001_age" if wave == 1 or new_sample else f"{prefix}A002_age"
    return {
        "pid": "pid",
        "age": age,
        "sex": f"{prefix}gender1",
        "self_rated_health": f"{prefix}C001",
        "weight_kg": f"{prefix}C105",
        "height_cm": f"{prefix}C107",
        "regular_exercise": f"{prefix}C108",
        "smoking_experience": f"{prefix}C116",
        "current_smoker": f"{prefix}C117",
        "current_drinker": f"{prefix}C122",
        "meal_breakfast": f"{prefix}C114m01",
        "meal_lunch": f"{prefix}C114m02",
        "meal_dinner": f"{prefix}C114m03",
        "hypertension_event": f"{prefix}C006",
        "diabetes_event": f"{prefix}C011",
        "panel_weight": f"{prefix}wgt_p",
    }


def preprocess_klosa_wave(path: Path, wave: int) -> pd.DataFrame:
    mapping = _klosa_source_columns(wave, new_sample="_new_" in path.name.lower())
    _, metadata = pyreadstat.read_sav(path, metadataonly=True)
    available_mapping = {key: value for key, value in mapping.items() if value in metadata.column_names}
    required = {"pid", "age", "hypertension_event", "diabetes_event"}
    missing = required.difference(available_mapping)
    if missing:
        raise ValueError(f"{path.name}: required KLoSA columns missing: {sorted(missing)}")
    raw, _ = pyreadstat.read_sav(path, usecols=list(available_mapping.values()), apply_value_formats=False)
    raw = raw.rename(columns={source: key for key, source in available_mapping.items()})
    out = pd.DataFrame(index=raw.index)
    out["participant_id"] = raw["pid"].astype("string")
    out["survey_wave"] = wave
    out["survey_year"] = WAVE_YEARS[wave]
    out["age"] = _numeric(raw["age"], 40, 120).astype("Int64")
    out["sex"] = _codes(raw.get("sex", pd.Series(index=raw.index, dtype=float)), (1, 5))
    out["self_rated_health"] = _codes(
        raw.get("self_rated_health", pd.Series(index=raw.index, dtype=float)), (1, 2, 3, 4, 5)
    )
    out["weight_kg"] = _numeric(raw.get("weight_kg", pd.Series(index=raw.index, dtype=float)), 20, 250)
    out["height_cm"] = _numeric(raw.get("height_cm", pd.Series(index=raw.index, dtype=float)), 100, 220)
    out["bmi"] = out["weight_kg"] / (out["height_cm"] / 100) ** 2
    out["bmi"] = out["bmi"].where(out["bmi"].between(10, 80))
    out["regular_exercise"] = _one_five(raw.get("regular_exercise", pd.Series(index=raw.index, dtype=float)))
    current_smoker = _one_five(raw.get("current_smoker", pd.Series(index=raw.index, dtype=float)))
    smoking_experience = _one_five(raw.get("smoking_experience", pd.Series(index=raw.index, dtype=float)))
    # Early waves skip C117 for respondents without the qualifying smoking
    # experience in C116. Those structural skips are current non-smokers.
    current_smoker = current_smoker.mask(current_smoker.isna() & smoking_experience.eq(0), 0)
    out["current_smoker"] = current_smoker
    out["current_drinker"] = _one_five(raw.get("current_drinker", pd.Series(index=raw.index, dtype=float)))
    meals = []
    for column in ("meal_breakfast", "meal_lunch", "meal_dinner"):
        meals.append(_codes(raw.get(column, pd.Series(index=raw.index, dtype=float)), (0, 1)))
    meal_frame = pd.concat(meals, axis=1)
    out["meal_count_yesterday"] = meal_frame.sum(axis=1, min_count=1).astype("Int64")
    out["hypertension_event"] = _one_five(raw["hypertension_event"])
    out["diabetes_event"] = _one_five(raw["diabetes_event"])
    out["panel_weight"] = _numeric(raw.get("panel_weight", pd.Series(index=raw.index, dtype=float)), 0)
    out["source_file"] = path.name
    return out


def add_klosa_incident_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """Create adjacent-wave incident targets while excluding uncertain histories."""
    result = frame.sort_values(["participant_id", "survey_wave", "source_file"]).copy()
    result = result.drop_duplicates(["participant_id", "survey_wave"], keep="last")
    grouped = result.groupby("participant_id", sort=False, observed=True)
    result["next_wave"] = grouped["survey_wave"].shift(-1)
    result["adjacent_next_wave"] = result["next_wave"].eq(result["survey_wave"] + 1)
    for disease in ("hypertension", "diabetes"):
        event_column = f"{disease}_event"
        event = result[event_column]
        event_observed = event.notna().astype(int)
        history_observed = event_observed.groupby(result["participant_id"], sort=False).cummin().eq(1)
        diagnosed = event.eq(1).fillna(False).astype(int).groupby(result["participant_id"], sort=False).cummax().eq(1)
        next_event = grouped[event_column].shift(-1)
        eligible = history_observed & ~diagnosed & result["adjacent_next_wave"] & next_event.notna()
        target = pd.Series(pd.NA, index=result.index, dtype="Int64")
        target.loc[eligible] = next_event.loc[eligible].astype("Int64")
        result[f"diagnosed_through_wave_{disease}"] = diagnosed.astype("boolean")
        result[f"eligible_{disease}_incident"] = eligible.astype("boolean")
        result[f"target_{disease}_incident_next_wave"] = target
    result = add_age_cohorts(result, thresholds=(19, 40, 65))
    result["split"] = assign_group_split(result, group_column="participant_id")
    return result.reset_index(drop=True)


def preprocess_klosa_directory(root: Path) -> pd.DataFrame:
    frames = []
    for wave in range(1, 11):
        paths = sorted(root.glob(f"w{wave:02d}_*.sav"))
        if wave == 5:
            paths = sorted(root.glob("w05_*.sav"))
        paths = [path for path in paths if not (wave != 5 and "new" in path.name)]
        if not paths:
            raise FileNotFoundError(f"KLoSA wave {wave} file not found under {root}")
        frames.extend(preprocess_klosa_wave(path, wave) for path in paths)
    return add_klosa_incident_targets(pd.concat(frames, ignore_index=True))


def source_manifest(paths: Iterable[Path]) -> pd.DataFrame:
    rows = []
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"file_name": path.name, "bytes": path.stat().st_size, "sha256": digest})
    return pd.DataFrame(rows)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def build_quality_summary(knhanes: pd.DataFrame, klosa: pd.DataFrame) -> dict[str, object]:
    summary: dict[str, object] = {
        "knhanes_rows": int(len(knhanes)),
        "klosa_rows": int(len(klosa)),
        "knhanes_years": sorted(knhanes["survey_year"].unique().tolist()),
        "klosa_waves": sorted(klosa["survey_wave"].unique().tolist()),
        "knhanes_cohorts": {str(t): int(knhanes[f"cohort_{t}_plus"].sum()) for t in (19, 40, 65)},
        "klosa_population_rows": int(len(klosa)),
        "klosa_65_plus_rows": int(klosa["cohort_65_plus"].sum()),
    }
    for disease in ("hypertension", "diabetes"):
        kn_eligible = knhanes[f"eligible_{disease}_undiagnosed"].fillna(False)
        kl_eligible = klosa[f"eligible_{disease}_incident"].fillna(False)
        summary[f"knhanes_{disease}_eligible"] = int(kn_eligible.sum())
        summary[f"knhanes_{disease}_positive"] = int(knhanes.loc[kn_eligible, f"target_{disease}_clinical"].sum())
        summary[f"klosa_{disease}_eligible"] = int(kl_eligible.sum())
        summary[f"klosa_{disease}_positive"] = int(klosa.loc[kl_eligible, f"target_{disease}_incident_next_wave"].sum())
    return summary


def build_cohort_quality_table(knhanes: pd.DataFrame, klosa: pd.DataFrame) -> pd.DataFrame:
    """Summarize comparable modeling populations without merging survey rows."""
    rows: list[dict[str, object]] = []
    for disease in ("hypertension", "diabetes"):
        for threshold in (19, 40, 65):
            mask = knhanes[f"cohort_{threshold}_plus"].fillna(False) & knhanes[
                f"eligible_{disease}_undiagnosed"
            ].fillna(False)
            selected = knhanes.loc[mask]
            positive = int(selected[f"target_{disease}_clinical"].sum())
            rows.append(
                {
                    "dataset": "KNHANES",
                    "target_definition": "undiagnosed",
                    "disease": disease,
                    "age_group": f"{threshold}+",
                    "rows": int(len(selected)),
                    "positive": positive,
                    "prevalence": positive / len(selected) if len(selected) else np.nan,
                    "train_rows": int(selected["split"].eq("train").sum()),
                    "validation_rows": int(selected["split"].eq("validation").sum()),
                    "test_rows": int(selected["split"].eq("test").sum()),
                }
            )

        mask = klosa[f"eligible_{disease}_incident"].fillna(False)
        selected = klosa.loc[mask]
        positive = int(selected[f"target_{disease}_incident_next_wave"].sum())
        rows.append(
            {
                "dataset": "KLoSA",
                "target_definition": "incident",
                "disease": disease,
                "age_group": "survey_population",
                "rows": int(len(selected)),
                "positive": positive,
                "prevalence": positive / len(selected) if len(selected) else np.nan,
                "train_rows": int(selected["split"].eq("train").sum()),
                "validation_rows": int(selected["split"].eq("validation").sum()),
                "test_rows": int(selected["split"].eq("test").sum()),
            }
        )
    return pd.DataFrame(rows)


def build_missingness_table(knhanes: pd.DataFrame, klosa: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dataset, frame, features in (
        ("KNHANES", knhanes, KNHANES_FEATURES),
        ("KLoSA", klosa, KLOSA_FEATURES),
    ):
        analysis_frame = frame.loc[frame["age"].ge(19)]
        for column in features:
            missing = int(analysis_frame[column].isna().sum())
            rows.append(
                {
                    "dataset": dataset,
                    "canonical_name": column,
                    "population": "age_19_plus",
                    "rows": int(len(analysis_frame)),
                    "missing_count": missing,
                    "missing_rate": missing / len(analysis_frame),
                }
            )
    return pd.DataFrame(rows)


def build_selected_variable_registry() -> pd.DataFrame:
    """Return the reviewed variable map used by this official pipeline."""
    rows: list[dict[str, str]] = []

    kn_sources = {
        "age": "age",
        "sex": "sex",
        "region": "region",
        "urban": "town_t",
        "education": "edu",
        "income_quartile": "incm",
        "household_income_quartile": "ho_incm",
        "height_cm": "HE_ht",
        "weight_kg": "HE_wt",
        "waist_cm": "HE_wc",
        "bmi": "HE_BMI",
        "hypertension_family_history": "HE_HPfh1|HE_HPfh2|HE_HPfh3",
        "diabetes_family_history": "HE_DMfh1|HE_DMfh2|HE_DMfh3",
        "current_smoker": "sm_presnt",
        "alcohol_frequency": "BD1_11",
        "aerobic_activity": "pa_aerobic",
        "walking_days": "BE3_31",
        "energy_kcal": "N_EN",
        "protein_g": "N_PROT",
        "fat_g": "N_FAT",
        "carbohydrate_g": "N_CHO",
        "sodium_mg": "N_NA",
        "target_hypertension_clinical": "HE_HP",
        "target_diabetes_clinical": "HE_DM (2016-2018)|HE_DM_HbA1c (2019-2024)",
        "hypertension_diagnosed": "DI1_dg",
        "diabetes_diagnosed": "DE1_dg",
        "survey_weight": "wt_itvex",
        "survey_stratum": "kstrata",
        "survey_cluster": "psu",
        "systolic_bp": "HE_sbp",
        "diastolic_bp": "HE_dbp",
        "fasting_glucose": "HE_glu",
        "hba1c": "HE_HbA1c",
    }
    leakage = {
        "systolic_bp",
        "diastolic_bp",
        "fasting_glucose",
        "hba1c",
        "hypertension_diagnosed",
        "diabetes_diagnosed",
    }
    for canonical, source in kn_sources.items():
        role = "feature"
        note = "공식 코드북 확인; 변수별 허용값·범위 적용"
        if canonical.startswith("target_"):
            role, note = "target", "공식 파생 질환상태 변수; 모델 입력 금지"
        elif canonical.startswith("survey_"):
            role, note = "survey_design", "복합표본 설계·가중 평가용"
        elif canonical in leakage:
            role, note = "target_component", "타깃 정의/적합성 확인 전용; 모델 입력 금지"
        rows.append(
            {
                "dataset": "KNHANES",
                "canonical_name": canonical,
                "source_column": source,
                "role": role,
                "unit": {
                    "height_cm": "cm",
                    "weight_kg": "kg",
                    "waist_cm": "cm",
                    "bmi": "kg/m2",
                    "energy_kcal": "kcal/day",
                    "protein_g": "g/day",
                    "fat_g": "g/day",
                    "carbohydrate_g": "g/day",
                    "sodium_mg": "mg/day",
                    "systolic_bp": "mmHg",
                    "diastolic_bp": "mmHg",
                    "fasting_glucose": "mg/dL",
                    "hba1c": "%",
                }.get(canonical, "code"),
                "applicable_period": "2016-2024",
                "missing_rule": "공식 무응답/비해당 및 허용범위 밖 값을 NA로 변환",
                "model_input": "no" if role != "feature" else "yes",
                "review_status": "approved",
                "notes": note,
            }
        )

    kl_sources = {
        "age": "w01A001_age; w02-10A002_age; w05_newA001_age",
        "sex": "wXXgender1",
        "bmi": "wXXC105,wXXC107 (계산)",
        "self_rated_health": "wXXC001",
        "regular_exercise": "wXXC108",
        "current_smoker": "wXXC116+wXXC117",
        "current_drinker": "wXXC122",
        "meal_count_yesterday": "wXXC114m01-m03",
        "hypertension_event": "wXXC006",
        "diabetes_event": "wXXC011",
        "panel_weight": "wXXwgt_p",
        "target_hypertension_incident_next_wave": "다음 인접 차수 wXXC006",
        "target_diabetes_incident_next_wave": "다음 인접 차수 wXXC011",
    }
    for canonical, source in kl_sources.items():
        role = "feature"
        note = "차수별 공식 변수명 확인; -8/-9 및 비허용 코드를 NA로 변환"
        if canonical.endswith("_event"):
            role, note = "target_component", "과거 진단 배제·다음 차수 발생 타깃 생성 전용"
        elif canonical.startswith("target_"):
            role, note = "target", "인접한 다음 조사차수의 신규 진단; 모델 입력 금지"
        elif canonical == "panel_weight":
            role, note = "survey_design", "패널 가중 평가용"
        rows.append(
            {
                "dataset": "KLoSA",
                "canonical_name": canonical,
                "source_column": source,
                "role": role,
                "unit": "kg/m2" if canonical == "bmi" else "code",
                "applicable_period": "1-10차 (2006-2024)",
                "missing_rule": "-8 거절, -9 모름 및 비허용 코드를 NA로 변환",
                "model_input": "yes" if role == "feature" else "no",
                "review_status": "approved",
                "notes": note,
            }
        )
    return pd.DataFrame(rows)


def save_summary(summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
