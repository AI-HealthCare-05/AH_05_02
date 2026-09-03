from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.facilities.providers import MedicalFacilitySearchError
from app.models.users import User
from app.services.facilities import (
    MEDICAL_FACILITY_DEFAULT_RADIUS_METERS,
    MEDICAL_FACILITY_MAX_RADIUS_METERS,
    MEDICAL_FACILITY_MIN_RADIUS_METERS,
    EmergencyFacilityService,
    MedicalFacilityService,
)

facility_router = APIRouter(tags=["Medical facilities"])


@facility_router.get("/emergency-facilities/nearby")
async def nearby_emergency_facilities(
    user: Annotated[User, Depends(get_request_user)],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[
        int,
        Query(ge=MEDICAL_FACILITY_MIN_RADIUS_METERS, le=MEDICAL_FACILITY_MAX_RADIUS_METERS),
    ] = 10000,
) -> dict[str, object]:
    del user
    try:
        result = await EmergencyFacilityService().nearby(latitude=lat, longitude=lon, radius_meters=radius)
    except (MedicalFacilitySearchError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return envelope(result)


@facility_router.get("/medical-facilities/nearby")
async def nearby_medical_facilities(
    user: Annotated[User, Depends(get_request_user)],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[
        int,
        Query(ge=MEDICAL_FACILITY_MIN_RADIUS_METERS, le=MEDICAL_FACILITY_MAX_RADIUS_METERS),
    ] = MEDICAL_FACILITY_DEFAULT_RADIUS_METERS,
) -> dict[str, object]:
    del user  # 인증만 필요하고 사용자별로 결과를 분기하지는 않습니다.
    try:
        result = await MedicalFacilityService().nearby(latitude=lat, longitude=lon, radius_meters=radius)
    except MedicalFacilitySearchError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return envelope(result)
