from pathlib import Path

from app.main import app
from app.prediction.contracts import ACTIVE_MODEL

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_entrypoint_uses_formal_application() -> None:
    from src.backend.main import app as compatibility_app

    assert compatibility_app is app
    paths = app.openapi()["paths"]
    assert "/api/v1/prediction-jobs" in paths
    assert "/api/v1/ai-jobs" not in paths


def test_home_has_accessibility_and_medical_notice() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "본문으로 바로가기" in html
    assert "진단·처방" in html
    assert "간당간당 개발용 서비스" in html
    assert "DEVELOPMENT" not in html
    assert "확률 비공개" not in html
    assert "약을 끊으세요" not in html + script
    assert "약을 시작하세요" not in html + script


def test_reviewed_eligibility_and_failure_guidance_is_user_specific() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src/frontend/styles.css").read_text(encoding="utf-8")

    for screen_code in ("E02", "E03", "D01", "E05"):
        assert screen_code in script
    for reason_code in (
        "UNDER_MINIMUM_SERVICE_AGE",
        "URGENT_MEDICAL_ATTENTION",
        "DIAGNOSED_DIABETES",
        "MODEL_AGE_OUT_OF_RANGE",
    ):
        assert reason_code in script
    assert "분석 실패는 당뇨병 위험도가 높다는 의미가 아닙니다." in html
    assert "입력정보 확인하기" in html
    assert "다시 시도하기" in html
    assert "증상이 있으면 의료기관 안내가 우선돼요." not in html
    assert "연령대는 별도 질문 없이 자동으로 구분합니다." not in html
    assert 'class="eligibility-profile-fields"' in html
    assert ".eligibility-profile-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))" in styles
    assert ".branch-result{max-width:none;width:100%" in styles
    assert '$("#eligibility-form").addEventListener("change", () => {' in script
    assert script.count('$("#eligibility-guidance").hidden = true;') >= 4


def test_high_risk_prioritizes_medical_guidance_and_hides_internal_versions() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "검사·상담 안내 보기" in script
    assert 'prediction.result_status === "approved"' in script
    assert 'prediction.promotion_status === "approved"' in script
    assert '$("#result-next").hidden = !isApprovedRisk' in script
    assert "options.resultAvailable === true" in script
    assert 'factors?.status === "approved"' in script
    assert "factors?.shap_claimed === true" in script
    assert '$("#risk-confirm-card").hidden = !isApprovedRisk' in script
    assert 'id="result-unavailable"' in html
    assert "모델 검증 중" in script
    assert "medical-guidance-detail" in html + script
    assert 'id="model-version"' not in html
    assert "prediction.model_version" not in script
    assert "prediction.feature_schema_version" not in script
    assert "약 2년 뒤" not in html


def test_age_risk_forecast_is_accessible_and_requires_public_approval() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src/frontend/styles.css").read_text(encoding="utf-8")

    assert 'id="risk-forecast-panel"' in html
    assert 'id="age-risk-chart" role="img"' in html
    assert 'id="forecast-state" role="status" aria-live="polite"' in html
    assert "현재 생활습관 유지" in html
    assert "생활습관 개선" in html
    assert "효과를 보장하거나 치료 결과를 예측하는 값이 아닙니다." in html
    assert "불확실성 범위" in html
    assert 'forecast?.status === "approved"' in script
    assert "forecast?.public_display_approved === true" in script
    assert "approvedDisplayPercent" in script
    assert "임의 수치나 그래프를 만들지 않습니다." in script
    assert "renderAgeRiskForecast(prediction, isApprovedRisk)" in script
    assert "@media(forced-colors:active)" in styles
    assert "repeating-linear-gradient" in styles


def test_together_shares_only_challenge_completion_status() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "건강정보와 예측 결과는 공유하지 않습니다." in html
    assert "챌린지 수행 상태만 공유" in script
    assert "completed_days" in script
    assert "shared-member-progress" in script


