from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".parquet", ".dta", ".sav", ".zsav"}


def read_tabular(path: str | Path) -> pd.DataFrame:
    """Read a supported public-use research file without modifying it."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {source}")
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"지원하지 않는 형식입니다: {suffix}")
    if suffix == ".csv":
        return pd.read_csv(source, encoding="utf-8-sig", low_memory=False)
    if suffix == ".parquet":
        return pd.read_parquet(source)
    if suffix == ".dta":
        return pd.read_stata(source, convert_categoricals=False)
    return pd.read_spss(source, convert_categoricals=False)


def write_processed(df: pd.DataFrame, path: str | Path) -> None:
    """Write a derived table; raw input paths must never be passed here."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".csv":
        df.to_csv(destination, index=False, encoding="utf-8-sig")
    elif destination.suffix.lower() == ".parquet":
        df.to_parquet(destination, index=False)
    else:
        raise ValueError("처리 결과는 .csv 또는 .parquet로만 저장합니다.")
