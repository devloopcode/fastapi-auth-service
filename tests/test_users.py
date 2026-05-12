"""Integration tests for /api/v1/users endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers

ME_URL = "/api/v1/users/me"
USERS_URL = "/api/v1/users"


# ── GET /users/me ─────────────────────────────────────────────────────────────

class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, test_user):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.get(ME_URL, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "hashed_password" not in data

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get(ME_URL)
        assert resp.status_code == 401


# ── PATCH /users/me ───────────────────────────────────────────────────────────

class TestUpdateMe:
    async def test_update_full_name(self, client: AsyncClient, test_user):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.patch(
            ME_URL, json={"full_name": "Updated Name"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    async def test_update_username(self, client: AsyncClient, test_user):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.patch(
            ME_URL, json={"username": "updated_username"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "updated_username"

    async def test_update_unauthenticated(self, client: AsyncClient):
        resp = await client.patch(ME_URL, json={"full_name": "Hacker"})
        assert resp.status_code == 401


# ── GET /users (admin only) ───────────────────────────────────────────────────

class TestListUsers:
    async def test_list_users_as_admin(self, client: AsyncClient, admin_user):
        headers = await get_auth_headers(client, admin_user.email, "AdminPass123!")
        resp = await client.get(USERS_URL, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "pages" in data

    async def test_list_users_as_regular_user(
        self, client: AsyncClient, test_user
    ):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.get(USERS_URL, headers=headers)
        assert resp.status_code == 403

    async def test_list_users_unauthenticated(self, client: AsyncClient):
        resp = await client.get(USERS_URL)
        assert resp.status_code == 401

    async def test_pagination_params(self, client: AsyncClient, admin_user):
        headers = await get_auth_headers(client, admin_user.email, "AdminPass123!")
        resp = await client.get(USERS_URL + "?page=1&per_page=5", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["per_page"] == 5
        assert data["page"] == 1


# ── DELETE /users/{id} (admin only) ──────────────────────────────────────────

class TestDeleteUser:
    async def test_delete_user_as_admin(
        self, client: AsyncClient, admin_user, test_user
    ):
        headers = await get_auth_headers(client, admin_user.email, "AdminPass123!")
        resp = await client.delete(f"{USERS_URL}/{test_user.id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_nonexistent_user(
        self, client: AsyncClient, admin_user
    ):
        import uuid
        headers = await get_auth_headers(client, admin_user.email, "AdminPass123!")
        resp = await client.delete(
            f"{USERS_URL}/{uuid.uuid4()}", headers=headers
        )
        assert resp.status_code == 404

    async def test_delete_user_as_regular_user(
        self, client: AsyncClient, test_user
    ):
        headers = await get_auth_headers(client, test_user.email, "TestPass123!")
        resp = await client.delete(
            f"{USERS_URL}/{test_user.id}", headers=headers
        )
        assert resp.status_code == 403


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
