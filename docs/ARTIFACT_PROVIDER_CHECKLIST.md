# Artifact Provider connection checklist

`PREDICTION_PROVIDER=artifact` is intentionally unavailable until every item
below is supplied and reviewed. Model binaries and raw health data must not be
committed to Git.

## Required handoff

- A provider URI or mounted local path outside Git.
- SHA-256 digest of the exact artifact (`model_artifact_digest`).
- Model version, input schema version, preprocessing version, target definition
  version, calibration version, and threshold version.
- The exact eight input field names, order, data types, and categorical encoding.
- Confirmation that preprocessing is bundled with the artifact, or a separate
  versioned preprocessing artifact.
- Whether `predict_proba` is available, and the approved decision threshold.
- Approval status for displaying a risk category. Until approved, the API keeps
  `decision_threshold`, `risk_category`, and `risk_category_label` null.

## Persistence contract

- `prediction_jobs` stores the requested model provenance before queueing.
- `predictions` stores the provenance actually used, internal-only class
  probabilities when available, and `output_status`.
- No `risk_factors` record is created until an explanation method and its
  `explanation_version` are reviewed.
