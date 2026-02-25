"""Tests for routes/auth.py – login, refresh (cookie) and logout endpoints."""

import json

import pytest


def _login(client, email="admin@test.com", password="password123"):
    """Helper: login and return the response."""
    return client.post(
        "/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )


def test_login_success(client, admin_user):
    rv = _login(client)
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "refresh_token" not in data  # no longer in JSON body
    assert data["role"] == "admin"
    # Refresh token is now an HTTPOnly cookie
    set_cookie = rv.headers.get("Set-Cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie


def test_login_returns_client_role(client, client_user):
    rv = _login(client, email="client@test.com")
    assert rv.status_code == 200
    assert rv.get_json()["role"] == "client"


def test_login_wrong_password(client, admin_user):
    rv = _login(client, password="wrong")
    assert rv.status_code == 401


def test_login_missing_fields(client):
    rv = client.post(
        "/login",
        data=json.dumps({"email": "admin@test.com"}),
        content_type="application/json",
    )
    assert rv.status_code == 400


def test_login_empty_body(client):
    rv = client.post(
        "/login",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert rv.status_code == 400


def test_login_unknown_user(client):
    rv = client.post(
        "/login",
        data=json.dumps({"email": "unknown@test.com", "password": "x"}),
        content_type="application/json",
    )
    assert rv.status_code == 401


def test_refresh_with_cookie(client, admin_user):
    """After login, the test client stores the cookie and sends it automatically."""
    login_rv = _login(client)
    assert login_rv.status_code == 200

    rv = client.post("/refresh")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "role" in data
    assert "refresh_token" not in data  # still only in cookie
    # A new cookie should be set (token rotation)
    assert "refresh_token=" in rv.headers.get("Set-Cookie", "")


def test_refresh_without_cookie_returns_401(client):
    rv = client.post("/refresh")
    assert rv.status_code == 401


def test_logout_clears_cookie(client, admin_user):
    login_rv = _login(client)
    assert login_rv.status_code == 200

    rv = client.post("/logout")
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "ok"
    # Cookie should be cleared (Max-Age=0 or expires in the past)
    set_cookie = rv.headers.get("Set-Cookie", "")
    assert "refresh_token=" in set_cookie

    # After logout, refresh should fail
    rv = client.post("/refresh")
    assert rv.status_code == 401
