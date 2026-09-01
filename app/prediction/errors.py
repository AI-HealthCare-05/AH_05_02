from __future__ import annotations


class ModelNotReadyError(RuntimeError):
    """No approved/active model is registered for the requested model_key yet.

    Raised at job-creation time (before enqueueing) so the caller gets an
    immediate, honest answer instead of a job that would only fail later in
    the worker. Maps to HTTP 503 / error_code MODEL_NOT_READY.
    """


def classify_ml_input_error(exc: Exception) -> str:
    message = str(exc)
    if "invalid diabetes risk input" in message or "required" in message or "ML_INPUT_MISSING" in message:
        return "ML_INPUT_MISSING"
    if "outside the model-supported range" in message:
        return "ML_POPULATION_UNSUPPORTED"
    if "ineligible for an incidence" in message:
        return "ML_POPULATION_INELIGIBLE"
    return "ML_INPUT_OUT_OF_RANGE"
