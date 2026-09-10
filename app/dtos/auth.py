from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator

from app.core.validators import validate_password


class SignUpRequest(BaseModel):
    email: Annotated[
        EmailStr,
        Field(None, max_length=40),
    ]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    terms_agreed: bool = Field(..., description="서비스 이용약관 동의 여부")

    @field_validator("terms_agreed")
    @classmethod
    def require_terms_agreement(cls, value: bool) -> bool:
        if not value:
            raise ValueError("서비스 이용약관에 동의해야 합니다.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...


class PasswordChangeRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=8)]
    new_password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    new_password_confirmation: str

    @field_validator("new_password_confirmation")
    @classmethod
    def confirmation_is_present(cls, value: str) -> str:
        if not value:
            raise ValueError("새 비밀번호 확인을 입력해 주세요.")
        return value


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    new_password_confirmation: str
