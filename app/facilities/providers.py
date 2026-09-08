from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Protocol
from urllib.parse import quote, unquote
from xml.etree import ElementTree

import httpx

from app.core import config


class MedicalFacilitySearchError(RuntimeError):
    """의료기관 검색 provider 호출에 실패했을 때 사용하는 예외입니다."""


@dataclass(frozen=True)
class FacilityResult:
    name: str
    department_hint: str | None
    address: str | None
    road_address: str | None
    phone: str | None
    distance_meters: int | None
    map_url: str | None
    latitude: float
    longitude: float


class MedicalFacilitySearchProvider(Protocol):
    provider_kind: str
    data_source: str

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
    ) -> list[FacilityResult]: ...


class DevelopmentMedicalFacilitySearchProvider:
    """실제 카카오 API를 호출하지 않는 개발용 어댑터입니다.

    좌표 근처에 있는 것처럼 보이는 고정된 목업 의료기관 3곳을 결정적으로 반환해서,
    provider 인터페이스와 화면 연동을 실제 카카오 API 키 없이도 검증할 수 있게 합니다.
    운영 환경에서는 MEDICAL_FACILITY_SEARCH_PROVIDER=kakao로 전환해서 사용하지 않습니다.
    """

    provider_kind = "development"
    data_source = "development_mock"

    _MOCK_FACILITIES: tuple[tuple[str, str, int, str], ...] = (
        ("튼튼내과의원", "내과", 350, "02-000-0001"),
        ("행복가정의학과의원", "가정의학과", 620, "02-000-0002"),
        ("서울종합내과", "내과", 890, "02-000-0003"),
    )

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
    ) -> list[FacilityResult]:
        del radius_meters  # 개발용 어댑터는 반경과 무관하게 항상 같은 3곳을 반환합니다.
        results: list[FacilityResult] = []
        for index, (name, department_hint, distance_meters, phone) in enumerate(self._MOCK_FACILITIES, start=1):
            # 좌표는 지도에 표시할 수 있도록 입력 좌표에서 아주 조금씩만 벗어난 값을 사용합니다.
            offset = 0.001 * index
            results.append(
                FacilityResult(
                    name=name,
                    department_hint=department_hint,
                    address=f"(개발용 목업 주소) 서울시 어딘가 {index}길 {index}",
                    road_address=None,
                    phone=phone,
                    distance_meters=distance_meters,
                    map_url=f"https://place.map.kakao.com/development-mock-{index}",
                    latitude=latitude + offset,
                    longitude=longitude + offset,
                )
            )
        return results


