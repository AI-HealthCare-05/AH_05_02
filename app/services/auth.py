import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.transactions import in_transaction

from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.utils.security import hash_password, verify_password
from app.dtos.auth import LoginRequest, SignUpRequest
from app.models.users import AuthThrottle, PasswordResetToken, User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

DUMMY_PASSWORD_HASH = hash_password("timing-only-password1!")


class AuthService:
    INVALID_LOGIN_MESSAGE = "이메일 또는 비밀번호가 올바르지 않습니다."
    RESET_MESSAGE = "가입된 이메일이라면 비밀번호 재설정 안내를 보냈습니다."

    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        # 이메일 중복 체크
        await self.check_email_exists(data.email)

        # 유저 생성
        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                hashed_password=hash_password(data.password),  # 해시화된 비밀번호를 사용
                name=None,
                phone_number=None,
                gender=None,
                birthday=None,
                # SignUpRequest.terms_agreed는 field_validator에서 True가 아니면 이미 422로
                # 막히므로 여기 도달했다면 항상 True다. 동의 시각도 함께 남겨 나중에
                # 동의 이력을 증빙할 수 있게 한다.
                terms_agreed=data.terms_agreed,
                terms_agreed_at=datetime.now(UTC),
            )

            return user

    @staticmethod
    def _key_hash(value: str) -> str:
        return hashlib.sha256(value.strip().casefold().encode()).hexdigest()

    async def _throttle(self, scope: str, value: str) -> AuthThrottle:
        item, _ = await AuthThrottle.get_or_create(scope=scope, key_hash=self._key_hash(value))
        now = datetime.now(UTC)
        if item.locked_until and item.locked_until > now:
            retry_after = max(1, int((item.locked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "로그인을 여러 번 시도했습니다. 잠시 후 다시 시도해 주세요.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        if item.locked_until and item.locked_until <= now:
            item.failure_count = 0
            item.locked_until = None
            await item.save(update_fields=["failure_count", "locked_until", "updated_at"])
        return item

    async def _record_failure(
        self, item: AuthThrottle, *, threshold: int = 5, fixed_lock_minutes: int | None = None
    ) -> None:
        item.failure_count += 1
        if item.failure_count >= threshold:
            minutes = fixed_lock_minutes if fixed_lock_minutes is not None else (5 if item.lock_level == 0 else 30)
            item.lock_level += 1
            item.failure_count = 0
            item.locked_until = datetime.now(UTC) + timedelta(minutes=minutes)
        await item.save(update_fields=["failure_count", "lock_level", "locked_until", "updated_at"])

    async def authenticate(self, data: LoginRequest, client_ip: str) -> User:
        # 이메일로 사용자 조회
        email = str(data.email).strip().casefold()
        account_state = await self._throttle("login_account", email)
        ip_state = await self._throttle("login_ip", client_ip)
        user = await self.user_repo.get_user_by_email(email)
        password_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
        valid_password = verify_password(data.password, password_hash)
        if not user or not valid_password:
            await self._record_failure(account_state)
            await self._record_failure(ip_state, threshold=30, fixed_lock_minutes=15)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=self.INVALID_LOGIN_MESSAGE)

        # 활성 사용자 체크
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        await AuthThrottle.filter(id__in=[account_state.id, ip_state.id]).delete()

        return user

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        await self.user_repo.update_last_login(user.id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")

    async def change_password(self, user: User, current_password: str, new_password: str, confirmation: str) -> None:
        if new_password != confirmation:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="새 비밀번호가 일치하지 않습니다.")
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다.")
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="현재 비밀번호와 다른 비밀번호를 입력해 주세요.")
        user.hashed_password = hash_password(new_password)
        user.auth_version += 1
        await user.save(update_fields=["hashed_password", "auth_version", "updated_at"])

    async def request_password_reset(self, email: str, client_ip: str) -> str | None:
        email_value = email.strip().casefold()
        email_state = await self._throttle("reset_email", email_value)
        ip_state = await self._throttle("reset_ip", client_ip)
        await self._record_failure(email_state, fixed_lock_minutes=15)
        await self._record_failure(ip_state, threshold=20, fixed_lock_minutes=15)
        user = await self.user_repo.get_user_by_email(email_value)
        verify_password("timing-only-password1!", DUMMY_PASSWORD_HASH)
        if not user:
            return None
        await PasswordResetToken.filter(user_id=user.id, used_at=None).update(used_at=datetime.now(UTC))
        raw_token = secrets.token_urlsafe(32)
        await PasswordResetToken.create(
            user_id=user.id,
            token_hash=self._key_hash(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        return raw_token

    async def reset_password(self, raw_token: str, new_password: str, confirmation: str) -> None:
        if new_password != confirmation:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="새 비밀번호가 일치하지 않습니다.")
        item = await PasswordResetToken.get_or_none(token_hash=self._key_hash(raw_token)).select_related("user")
        now = datetime.now(UTC)
        if not item or item.used_at or item.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="재설정 링크가 만료되었거나 이미 사용되었습니다.")
        if verify_password(new_password, item.user.hashed_password):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="현재 비밀번호와 다른 비밀번호를 입력해 주세요.")
        item.user.hashed_password = hash_password(new_password)
        item.user.auth_version += 1
        item.used_at = now
        async with in_transaction():
            await item.user.save(update_fields=["hashed_password", "auth_version", "updated_at"])
            await item.save(update_fields=["used_at"])