def test_service_and_model_age_are_separately_explained() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")

    assert "만 14~18세는 생활습관 챌린지" in html
    assert "만 19~44세는 현재 건강 신호" in html
    assert "만 45세 이상은 미래 발병 위험" in html


def test_health_form_uses_rf25_smoking_status_contract() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'name="smoking-status"' in html
    for value in ("never", "former", "current"):
        assert f'value="{value}"' in html
    assert 'smoking_status: selectedRadioValue("smoking-status")' in script
    assert 'current_smoker: selectedRadioValue("current-smoker")' not in script


def test_health_form_uses_rf25_exercise_detail_contract() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="exercise-days"' in html
    assert 'min="0" max="7"' in html
    assert 'id="exercise-minutes"' in html
    assert 'min="0" max="720"' in html
    assert "exercise_days_per_week:" in script
    assert "exercise_minutes:" in script
    assert 'days.value = "0"' in script
    assert 'minutes.value = "0"' in script
    assert "운동하지 않는 경우에는 두 값이 자동으로 0으로 저장됩니다." not in html
    assert html.index('id="current-drinker-title"') < html.index('id="smoking-status-title"')
    lifestyle = html.split('id="lifestyle-input-panel"', 1)[1].split('id="health-review-panel"', 1)[0]
    assert "필수" not in lifestyle
    assert (
        lifestyle.index('id="regular-exercise-title"')
        < lifestyle.index('for="self-health"')
        < lifestyle.index('for="meal-count"')
    )
    assert "card.hidden = !isRegularExercise" in script
    assert 'id="regular-exercise" name="regular-exercise" type="radio" value="true" required' in lifestyle
    assert 'value="true" checked' not in lifestyle.split('id="regular-exercise-title"', 1)[1].split("</div>", 2)[0]


def test_mvp_exposes_returning_login_and_extended_dashboard_actions() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    for label in (
        "기존 계정으로 로그인",
        "이메일로 초대",
        "초대 코드로 초대",
        "워치 연결하기",
        "근거 자료에서 찾기",
        "검진표 사진 올리기",
        "PDF 받기",
    ):
        assert label in html
    assert "accept-shared" in script
    assert "cheer-shared" in script
    assert "[hidden]{display:none!important}" in (ROOT / "src/frontend/styles.css").read_text(encoding="utf-8")


def test_invite_method_starts_unselected_and_reveals_only_requested_panel() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="relation-type"' not in html
    assert 'id="invite-nickname"' not in html
    assert 'id="invite-tab-email" type="button" aria-expanded="false"' in html
    assert 'id="invite-tab-code" type="button" aria-expanded="false"' in html
    assert 'id="invite-form"' in html and 'data-invite-panel="email" hidden' in html
    assert 'id="invite-panel-code"' in html and 'data-invite-panel="code" hidden' in html
    assert "panel.hidden = !selected" in script
    assert 'button.addEventListener("click", () => setInviteMode(button.dataset.inviteMode))' in script


def test_demo_controls_and_invite_placeholders_are_environment_safe() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'class="status-demo-panel" aria-label="분석 결과 상태 확인용" hidden' in html
    assert "statusPanel.hidden = !isDemoEnvironment()" in script
    assert '<strong id="forest-invite-code">7F K3 Q1</strong>' not in html
    assert '<strong id="forest-invite-code">초대 코드 발급 준비 중</strong>' in html
    assert 'id="copy-invite-code" type="button" disabled' in html
    assert 'codeNode.dataset.copyValue = isDemo ? "DEMO-CODE" : ""' in script
    assert "로컬 화면 확인용 코드입니다. 실제 초대에는 사용할 수 없어요." in script
    assert "실제 초대 코드 API가 연결되면 여기에서 확인할 수 있어요." in html + script


