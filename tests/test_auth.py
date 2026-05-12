"""Integration tests for /api/v1/auth endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
FORGOT_URL = "/api/v1/auth/forgot-password"
RESET_URL = "/api/v1/auth/reset-password"
VERIFY_URL = "/api/v1/auth/verify-email"


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewPass123!",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": test_user.email,
                "username": "otherusername",
                "password": "NewPass123!",
            },
        )
        assert resp.status_code == 409

    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "other@example.com",
                "username": test_user.username,
                "password": "NewPass123!",
            },
        )
        assert resp.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "password",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "NewPass123!",
            },
        )
        assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        resp = await client.post(
            LOGIN_URL,
            json={"email": test_user.email, "password": "TestPass123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        resp = await client.post(
            LOGIN_URL,
            json={"email": test_user.email, "password": "WrongPass123!"},
        )
        assert resp.status_code == 400

    async def test_login_nonexistent_email(self, client: AsyncClient):
        resp = await client.post(
            LOGIN_URL,
            json={"email": "ghost@example.com", "password": "TestPass123!"},
        )
        assert resp.status_code == 400

    async def test_login_returns_same_message_for_wrong_creds(
        self, client: AsyncClient, test_user
    ):
        """Verify we don't leak whether the email exists."""
        r1 = await client.post(
            LOGIN_URL,
            json={"email": test_user.email, "password": "Wrong123!"},
        )
        r2 = await client.post(
            LOGIN_URL,
            json={"email": "ghost@example.com", "password": "Wrong123!"},
        )
        assert r1.json()["message"] == r2.json()["message"]


# ── Token refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient, test_user):
        login = await client.post(
            LOGIN_URL,
            json={"email": test_user.email, "password": "TestPass123!"},
        )
        refresh_token = login.json()["refresh_token"]

        resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token must differ from the old one (rotation)
        assert data["refresh_token"] != refresh_token

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            REFRESH_URL, json={"refresh_token": "not-a-real-token"}
        )
        assert resp.status_code == 401

    async def test_refresh_token_reuse_rejected(self, client: AsyncClient, test_user):
        login = await client.post(
            LOGIN_URL,
            json={"email": test_user.email, "password": "TestPass123!"},
        )
        old_token = login.json()["refresh_token"]

        # Use the token once
        await client.post(REFRESH_URL, json={"refresh_token": old_token})

        # Reuse should be rejected
        resp = await client.post(REFRESH_URL, json={"refresh_token": old_token})
        assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    async def test_logout_success(self, client: AsyncClient, test_user):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.post(LOGOUT_URL, json={}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_logout_without_token_returns_401(self, client: AsyncClient):
        resp = await client.post(LOGOUT_URL, json={})
        assert resp.status_code == 401


# ── Forgot password ───────────────────────────────────────────────────────────

class TestForgotPassword:
    async def test_forgot_password_existing_email(
        self, client: AsyncClient, test_user
    ):
        resp = await client.post(FORGOT_URL, json={"email": test_user.email})
        assert resp.status_code == 200

    async def test_forgot_password_nonexistent_email(self, client: AsyncClient):
        # Must return 200 even for unknown emails (anti-enumeration)
        resp = await client.post(
            FORGOT_URL, json={"email": "ghost@example.com"}
        )
        assert resp.status_code == 200

    async def test_forgot_existing_and_nonexistent_return_same_body(
        self, client: AsyncClient, test_user
    ):
        r1 = await client.post(FORGOT_URL, json={"email": test_user.email})
        r2 = await client.post(
            FORGOT_URL, json={"email": "ghost@example.com"}
        )
        assert r1.json()["message"] == r2.json()["message"]


# ── Email verify / reset password (token-based happy path) ───────────────────

class TestVerifyEmail:
    async def test_invalid_verify_token(self, client: AsyncClient):
        resp = await client.post(VERIFY_URL, json={"token": "bad-token"})
        assert resp.status_code == 401

    async def test_invalid_reset_token(self, client: AsyncClient):
        resp = await client.post(
            RESET_URL,
            json={"token": "bad-token", "new_password": "NewPass123!"},
        )
        assert resp.status_code == 401
