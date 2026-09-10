from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from app.models.users import AuthThrottle

pytestmark = pytest.mark.asyncio


async def _signup(client: AsyncClient, email: str = "auth-security@example.com", password: str = "health1!"):
    return await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "terms_agreed": True},
    )


@pytest_asyncio.fixture
async def client():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value
    await Tortoise.close_connections()


async def test_password_policy_allows_single_case_english_with_number_and_symbol(client: AsyncClient):
    assert (await _signup(client)).status_code == 201
    rejected = await _signup(client, "missing-symbol@example.com", "health12")
    assert rejected.status_code == 422


async def test_five_failures_lock_account_and_return_retry_after(client: AsyncClient):
    await _signup(client)
    payload = {"email": "auth-security@example.com", "password": "wrongpass1!"}
    for _ in range(5):
        assert (await client.post("/api/v1/auth/login", json=payload)).status_code == 400
    locked = await client.post("/api/v1/auth/login", json=payload)
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    assert locked.json()["detail"]["retry_after_seconds"] > 0


async def test_success_resets_login_failures(client: AsyncClient):
    await _signup(client)
    wrong = {"email": "auth-security@example.com", "password": "wrongpass1!"}
    for _ in range(2):
        await client.post("/api/v1/auth/login", json=wrong)
    success = await client.post(
        "/api/v1/auth/login", json={"email": "auth-security@example.com", "password": "health1!"}
    )
    assert success.status_code == 200
    assert await AuthThrottle.filter(scope="login_account").count() == 0


async def test_unknown_email_uses_same_public_error(client: AsyncClient):
    known = await client.post(
        "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrongpass1!"}
    )
    assert known.status_code == 400
    assert known.json()["detail"] == "이메일 또는 비밀번호가 올바르지 않습니다."


async def test_password_change_invalidates_existing_tokens(client: AsyncClient):
    await _signup(client)
    login = await client.post(
        "/api/v1/auth/login", json={"email": "auth-security@example.com", "password": "health1!"}
    )
    token = login.json()["access_token"]
    changed = await client.patch(
        "/api/v1/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "health1!",
            "new_password": "newhealth2!",
            "new_password_confirmation": "newhealth2!",
        },
    )
    assert changed.status_code == 204
    assert (await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "auth-security@example.com", "password": "newhealth2!"},
        )
    ).status_code == 200


async def test_password_reset_is_neutral_single_use_and_invalidates_session(client: AsyncClient):
    await _signup(client)
    login = await client.post(
        "/api/v1/auth/login", json={"email": "auth-security@example.com", "password": "health1!"}
    )
    old_token = login.json()["access_token"]
    requested = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "auth-security@example.com"}
    )
    missing = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "not-registered@example.com"}
    )
    assert requested.status_code == missing.status_code == 202
    assert requested.json()["message"] == missing.json()["message"]
    token = requested.json()["development_reset_token"]
    payload = {"token": token, "new_password": "resetpass3!", "new_password_confirmation": "resetpass3!"}
    assert (await client.post("/api/v1/auth/password-reset/confirm", json=payload)).status_code == 204
    assert (await client.post("/api/v1/auth/password-reset/confirm", json=payload)).status_code == 400
    assert (await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {old_token}"})).status_code == 401


async def test_second_lock_level_is_thirty_minutes(client: AsyncClient):
    await _signup(client)
    payload = {"email": "auth-security@example.com", "password": "wrongpass1!"}
    for _ in range(5):
        await client.post("/api/v1/auth/login", json=payload)
    state = await AuthThrottle.get(scope="login_account")
    state.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    await state.save(update_fields=["locked_until"])
    ip_state = await AuthThrottle.get(scope="login_ip")
    ip_state.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    await ip_state.save(update_fields=["locked_until"])
    for _ in range(5):
        await client.post("/api/v1/auth/login", json=payload)
    state = await AuthThrottle.get(scope="login_account")
    assert state.lock_level == 2
    assert (state.locked_until - datetime.now(UTC)).total_seconds() > 29 * 60