def test_invite_api_response_is_rendered_as_text_not_html() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "function renderInviteEmailResult(result = {})" in script
    assert 'token.textContent = result.token || "초대 요청 접수 완료"' in script
    assert 'notice.textContent = result.notice || "초대 상태는 함께하기 화면에서 확인할 수 있어요."' in script
    assert "box.replaceChildren(content)" in script
    assert "renderInviteEmailResult(result)" in script
    assert "box.innerHTML = `<div><strong>초대 이메일을 보낼 준비가 되었습니다" not in script


def test_frontend_uses_current_backend_signup_profile_and_prediction_contract() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="display-name"' not in html
    assert 'name: $("#display-name").value' not in script
    assert 'id="signup-birth-date" type="date"' in html
    assert 'id="signup-gender" required' in html
    assert "email, password, gender, birth_date: birthDate" in script
    assert 'terms_agreed: $("#personal-consent").checked' not in script
    assert 'api("/users/me", { method: "PATCH"' in script
    assert 'api("/users/me/profile", { method: "PATCH"' not in script
    assert 'birthday: $("#eligibility-birth-date").value' in script
    assert '$("#eligibility-birth-date").value = birthDate' in script
    assert 'state.token = state.token || "local-demo-token"' not in script
    assert 'const isDemoEnvironment = () => ["localhost", "127.0.0.1", "::1"]' in script
    assert "if (!isDemoEnvironment()) return;" in script
    assert "API 연결 전이라 로컬 화면 확인 모드로 계속합니다." not in script
    assert "API 연결 전이라 기존 회원 화면 확인 모드로 로그인했습니다." not in script
    assert 'data-demo-status="timeout"' not in html
    assert 'data-demo-status="model_not_ready"' not in html
    assert 'renderPredictionStatus("failed", {' in script
    assert 'errorCode: isTimeout ? "TIMEOUT"' in script


def test_signup_and_existing_login_use_separate_forms() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="auth-mode-signup"' in html
    assert 'id="auth-mode-login"' in html
    assert 'id="signup-form"' in html
    assert 'id="login-form" class="login-form" hidden' in html
    assert 'id="login-email" type="email"' in html
    assert 'id="login-password" type="password"' in html
    assert "생년월일과 성별은 가입할 때 저장한 정보를 불러옵니다." in html
    assert '$("#login-form").addEventListener("submit"' in script
    assert 'email: $("#login-email").value, password: $("#login-password").value' in script
    assert '$("#login-existing")' not in script


def test_challenge_grid_has_a_custom_challenge_slot() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="custom-challenge-editor"' in html
    assert 'id="custom-challenge-title"' in html
    assert 'id="custom-challenge-goal"' in html
    assert 'id="custom-challenge-record-type"' in html
    assert "나만의 챌린지 추가" in script
    assert "function customChallengeSlot()" in script
    assert "function renderChallengeChoices()" in script
    assert "나만의 챌린지는 저장 API가 연결된 뒤 시작할 수 있어요." in script


def test_notion_challenges_are_grouped_into_selectable_habit_categories() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="challenge-category-panel"' in html
    assert 'id="challenge-detail-list"' in html
    assert 'id="challenge-selection-count"' in html
    for category in ("움직이기", "건강하게 먹기", "기록하기"):
        assert category in script
    for mascot in (
        "hyeoldangi-challenge-walking.png",
        "hyeoldangi-challenge-meal.png",
        "hyeoldangi-daily-record.png",
    ):
        assert mascot in script
    for challenge in (
        "빠르게 걷기",
        "30분마다 일어나기",
        "채소 먼저 먹기",
        "통곡물·잡곡 선택",
        "7~8시간 수면 기록",
        "생활습관 돌아보기",
        "무가당 음료 주 5일",
        "채소 먹기 주 5일",
        "통곡물 선택 주 3회",
        "체중 추이 확인",
    ):
        assert challenge in script
    assert 'api("/challenges")' in script
    assert "state.selectedChallengeIds" in script
    assert "state.challengeRecommendationsPersonalized = result.personalized === true" in script
    assert "state.challengeRecommendationsPersonalized && recommendationIds.has" in script
    assert "챌린지는 최대 3개까지 선택할 수 있어요." in script


