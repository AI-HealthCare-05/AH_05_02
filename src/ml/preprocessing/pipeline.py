from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


APPROVED = {"approved", "approved_with_note"}
MODEL_FEATURE_ROLES = {"feature", "feature_optional"}


def _parse_codes(value: object) -> list[object]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    parsed: list[object] = []
    for token in str(value).split("|"):
        token = token.strip()
        if not token:
            continue
        try:
            number = float(token)
            parsed.append(int(number) if number.is_integer() else number)
        except ValueError:
            parsed.append(token)
    return parsed


def clean_with_registry(
    raw: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    require_approved: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map, type and range-check variables using an auditable registry.

    Values outside a documented range are set to missing in the derived copy and
    counted in the returned audit table. No global missing-code heuristic is used.
    """
    required = {
        "canonical_name",
        "source_column",
        "dtype",
        "missing_codes",
        "valid_min",
        "valid_max",
        "review_status",
    }
    missing = required.difference(registry.columns)
    if missing:
        raise ValueError(f"레지스트리 필수 컬럼 누락: {sorted(missing)}")

    selected = registry.copy()
    if require_approved:
        selected = selected[selected["review_status"].isin(APPROVED)]
    if selected.empty:
        raise ValueError("공식 코드북 검토 후 approved 처리된 변수가 없습니다.")

    output: dict[str, pd.Series] = {}
    audit_rows: list[dict[str, object]] = []
    for row in selected.to_dict("records"):
        canonical = str(row["canonical_name"])
        source = str(row["source_column"])
        if source not in raw.columns:
            audit_rows.append(
                {
                    "canonical_name": canonical,
                    "source_column": source,
                    "status": "missing_source_column",
                    "missing_code_count": 0,
                    "out_of_range_count": 0,
                }
            )
            continue

        series = raw[source].copy()
        codes = _parse_codes(row.get("missing_codes"))
        missing_mask = series.isin(codes) if codes else pd.Series(False, index=series.index)
        series = series.mask(missing_mask)

        dtype = str(row.get("dtype", "string")).lower()
        out_of_range = pd.Series(False, index=series.index)
        if dtype in {"float", "numeric", "integer", "int"}:
            series = pd.to_numeric(series, errors="coerce")
            lower = pd.to_numeric(pd.Series([row.get("valid_min")]), errors="coerce").iloc[0]
            upper = pd.to_numeric(pd.Series([row.get("valid_max")]), errors="coerce").iloc[0]
            if pd.notna(lower):
                out_of_range |= series < float(lower)
            if pd.notna(upper):
                out_of_range |= series > float(upper)
            series = series.mask(out_of_range)
            if dtype in {"integer", "int"}:
                series = series.astype("Int64")
        elif dtype in {"category", "categorical", "string"}:
            series = series.astype("string")
        elif dtype in {"boolean", "bool"}:
            series = series.astype("boolean")
        else:
            raise ValueError(f"지원하지 않는 dtype: {dtype} ({canonical})")

        output[canonical] = series
        audit_rows.append(
            {
                "canonical_name": canonical,
                "source_column": source,
                "status": "processed",
                "missing_code_count": int(missing_mask.sum()),
                "out_of_range_count": int(out_of_range.sum()),
            }
        )

    return pd.DataFrame(output, index=raw.index), pd.DataFrame(audit_rows)


def add_age_cohorts(
    df: pd.DataFrame,
    *,
    age_column: str = "age",
    thresholds: Iterable[int] = (19, 40, 65),
) -> pd.DataFrame:
    if age_column not in df.columns:
        raise ValueError(f"연령 컬럼이 없습니다: {age_column}")
    result = df.copy()
    age = pd.to_numeric(result[age_column], errors="coerce")
    for threshold in thresholds:
        result[f"cohort_{threshold}_plus"] = age.ge(threshold).astype("boolean")
    return result


def validate_cohort_coverage(
    df: pd.DataFrame,
    *,
    dataset: str,
    age_column: str = "age",
    thresholds: Iterable[int] = (19, 40, 65),
) -> pd.DataFrame:
    age = pd.to_numeric(df[age_column], errors="coerce")
    rows: list[dict[str, object]] = []
    previous_mask: pd.Series | None = None
    for threshold in thresholds:
        mask = age.ge(threshold)
        same_as_previous = bool(previous_mask is not None and mask.equals(previous_mask))
        rows.append(
            {
                "dataset": dataset,
                "cohort": f"{threshold}+",
                "row_count": int(mask.sum()),
                "age_min_observed": float(age[mask].min()) if mask.any() else np.nan,
                "age_max_observed": float(age[mask].max()) if mask.any() else np.nan,
                "same_as_previous_cohort": same_as_previous,
                "warning": (
                    "직전 코호트와 표본이 동일하여 별도 모델 비교 의미가 낮음"
                    if same_as_previous
                    else ""
                ),
            }
        )
        previous_mask = mask
    return pd.DataFrame(rows)


def _stable_fraction(value: object, seed: str) -> float:
    digest = hashlib.sha256(f"{seed}|{value}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def assign_group_split(
    df: pd.DataFrame,
    *,
    group_column: str,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    seed: str = "chronic-disease-v1",
) -> pd.Series:
    """Assign all rows of one person/group to exactly one split."""
    if group_column not in df.columns:
        raise ValueError(f"그룹 컬럼이 없습니다: {group_column}")
    if not 0 < train_fraction < 1 or not 0 <= validation_fraction < 1:
        raise ValueError("분할 비율이 올바르지 않습니다.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation 비율은 1보다 작아야 합니다.")
    fractions = df[group_column].astype("string").map(lambda value: _stable_fraction(value, seed))
    split = pd.Series("test", index=df.index, dtype="string")
    split.loc[fractions < train_fraction] = "train"
    split.loc[
        (fractions >= train_fraction)
        & (fractions < train_fraction + validation_fraction)
    ] = "validation"
    return split


def build_klosa_incident_targets(
    df: pd.DataFrame,
    *,
    person_column: str,
    wave_column: str,
    disease_columns: Iterable[str] = ("hypertension_dx", "diabetes_dx"),
) -> pd.DataFrame:
    """Create t -> next observed wave incident labels without row leakage."""
    required = {person_column, wave_column, *disease_columns}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"KLoSA 종단 타깃 생성 컬럼 누락: {sorted(missing)}")
    result = df.sort_values([person_column, wave_column]).copy()
    grouped = result.groupby(person_column, sort=False, observed=True)
    result["next_wave"] = grouped[wave_column].shift(-1)
    for disease in disease_columns:
        current = pd.to_numeric(result[disease], errors="coerce")
        following = pd.to_numeric(grouped[disease].shift(-1), errors="coerce")
        eligible = current.eq(0) & following.notna()
        target = pd.Series(pd.NA, index=result.index, dtype="Int64")
        target.loc[eligible] = following.loc[eligible].eq(1).astype("int64")
        result[f"target_{disease}_incident_next_wave"] = target
        result[f"eligible_{disease}_incident"] = eligible.astype("boolean")
    return result.sort_index()


@dataclass(frozen=True)
class PreprocessingState:
    numeric_medians: Mapping[str, float]
    categorical_modes: Mapping[str, str]
    categorical_levels: Mapping[str, list[str]]

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    "numeric_medians": self.numeric_medians,
                    "categorical_modes": self.categorical_modes,
                    "categorical_levels": self.categorical_levels,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def fit_preprocessing_state(
    train: pd.DataFrame,
    *,
    numeric_columns: Iterable[str],
    categorical_columns: Iterable[str],
) -> PreprocessingState:
    """Fit imputation/categories on training rows only."""
    medians: dict[str, float] = {}
    modes: dict[str, str] = {}
    levels: dict[str, list[str]] = {}
    for column in numeric_columns:
        values = pd.to_numeric(train[column], errors="coerce")
        medians[column] = float(values.median())
    for column in categorical_columns:
        values = train[column].astype("string")
        mode = values.mode(dropna=True)
        modes[column] = str(mode.iloc[0]) if not mode.empty else "__MISSING__"
        observed = sorted(values.dropna().astype(str).unique().tolist())
        levels[column] = observed + [
            level for level in ("__MISSING__", "__UNKNOWN__") if level not in observed
        ]
    return PreprocessingState(medians, modes, levels)


def transform_model_matrix(
    df: pd.DataFrame,
    state: PreprocessingState,
) -> pd.DataFrame:
    """Apply train-fitted imputation and stable one-hot categories."""
    blocks: list[pd.DataFrame] = []
    numeric = pd.DataFrame(index=df.index)
    for column, median in state.numeric_medians.items():
        values = pd.to_numeric(df[column], errors="coerce")
        numeric[f"{column}__missing"] = values.isna().astype("int8")
        numeric[column] = values.fillna(median)
    blocks.append(numeric)
    for column, mode in state.categorical_modes.items():
        values = df[column].astype("string").fillna(mode)
        levels = state.categorical_levels[column]
        values = values.where(values.isin(levels), "__UNKNOWN__")
        cat = pd.Categorical(values, categories=levels)
        dummies = pd.get_dummies(cat, prefix=column, dtype="int8")
        dummies.index = df.index
        blocks.append(dummies)
    return pd.concat(blocks, axis=1)
