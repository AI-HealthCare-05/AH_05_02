"""Read-only local artifact audit and warm inference benchmark; prints JSON."""

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ml.inference import research_models as models  # noqa: E402


def timed(call):
    start = perf_counter()
    value = call()
    return value, (perf_counter() - start) * 1000


def measure(call, repeats):
    samples = [timed(call)[1] for _ in range(repeats)]
    return {"median_ms": float(np.median(samples)), "p95_ms": float(np.percentile(samples, 95))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today-artifact", required=True)
    parser.add_argument("--tomorrow-artifact", required=True)
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("repeats must be >= 2")
    payload = json.loads((ROOT / "docs/api/examples/tuned_rf25_valid_input.json").read_text())
    day = date(2026, 8, 31)
    report = {
        "repeats": args.repeats,
        "as_of_date": str(day),
        "scope": "local process; excludes queue, Redis, DB, HTTP",
    }
    for name, key, path, loader in (
        ("today", "shared8-waist", args.today_artifact, models.load_shared8),
        ("tomorrow", "tomorrow-rf25", args.tomorrow_artifact, models.load_tomorrow_rf25),
    ):
        loaded, load_ms = timed(lambda loader=loader, path=path: loader(path))
        manifest = loaded[1] if name == "today" else loaded.manifest
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert digest == manifest["artifact_sha256"]

        def basic(name=name, loaded=loaded):
            if name == "today":
                frame = models.shared8_frame(payload, as_of_date=day)
                bundle = loaded[0]
                result = 0.0
                for component, weight in bundle["ensemble_weights"].items():
                    raw = np.clip(bundle["pipelines"][component].predict_proba(frame)[:, 1], 1e-6, 1 - 1e-6)
                    result += (
                        weight
                        * bundle["calibrators"][component].predict_proba(np.log(raw / (1 - raw)).reshape(-1, 1))[0, 1]
                    )
                return float(result)
            _, frame = models.validated_input(payload, day)
            return float(loaded.pipeline.predict_proba(frame)[0, 1])

        def full(key=key, path=path):
            return models.predict_research_model(key, payload, as_of_date=day, model_path=path)

        first, first_ms = timed(full)
        assert first == full()
        assert first["explanation"]["additivity_verified"]
        assert abs(basic() - first["explanation"]["score"]) < 1e-10
        raw = manifest["test"] if name == "today" else manifest["metrics"]["confusion_matrix"]
        tp, fn, tn, fp = [
            raw[k]
            for k in (
                ("tp", "fn", "tn", "fp")
                if name == "today"
                else ("true_positive", "false_negative", "true_negative", "false_positive")
            )
        ]
        report[name] = {
            "model_version": manifest["model_version"],
            "sha256": digest,
            "hash_verified": True,
            "manifest_promotion_status": manifest["promotion_status"],
            "operational_model_activated": manifest["operational_model_activated"],
            "features": manifest["features"],
            "supported_population": manifest["supported_population"],
            "thresholds": manifest.get("thresholds", {"signal": manifest.get("threshold")}),
            "confusion_matrix": {"tp": tp, "fn": fn, "tn": tn, "fp": fp},
            "metrics_from_stored_counts": {
                "recall": tp / (tp + fn),
                "specificity": tn / (tn + fp),
                "ppv": tp / (tp + fp),
                "npv": tn / (tn + fn),
                "positive_rate": (tp + fp) / (tp + fn + tn + fp),
            },
            "artifact_load_ms": load_ms,
            "first_full_call_ms": first_ms,
            "basic_inference": measure(basic, args.repeats),
            "with_xai": measure(full, args.repeats),
            "fixed_input_reproducible": True,
            "explanation": first["explanation"],
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
