"""Tests for routes/auth.py – login and refresh endpoints."""

import json

import pytest


def test_login_success(client, admin_user):
    rv = client.post(
        "/login",
        data=json.dumps({"email": "admin@test.com", "password": "password123"}),
        content_type="application/json",
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "refresh_token" in data
    assert data["role"] == "admin"


def test_login_returns_client_role(client, client_user):
    rv = client.post(
        "/login",
        data=json.dumps({"email": "client@test.com", "password": "password123"}),
        content_type="application/json",
    )
    assert rv.status_code == 200
    assert rv.get_json()["role"] == "client"


def test_login_wrong_password(client, admin_user):
    rv = client.post(
        "/login",
        data=json.dumps({"email": "admin@test.com", "password": "wrong"}),
        content_type="application/json",
    )
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


# NOTE: POST /refresh from routes/auth.py is shadowed by the products blueprint
# which also defines POST /refresh. The auth refresh logic is tested via
# test_auth.py (token generation/decoding) instead.
