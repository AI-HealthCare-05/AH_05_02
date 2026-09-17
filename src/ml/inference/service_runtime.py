"""Preloaded Today14/RF25 inference without ancillary age curves.

Construct once per Worker process at startup. Reuse for subsequent requests.
Caller owns HTTP errors and retry policy; input ValueError is not retryable.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import date
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from src.ml.preprocessing.diabetes_api_features import build_standard_model_frame, parse_diabetes_risk_input
from src.ml.preprocessing.today_api_features import build_today_model_frame, parse_today_risk_input


class ServiceModelRuntime:
    def __init__(self, manifest_path: Path, artifact_path: Path, *, serial=True):
        started = perf_counter()
        if sklearn.__version__ != "1.8.0":
            raise ValueError("scikit-learn 1.8.0 required")
        self.manifest = json.loads(manifest_path.read_text())
        if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != self.manifest["artifact_sha256"]:
            raise ValueError("Artifact checksum mismatch")
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            self.bundle = joblib.load(artifact_path)
        if self.bundle["features"] != self.manifest["features"]:
            raise ValueError("Feature order mismatch")
        expected = self.manifest.get("threshold", self.manifest.get("thresholds", {}).get("high"))
        if self.bundle["threshold"] != expected:
            raise ValueError("Threshold mismatch")
        self.shared = self.manifest["model_key"] == "diabetes_current_screening"
        pipes = self.bundle["pipelines"].values() if self.shared else [self.bundle["pipeline"]]
        if serial:
            for pipe in pipes:
                pipe.set_params(**{key: 1 for key in pipe.get_params() if key.endswith("__n_jobs")})
        self.load_ms = (perf_counter() - started) * 1000

    def predict(self, payload: dict, *, as_of_date: date):
        start = perf_counter()
        if self.shared:
            user = parse_today_risk_input(payload)
            frame = build_today_model_frame(user, as_of_date=as_of_date)
        else:
            user = parse_diabetes_risk_input(payload)
            frame = build_standard_model_frame(user, as_of_date=as_of_date)
        mapped = perf_counter()
        preprocessing_ms = 0.0
        inference_ms = 0.0
        score = 0.0
        pipes = self.bundle["pipelines"] if self.shared else {"rf": self.bundle["pipeline"]}
        for name, pipe in pipes.items():
            t = perf_counter()
            transformed = frame
            for _, transformer in pipe.steps[:-1]:
                transformed = transformer.transform(transformed)
            preprocessing_ms += (perf_counter() - t) * 1000
            t = perf_counter()
            p = pipe.steps[-1][1].predict_proba(transformed)[:, 1]
            if self.shared:
                p = np.clip(p, 1e-6, 1 - 1e-6)
                p = self.bundle["calibrators"][name].predict_proba(np.log(p / (1 - p)).reshape(-1, 1))[:, 1]
                score += self.bundle["ensemble_weights"][name] * float(p[0])
            else:
                score = float(p[0])
            inference_ms += (perf_counter() - t) * 1000
        threshold = float(self.bundle["threshold"])
        category = (
            None
            if self.shared
            else "high"
            if score >= threshold
            else "moderate"
            if score >= self.manifest["thresholds"]["moderate"]
            else "low"
        )
        result = dict(
            score=round(score, 15),
            signal=score >= threshold,
            category=category,
            model_version=self.manifest["model_version"],
            threshold_version=self.manifest["threshold_version"],
        )
        times = dict(
            input_mapping_ms=(mapped - start) * 1000,
            preprocessing_ms=preprocessing_ms,
            inference_and_calibration_ms=inference_ms,
            long_term_curve_ms=0.0,
            total_ms=(perf_counter() - start) * 1000,
        )
        return result, times
