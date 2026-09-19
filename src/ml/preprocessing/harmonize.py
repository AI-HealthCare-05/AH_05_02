from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from .pipeline import APPROVED

DEFAULT_KLOSA_WAVE_YEARS = {
    1: 2006,
    2: 2008,
    3: 2010,
    4: 2012,
    5: 2014,
    6: 2016,
    7: 2018,
    8: 2020,
    9: 2022,
    10: 2024,
}


def split_aliases(value: object) -> list[str]:
    return [item.strip() for item in str(value or "").split("|") if item.strip()]


def _coalesce_with_conflict_check(
    raw: pd.DataFrame,
    columns: Iterable[str],
    *,
    canonical_name: str,
) -> tuple[pd.Series, int]:
    available = [column for column in columns if column in raw.columns]
    if not available:
        return pd.Series(pd.NA, index=raw.index, dtype="object"), 0
    values = raw[available].copy()
    conflicts = 0
    if len(available) > 1:
        normalized = values.astype("string")
        conflicts = int(normalized.nunique(axis=1, dropna=True).gt(1).sum())
        if conflicts:
            raise ValueError(
                f"{canonical_name}: 같은 개념 후보 컬럼 {available} 사이에 "
                f"{conflicts}개 행의 값 충돌이 있습니다. 자동 병합하지 않습니다."
            )
    return values.bfill(axis=1).iloc[:, 0], conflicts


def approved_registry(registry: pd.DataFrame, dataset: str) -> pd.DataFrame:
    selected = registry[(registry["dataset"] == dataset) & registry["review_status"].isin(APPROVED)].copy()
    if selected.empty:
        raise ValueError(f"{dataset}: 코드북 승인 변수가 없어 전처리를 중단합니다.")
    return selected


def harmonize_knhanes(
    raw: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    survey_year: int,
    source_file: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = approved_registry(registry, "KNHANES")
    output = pd.DataFrame(index=raw.index)
    audit: list[dict[str, object]] = []
    for row in selected.to_dict("records"):
        aliases = split_aliases(row["source_columns_all"])
        present = [alias for alias in aliases if alias in raw.columns]
        series, conflicts = _coalesce_with_conflict_check(raw, aliases, canonical_name=str(row["canonical_name"]))
        output[str(row["canonical_name"])] = series
        audit.append(
            {
                "dataset": "KNHANES",
                "survey_year": survey_year,
                "canonical_name": row["canonical_name"],
                "present_source_columns": " | ".join(present),
                "status": "mapped" if present else "missing_in_year",
                "conflict_count": conflicts,
            }
        )
    output.insert(0, "source_row_number", range(1, len(output) + 1))
    output.insert(0, "source_file", source_file)
    output.insert(0, "survey_year", survey_year)
    output.insert(
        0,
        "record_key",
        [f"KNHANES:{survey_year}:{source_file}:{i}" for i in range(1, len(output) + 1)],
    )
    return output, pd.DataFrame(audit)


def harmonize_klosa_wide(
    raw: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    person_column: str,
    wave_year_map: Mapping[int, int] = DEFAULT_KLOSA_WAVE_YEARS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if person_column not in raw.columns:
        raise ValueError(f"KLoSA 개인 식별 컬럼이 없습니다: {person_column}")
    selected = approved_registry(registry, "KLoSA")
    waves: list[pd.DataFrame] = []
    audit: list[dict[str, object]] = []
    for wave, year in wave_year_map.items():
        prefix = f"w{wave:02d}"
        frame = pd.DataFrame({"participant_id": raw[person_column]})
        frame["survey_wave"] = wave
        frame["survey_year"] = year
        for row in selected.to_dict("records"):
            aliases = [
                alias for alias in split_aliases(row["source_columns_all"]) if alias.lower().startswith(prefix.lower())
            ]
            present = [alias for alias in aliases if alias in raw.columns]
            series, conflicts = _coalesce_with_conflict_check(
                raw, aliases, canonical_name=f"wave {wave} / {row['canonical_name']}"
            )
            frame[str(row["canonical_name"])] = series
            audit.append(
                {
                    "dataset": "KLoSA",
                    "survey_wave": wave,
                    "survey_year": year,
                    "canonical_name": row["canonical_name"],
                    "present_source_columns": " | ".join(present),
                    "status": "mapped" if present else "missing_in_wave",
                    "conflict_count": conflicts,
                }
            )
        waves.append(frame)
    long = pd.concat(waves, ignore_index=True)
    return long, pd.DataFrame(audit)
