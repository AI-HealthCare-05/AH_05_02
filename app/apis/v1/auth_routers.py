import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse as Response

from app.apis.responses import envelope
from app.core import config
from app.core.config import Env
from app.dependencies.security import get_request_user
from app.dtos.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignUpRequest,
    TokenRefreshResponse,
)
from app.models.users import User
from app.services.auth import AuthService
from app.services.jwt import JwtService
from app.services.password_reset_delivery import PasswordResetDelivery

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    user = await auth_service.signup(request)
    return Response(
        content=jsonable_encoder(envelope({"user_id": user.id, "email": user.email, "created_at": user.created_at})),
        status_code=status.HTTP_201_CREATED,
    )


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    client_ip = http_request.client.host if http_request.client else "unknown"
    user = await auth_service.authenticate(request, client_ip)
    tokens = await auth_service.login(user)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(), status_code=status.HTTP_200_OK
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["refresh_token"].payload["exp"],
    )
    return resp


@auth_router.get(
    "/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK, include_in_schema=False
)
@auth_router.post("/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
@auth_router.get("/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
    verified = jwt_service.verify_jwt(refresh_token, "refresh")
    user = await User.get_or_none(id=verified.payload.get("user_id"))
    if not user or verified.payload.get("auth_version", 0) != user.auth_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is no longer valid.")
    access_token = verified.access_token
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(), status_code=status.HTTP_200_OK
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: Annotated[User, Depends(get_request_user)]) -> Response:
    response = Response(content=None, status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key="refresh_token", domain=config.COOKIE_DOMAIN or None)
    return response


@auth_router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    user: Annotated[User, Depends(get_request_user)],
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.change_password(
        user, request.current_password, request.new_password, request.new_password_confirmation
    )
    response = Response(content=None, status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key="refresh_token", domain=config.COOKIE_DOMAIN or None)
    return response


@auth_router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    request: PasswordResetRequest,
    http_request: Request,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    client_ip = http_request.client.host if http_request.client else "unknown"
    token = await auth_service.request_password_reset(str(request.email), client_ip)
    payload: dict[str, str] = {"message": auth_service.RESET_MESSAGE}
    if token:
        if config.ENV == Env.PROD:
            try:
                await PasswordResetDelivery().send(str(request.email), token)
            except Exception:
                logger.exception("Password reset email delivery failed")
        else:
            payload["development_reset_token"] = token
    return Response(content=payload, status_code=status.HTTP_202_ACCEPTED)


@auth_router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.reset_password(
        request.token, request.new_password, request.new_password_confirmation
    )
    response = Response(content=None, status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key="refresh_token", domain=config.COOKIE_DOMAIN or None)
    return response
