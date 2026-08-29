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
