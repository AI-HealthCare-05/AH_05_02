from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, UserUpdateRequest
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> UserInfoResponse:
    return UserInfoResponse.model_validate(user)


@user_router.patch("/me/profile", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> UserInfoResponse:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    return UserInfoResponse.model_validate(updated_user)


@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_me(user: Annotated[User, Depends(get_request_user)]) -> None:
    user.is_active = False
    await user.save(update_fields=["is_active", "updated_at"])
