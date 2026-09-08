from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User


class TestSignupAPI(TestCase):
    async def test_signup_success(self):
        signup_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "terms_agreed": True,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["email"] == "test@example.com"
        assert "meta" in response.json()

    async def test_signup_invalid_email(self):
        signup_data = {
            "email": "invalid-email",
            "password": "password123!",
            "terms_agreed": True,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_signup_requires_terms_agreement(self):
        signup_data = {
            "email": "no-terms@example.com",
            "password": "Password123!",
            "terms_agreed": False,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_signup_persists_terms_agreed(self):
        """terms_agreed는 검증만 하고 저장은 안 되던 버그(9/7) 회귀 방지용."""
        signup_data = {
            "email": "terms-persisted@example.com",
            "password": "Password123!",
            "terms_agreed": True,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_201_CREATED

        user_id = response.json()["data"]["user_id"]
        user = await User.get(id=user_id)
        assert user.terms_agreed is True
        assert user.terms_agreed_at is not None