def test_frontend_distinguishes_api_errors_without_demo_fallback() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    expected_status_codes = {
        401: "UNAUTHENTICATED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        503: "MODEL_NOT_READY",
        504: "TIMEOUT",
    }
    for status, code in expected_status_codes.items():
        assert f'if (status === {status}) return "{code}";' in script
    assert 'if (status >= 500) return "SERVER_ERROR";' in script
    for code in (*expected_status_codes.values(), "SERVER_ERROR", "NETWORK_ERROR"):
        assert code in script
    assert "네트워크 연결을 확인한 뒤 다시 시도해 주세요." in script
    assert "챌린지 목록을 불러오지 못했습니다." in script
    assert "현재 선택할 수 있는 챌린지가 없습니다." in script
    assert "기본 예시를 표시합니다." not in script


def test_rf25_ml_errors_have_safe_actionable_frontend_guidance() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src/frontend/styles.css").read_text(encoding="utf-8")

    expected_guidance = {
        "ML_INPUT_MISSING": "필수 건강정보를 확인해 주세요",
        "ML_INPUT_OUT_OF_RANGE": "건강정보의 입력값을 확인해 주세요",
        "ML_POPULATION_UNSUPPORTED": "현재 연령은 미래 발병 예측 대상이 아닙니다",
        "ML_POPULATION_INELIGIBLE": "현재는 미래 발병 예측을 진행하지 않습니다",
        "ML_MODEL_UNAVAILABLE": "현재 예측 모델을 준비하고 있습니다",
        "ML_MODEL_CONTRACT_ERROR": "예측 모델 연결을 점검하고 있습니다",
    }
    assert "const predictionFailureGuidance = {" in script
    for error_code, user_title in expected_guidance.items():
        assert error_code in script
        assert user_title in script

    assert "fallbackApiErrorMessage(resolvedCode)" in script
    assert "failureGuidance?.message || error.message" in script
    assert "실패는 높은 위험을 의미하지 않습니다." in script
    assert "임의 점수나 위험 범주를 표시하지 않습니다." in script
    assert "점수·확률·위험 범주를 만들거나 표시하지 않습니다." in script
    for error_code in ("ML_MODEL_UNAVAILABLE", "ML_MODEL_CONTRACT_ERROR"):
        assert f'data-error-code="{error_code}"' in styles


def test_signup_and_login_block_duplicate_requests_while_busy() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "function setFormBusy(form, activeButton, busyLabel)" in script
    assert 'form.setAttribute("aria-busy", "true")' in script
    assert "buttons.forEach((button) => { button.disabled = true; })" in script
    assert '"가입 처리 중…"' in script
    assert '"로그인 중…"' in script
    assert script.count("releaseBusy();") >= 2


def test_remaining_user_actions_block_duplicate_requests_while_busy() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "function setButtonBusy(button, busyLabel)" in script
    assert 'button.setAttribute("aria-busy", "true")' in script
    assert 'button.removeAttribute("aria-busy")' in script
    for busy_label in (
        "이용 가능 확인 중…",
        "챌린지 시작 중…",
        "기록 저장 중…",
        "오늘 기록 저장 중…",
        "초대 이메일 보내는 중…",
        "워치 기록 저장 중…",
        "PDF 만드는 중…",
    ):
        assert busy_label in script
    assert script.count("finally { releaseBusy(); }") >= 8


def test_active_challenge_conflict_resumes_current_cycle_dashboard() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "error.status === 409" in script
    assert 'error.message.includes("진행 중인 4주 챌린지")' in script
    assert 'const currentCycle = await api("/challenge-cycles/current")' in script
    assert "renderCycle(currentCycle)" in script
    assert 'showWorkspace("home", { moveFocus: false })' in script
    assert "이미 진행 중인 4주 챌린지를 불러왔어요" in script


