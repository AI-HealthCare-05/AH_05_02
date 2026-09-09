"""Read-only ASGI smoke checks; no account, health record, or DB startup is used."""

import unittest

import httpx

from app.main import app


class SuinFrontendRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_and_namespaced_assets(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/service?returnTo=forest-challenges")
            self.assertEqual(response.status_code, 200)
            self.assertIn('id="login-form"', response.text)
            self.assertIn("no-store", response.headers["cache-control"])
            for resource in ("app.js", "styles.css", "assets/hyeoldangi-consent.png"):
                asset = await client.get(f"/static/suin/{resource}")
                self.assertEqual(asset.status_code, 200, resource)

    async def test_unsigned_user_cannot_refresh_or_access_challenge(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            for resource in ("/api/v1/auth/token/refresh", "/api/v1/challenge-v2/today"):
                response = await client.get(resource)
                self.assertEqual(response.status_code, 401, resource)


if __name__ == "__main__":
    unittest.main()
