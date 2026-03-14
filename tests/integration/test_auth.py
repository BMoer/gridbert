"""Integration tests for auth routes."""

from __future__ import annotations

import pytest


class TestRegister:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "email": "new@user.com",
            "password": "securepass123",
            "name": "New User",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["name"] == "New User"
        assert data["user_id"] > 0

    def test_register_duplicate_email(self, client):
        client.post("/api/auth/register", json={
            "email": "dup@user.com",
            "password": "securepass1",
        })
        res = client.post("/api/auth/register", json={
            "email": "dup@user.com",
            "password": "securepass2",
        })
        assert res.status_code == 409

    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "pass",
        })
        assert res.status_code == 422


class TestLogin:
    def _register(self, client, email="login@test.com", password="securepass123"):
        client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "name": "Tester",
        })

    def test_login_success(self, client):
        self._register(client)
        res = client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "securepass123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        self._register(client)
        res = client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "wrongpass1",
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = client.post("/api/auth/login", json={
            "email": "noone@test.com",
            "password": "somepassword",
        })
        assert res.status_code == 401


class TestProfile:
    def test_get_profile_authenticated(self, client):
        # Register and get token
        res = client.post("/api/auth/register", json={
            "email": "profile@test.com",
            "password": "securepass123",
            "name": "Profiler",
        })
        token = res.json()["access_token"]

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "profile@test.com"
        assert res.json()["name"] == "Profiler"

    def test_get_profile_no_auth(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_get_profile_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert res.status_code == 401
