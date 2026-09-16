from __future__ import annotations

from app.core import config
from app.facilities.providers import (
    FacilityResult,
    NemcEmergencyFacilitySearchProvider,
    get_medical_facility_search_provider,
)

_DISCLAIMER = (
    "검색 결과는 위치 기반 근처 의료기관 안내이며, 특정 의료기관을 추천하거나 진단·처방을 대신하지 않습니다. "
    "진료과목, 운영시간 및 검사 가능 여부는 방문 전에 의료기관에 직접 확인해 주세요."
)


def _facility_to_dict(facility: FacilityResult) -> dict[str, object]:
    return {
        "name": facility.name,
        "department_hint": facility.department_hint,
        "address": facility.address,
        "road_address": facility.road_address,
        "phone": facility.phone,
        "distance_meters": facility.distance_meters,
        "map_url": facility.map_url,
        "latitude": facility.latitude,
        "longitude": facility.longitude,
    }


class MedicalFacilityService:
    async def nearby(self, *, latitude: float, longitude: float, radius_meters: int) -> dict[str, object]:
        provider = get_medical_facility_search_provider()
        facilities = await provider.search(latitude=latitude, longitude=longitude, radius_meters=radius_meters)
        return {
            "provider_kind": provider.provider_kind,
            "data_source": provider.data_source,
            "retrieved_radius_meters": radius_meters,
            "disclaimer": _DISCLAIMER,
            "facilities": [_facility_to_dict(facility) for facility in facilities],
        }


class EmergencyFacilityService:
    async def nearby(self, *, latitude: float, longitude: float, radius_meters: int) -> dict[str, object]:
        if config.EMERGENCY_FACILITY_SEARCH_PROVIDER != "nemc":
            raise ValueError("지원하지 않는 응급의료기관 검색 provider입니다.")
        provider = NemcEmergencyFacilitySearchProvider()
        facilities = await provider.search(latitude=latitude, longitude=longitude, radius_meters=radius_meters)
        return {
            "provider_kind": provider.provider_kind,
            "data_source": provider.data_source,
            "retrieved_radius_meters": radius_meters,
            "disclaimer": "위급한 경우 검색 결과를 기다리지 말고 119에 연락하세요. 기관 정보는 변동될 수 있습니다.",
            "facilities": [_facility_to_dict(facility) for facility in facilities],
        }


MEDICAL_FACILITY_MIN_RADIUS_METERS = 100
MEDICAL_FACILITY_MAX_RADIUS_METERS = 20000
MEDICAL_FACILITY_DEFAULT_RADIUS_METERS = config.MEDICAL_FACILITY_DEFAULT_RADIUS_METERS