def test_challenge_step_navigation_loads_cards_and_guards_start_button() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "async function goStepFromNav(step)" in script
    assert "if (step === 7)" in script
    assert "await loadChallenges()" in script
    assert "챌린지 목록을 불러오고 있어요." in script
    assert 'const startButton = $("#start-challenge")' in script
    assert "startButton.disabled = true" in script
    assert "if (!result.medical_guidance_required_first) startButton.disabled = false" in script


def test_returning_user_routes_from_persisted_eligibility_state() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'id="returning-route-note"' in html
    assert 'api("/eligibility-checks/latest")' in script
    assert "syncReturningEligibilityState(latestEligibility)" in script
    assert 'beginReturningEligibility("challenges")' in script
    assert 'beginReturningEligibility("health")' in script
    assert "로그인할 때마다 반복하는 절차는 아닙니다" in script
    assert 'id="challenge-follow-up"' in html
    assert 'api("/follow-up-actions")' in script
    assert "state.openFollowUpActionIds.map((actionId)" in script
    assert "api(`/follow-up-actions/${actionId}/acknowledge`" in script
    assert "if (state.currentHealthOnly)" in script
    assert "if (state.cycle?.user_challenges?.length)" in script
    assert "이어서 4주 생활습관 챌린지를 선택해 주세요" in script


def test_report_does_not_present_sample_progress_as_user_data() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    for sample_value in ("8/21~8/27", "5일 연속 잘하고 계세요!", "4주 동안 총 18번", "전체 완료율</small><strong>64%"):
        assert sample_value not in html
    assert 'id="report-week-period">기간 확인 중' in html
    assert 'id="report-week-days"' in html and 'aria-label="요일별 실천 현황" hidden' in html
    assert "4주 전체 기록은 아직 준비 중이에요" in html
    assert "전체 기간 이력 API가 연결되면" in html
    assert "report.challenge_details || []" in script
    assert "주간 기록을 확인할 수 없어요" in script
    assert "건강교육을 불러오지 못했어요" in script
    assert "완료 처리 중…" in script
    assert "정답입니다. 교육 콘텐츠를 완료했습니다." not in script
    assert 'if (!result.is_correct) showMessage("내용을 다시 확인해 주세요.", "error")' in script
    assert "completed: 5, planned: 7" not in script


def test_dashboard_is_split_into_tasks_and_lifestyle_map_is_non_diagnostic() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    for workspace in ("home", "challenge", "report", "together", "tools"):
        assert f'data-workspace="{workspace}"' in html
        assert f'data-workspace-panel="{workspace}"' in html
        assert f'id="workspace-tab-{workspace}"' in html
    assert "오늘 할 일부터 확인하세요" in html
    assert "내 생활습관 지도" in html
    assert "지도 보기" in html
    assert "지도 닫기" in html
    assert "체형이나 건강 위험을 판정하지 않습니다." in html
    assert "3D 생활습관 안내 캐릭터" in html
    assert "lifestyle-avatar-female-60.webp" in html
    assert '"male" : "female"' in script
    assert "ageBand" in script
    assert "Math.floor(age / 10) * 10" in script
    assert "syncLifestyleAvatar" in script
    assert "avatar-width-scale" in script
    assert "avatar-height-scale" in script
    assert "입력값을 반영한 참고 표현" in script
    assert "updateLifestyleMap" in script
    assert "체형 기록" in html + script
    assert 'role="tablist"' in html
    assert html.count('role="tab"') >= 5
    assert html.count('role="tabpanel"') >= 5
    assert 'aria-pressed="true"' in html
    assert 'button.setAttribute("aria-pressed", String(selected))' in script
    assert "selectedPanel.focus({ preventScroll: true })" in script


def test_only_reviewed_diabetes_contract_is_active() -> None:
    assert ACTIVE_MODEL.model_key == "diabetes_incidence"
    assert ACTIVE_MODEL.outcome_definition == "next_observation_new_diabetes_diagnosis"
    assert ACTIVE_MODEL.observation_horizon == "approximately_2_years_next_klosa_wave"
    assert ACTIVE_MODEL.threshold_is_approved is False