class KakaoLocalMedicalFacilitySearchProvider:
    """카카오 로컬 API 키워드 검색으로 근처 병원을 조회합니다.

    카테고리 검색(HP8, 반경 내 병원 전체 반환)이 아니라 키워드 검색으로 좁혀서
    반환하기로 결정했습니다(2026-09-02 팀 회의). 진료과와 무관한 병원까지 다 나오는
    장소 이름에 "내과"가 없어도 당뇨 진료 관련 의료기관을 찾을 수 있도록
    카카오 장소 검색에 "당뇨" 키워드만 전달합니다.
    category_group_code=HP8을 함께 지정해서 병원이 아닌 곳(약국 등)이 텍스트 매칭으로
    잘못 섞여 들어오는 것은 막습니다.
    """

    provider_kind = "kakao_local_api"
    data_source = "kakao_local_api_keyword_diabetes"

    _SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def __init__(self) -> None:
        if not config.KAKAO_REST_API_KEY:
            raise MedicalFacilitySearchError(
                "KAKAO_REST_API_KEY가 설정되어 있지 않습니다. .env에 키를 추가한 뒤 다시 시도해주세요."
            )
        self._api_key = config.KAKAO_REST_API_KEY
        self._keywords = [word.strip() for word in config.MEDICAL_FACILITY_SEARCH_KEYWORDS.split(",") if word.strip()]
        self._category_group_code = config.MEDICAL_FACILITY_SEARCH_CATEGORY_GROUP_CODE
        # "내과" 키워드가 "구강내과"(치과)까지 텍스트로 매칭시키는 것을 막기 위한 후처리 제외 목록입니다.
        self._excluded_category_keywords = [
            word.strip()
            for word in config.MEDICAL_FACILITY_SEARCH_EXCLUDED_CATEGORY_KEYWORDS.split(",")
            if word.strip()
        ]

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
    ) -> list[FacilityResult]:
        documents_by_id: dict[str, dict[str, object]] = {}
        try:
            async with httpx.AsyncClient(timeout=config.MEDICAL_FACILITY_SEARCH_TIMEOUT_SECONDS) as client:
                for keyword in self._keywords:
                    response = await client.get(
                        self._SEARCH_URL,
                        headers={"Authorization": f"KakaoAK {self._api_key}"},
                        params={
                            "query": keyword,
                            "x": str(longitude),
                            "y": str(latitude),
                            "radius": str(radius_meters),
                            "category_group_code": self._category_group_code,
                            "sort": "distance",
                        },
                    )
                    response.raise_for_status()
                    for document in response.json().get("documents", []):
                        place_id = document.get("id")
                        category_name = str(document.get("category_name") or "")
                        if any(excluded in category_name for excluded in self._excluded_category_keywords):
                            continue
                        if place_id and place_id not in documents_by_id:
                            documents_by_id[place_id] = document
        except httpx.TimeoutException as exc:
            raise MedicalFacilitySearchError(
                "의료기관 검색 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MedicalFacilitySearchError(
                f"의료기관 검색 provider 호출에 실패했습니다: {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise MedicalFacilitySearchError("의료기관 검색 provider에 연결할 수 없습니다.") from exc

        results = [self._to_facility_result(document) for document in documents_by_id.values()]
        results.sort(key=lambda item: (item.distance_meters is None, item.distance_meters))
        return results[: config.MEDICAL_FACILITY_MAX_RESULTS]

    @staticmethod
    def _to_facility_result(document: dict[str, object]) -> FacilityResult:
        category_name = str(document.get("category_name") or "")
        # 카카오 카테고리 문자열의 마지막 조각을 진료과 추정값으로 사용합니다.
        # 예: "의료,건강 > 병원 > 내과" -> "내과". 구조화된 진료과 정보가 아니므로
        # 확정된 값이 아니라 추정값이며, 화면에는 노출하지 않기로 결정했습니다.
        segments = [segment.strip() for segment in category_name.split(">") if segment.strip()]
        department_hint = segments[-1] if len(segments) > 1 else None
        distance_raw = document.get("distance")
        distance_meters = int(distance_raw) if isinstance(distance_raw, str) and distance_raw.isdigit() else None
        return FacilityResult(
            name=str(document.get("place_name") or "이름 미상"),
            department_hint=department_hint,
            address=document.get("address_name") or None,
            road_address=document.get("road_address_name") or None,
            phone=document.get("phone") or None,
            distance_meters=distance_meters,
            map_url=document.get("place_url") or None,
            latitude=float(document.get("y", 0.0)),
            longitude=float(document.get("x", 0.0)),
        )


class NemcEmergencyFacilitySearchProvider:
    """국립중앙의료원 공식 위치 기반 API로 가까운 응급의료기관을 조회합니다."""

    provider_kind = "nemc_emergency_api"
    data_source = "national_emergency_medical_center"

    def __init__(self) -> None:
        if not config.NEMC_SERVICE_KEY:
            raise MedicalFacilitySearchError("NEMC_SERVICE_KEY가 설정되어 있지 않습니다.")

    async def search(self, *, latitude: float, longitude: float, radius_meters: int) -> list[FacilityResult]:
        try:
            async with httpx.AsyncClient(timeout=config.NEMC_EMERGENCY_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    config.NEMC_EMERGENCY_API_URL,
                    params={
                        # 공공데이터포털이 제공하는 Encoding/Decoding 키를 모두 허용합니다.
                        # httpx가 params를 인코딩하므로 저장된 값은 먼저 한 번 디코딩합니다.
                        "serviceKey": unquote(config.NEMC_SERVICE_KEY),
                        "WGS84_LON": str(longitude),
                        "WGS84_LAT": str(latitude),
                        "pageNo": "1",
                        "numOfRows": str(config.EMERGENCY_FACILITY_MAX_RESULTS),
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MedicalFacilitySearchError("응급의료기관 조회가 시간 초과되었습니다.") from exc
        except httpx.HTTPError as exc:
            raise MedicalFacilitySearchError("공식 응급의료 API에 연결할 수 없습니다.") from exc

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise MedicalFacilitySearchError("응급의료 API 응답을 해석하지 못했습니다.") from exc
        gateway_error = root.findtext(".//returnAuthMsg") or root.findtext(".//errMsg")
        if gateway_error:
            raise MedicalFacilitySearchError(f"응급의료 API 인증 오류: {gateway_error}")
        result_code = root.findtext(".//resultCode")
        if result_code not in (None, "00"):
            message = root.findtext(".//resultMsg") or "알 수 없는 오류"
            raise MedicalFacilitySearchError(f"응급의료 API 오류: {message}")

        facilities: list[FacilityResult] = []
        for item in root.findall(".//item"):
            item_latitude = self._float(item.findtext("latitude"))
            item_longitude = self._float(item.findtext("longitude"))
            if item_latitude is None or item_longitude is None:
                continue
            distance = self._distance_meters(latitude, longitude, item_latitude, item_longitude)
            if distance > radius_meters:
                continue
            name = item.findtext("dutyName") or "이름 미상"
            facilities.append(
                FacilityResult(
                    name=name,
                    department_hint=item.findtext("dutyEmclsName") or "응급의료기관",
                    address=item.findtext("dutyAddr"),
                    road_address=None,
                    phone=item.findtext("dutyTel3") or item.findtext("dutyTel1"),
                    distance_meters=distance,
                    map_url=f"https://map.kakao.com/link/to/{quote(name)},{item_latitude},{item_longitude}",
                    latitude=item_latitude,
                    longitude=item_longitude,
                )
            )
        facilities.sort(key=lambda facility: facility.distance_meters or 0)
        return facilities[: config.EMERGENCY_FACILITY_MAX_RESULTS]

    @staticmethod
    def _float(value: str | None) -> float | None:
        try:
            return float(value) if value else None
        except ValueError:
            return None

    @staticmethod
    def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        earth_radius = 6_371_000
        lat_delta = radians(lat2 - lat1)
        lon_delta = radians(lon2 - lon1)
        a = sin(lat_delta / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(lon_delta / 2) ** 2
        return round(2 * earth_radius * asin(sqrt(a)))


def get_medical_facility_search_provider() -> MedicalFacilitySearchProvider:
    if config.MEDICAL_FACILITY_SEARCH_PROVIDER == "development":
        return DevelopmentMedicalFacilitySearchProvider()
    if config.MEDICAL_FACILITY_SEARCH_PROVIDER == "kakao":
        return KakaoLocalMedicalFacilitySearchProvider()
    raise MedicalFacilitySearchError(
        f"지원하지 않는 MEDICAL_FACILITY_SEARCH_PROVIDER입니다: {config.MEDICAL_FACILITY_SEARCH_PROVIDER}"
    )
