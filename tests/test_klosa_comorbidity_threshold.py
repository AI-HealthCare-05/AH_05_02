import pandas as pd

from src.ml.modeling.klosa_comorbidity_threshold import _normalize_id, feature_sets


def test_feature_sets_have_eight_and_sixteen_inputs() -> None:
    sets = feature_sets()
    assert sum(map(len, sets["core_8"].values())) == 8
    assert sum(map(len, sets["core_8_plus_t0_comorbidity_8"].values())) == 16


def test_normalize_id_matches_decimal_and_integer_forms() -> None:
    values = pd.Series(["10001.0", 10002, None])
    assert _normalize_id(values).tolist() == ["10001", "10002", pd.NA]
