from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"


def _frontend_sources() -> tuple[str, str]:
    return (
        (FRONTEND / "index.html").read_text(encoding="utf-8"),
        (FRONTEND / "app.js").read_text(encoding="utf-8"),
    )


def test_facility_buttons_call_real_nearby_endpoints() -> None:
    html, script = _frontend_sources()

    assert 'id="find-nearby-medical-facilities"' in html
    assert 'id="find-nearby-emergency"' in html
    assert "api(`/medical-facilities/nearby?${params.toString()}`)" in script
    assert "api(`/emergency-facilities/nearby?${params.toString()}`)" in script


def test_location_failure_offers_address_search_without_fixed_fallback() -> None:
    html, script = _frontend_sources()

    assert 'id="facility-address-form"' in html
    assert 'id="emergency-address-form"' in html
    assert "coordinatesForAddress" in script
    assert "geocoder.addressSearch" in script
    assert "DEFAULT_FACILITY_LOCATION" not in script
    assert "기본 위치" not in script
    assert '$("#facility-address-form").hidden = false' in script
    assert '$("#emergency-address-form").hidden = false' in script


def test_location_statuses_distinguish_denied_timeout_and_unavailable() -> None:
    _, script = _frontend_sources()

    assert 'if (error?.code === 1) return "permission"' in script
    assert 'if (error?.code === 3) return "timeout"' in script
    assert 'return "unavailable"' in script
    assert "setMedicalFacilityStatus(geolocationFailureState(error), title, message)" in script
    assert "setEmergencyFacilityStatus(geolocationFailureState(error), title" in script


def test_new_or_failed_search_clears_previous_results_and_map() -> None:
    html, script = _frontend_sources()

    assert 'id="medical-facility-map"' in html
    assert 'id="emergency-facility-map"' in html
    assert "function resetFacilitySearchUi(target)" in script
    assert 'results.innerHTML = ""' in script
    assert "clearFacilityMapMarkers(target)" in script
    assert "map.hidden = true" in script
    assert script.count('resetFacilitySearchUi("medical")') >= 4
    assert script.count('resetFacilitySearchUi("emergency")') >= 6
    assert script.count('referenceLabel: "검색 기준 위치"') == 2


def test_existing_frontend_contracts_remain_visible() -> None:
    html, script = _frontend_sources()

    assert 'href="tel:119"' in html
    assert 'id="risk-traffic-light"' in html
    assert 'id="risk-hyeoldangi"' in html
    assert "hyeoldangi-face-high.png" in html
    assert 'id="rag-challenge-generator"' in html
    assert 'email, password, terms_agreed: $("#personal-consent").checked' in script
    assert 'id="medical-guidance-detail"' in html
    assert 'tabindex="-1"' in html


def test_rag_challenge_states_include_grounding_failure() -> None:
    _, script = _frontend_sources()

    assert 'loading: ["챌린지 후보를 만들고 있어요"' in script
    assert 'done: ["맞춤 챌린지 후보 3개가 준비됐어요"' in script
    assert 'insufficient: ["추천 근거가 충분하지 않아요"' in script
    assert 'failed: ["초안을 만들지 못했어요"' in script
    assert "function hasGroundedRagChallengeCandidates(candidates)" in script
    assert 'hasGroundedRagChallengeCandidates(state.ragChallengeCandidates) ? "done" : "insufficient"' in script
