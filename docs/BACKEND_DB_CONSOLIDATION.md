# Backend and DB consolidation

## Canonical locations

- The production FastAPI application is `app/`.
- Redis worker code is `ai_worker/`.
- `src/backend/` is a legacy prototype and is not a deployment target.

## Prediction persistence contract

`prediction_jobs` is the single durable record for asynchronous prediction work.
The API contract continues to expose the general `/api/v1/ai-jobs` endpoints,
while diabetes-risk requests use `/api/v1/prediction-jobs`.

Persist only the minimum operational history: job status, timestamps, model key
and version, feature schema version, threshold version, retry metadata, linked
checkup and prediction IDs, and a safe error code/message. Do not persist raw
individual risk probabilities for public display before approval.

Migration 5 bootstraps `prediction_jobs` for a fresh database. Any production
conversion from a legacy `ai_jobs` table must be separately reviewed for data
migration and rollback before it is applied.

Migration 6 adds immutable prediction provenance: input schema, preprocessing,
target definition, calibration, artifact digest, internal class probabilities,
output status, and nullable decision threshold. Wearable-derived health input is
explicitly deferred to the next version.

## Prediction and risk factors

`predictions` stores the approved or development-only result audit trail.
The public risk-factor endpoint stays unavailable until a reviewed explanation
method and a `risk_factors` persistence contract are approved. No unreviewed
SHAP or personal explanation values are stored or shown.
