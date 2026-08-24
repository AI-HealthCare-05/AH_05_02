from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.validators import optional_after_validator, validate_birthday, validate_password, validate_phone_number
from app.models.users import Gender


class SignUpRequest(BaseModel):
    email: Annotated[
        EmailStr,
        Field(None, max_length=40),
    ]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    # 이름·전화번호는 서비스 제공과 모델 추론에 필요하지 않다. 기존 API
    # 호출과의 호환성만 유지하고 신규 클라이언트에는 수집을 요구하지 않는다.
    name: Annotated[str | None, Field(default=None, min_length=2, max_length=20)]
    gender: Gender
    birth_date: Annotated[date, AfterValidator(validate_birthday)]
    phone_number: Annotated[str | None, optional_after_validator(validate_phone_number)] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...
