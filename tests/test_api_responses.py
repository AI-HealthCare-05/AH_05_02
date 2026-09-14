from app.apis.responses import error_detail


def test_error_detail_has_shared_contract() -> None:
    assert error_detail("PREDICTION_NOT_FOUND", "예측 결과를 찾을 수 없습니다.") == {
        "error_code": "PREDICTION_NOT_FOUND",
        "message": "예측 결과를 찾을 수 없습니다.",
        "retryable": False,
    }


def test_error_detail_can_mark_retryable_failure() -> None:
    assert error_detail("QUEUE_UNAVAILABLE", "작업 큐에 연결할 수 없습니다.", retryable=True)["retryable"] is True
