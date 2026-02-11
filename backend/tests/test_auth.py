"""Tests for utils/auth.py – JWT generation, decoding, decorator."""

import time

import jwt as pyjwt
import pytest
from utils.auth import (
    SECRET_KEY,
    decode_refresh_token,
    decode_token,
    generate_access_token,
    generate_refresh_token,
)


def test_generate_access_token(admin_user):
    token = generate_access_token(admin_user)
    assert isinstance(token, str)
    payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["user_id"] == admin_user.id
    assert payload["type"] == "access"
    assert payload["role"] == "admin"


def test_generate_refresh_token(admin_user):
    token = generate_refresh_token(admin_user)
    payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["user_id"] == admin_user.id
    assert payload["type"] == "refresh"
    assert "role" not in payload


def test_decode_access_token(admin_user):
    token = generate_access_token(admin_user)
    payload = decode_token(token)
    assert payload["user_id"] == admin_user.id
    assert payload["type"] == "access"


def test_decode_refresh_token_ok(admin_user):
    token = generate_refresh_token(admin_user)
    payload = decode_refresh_token(token)
    assert payload["user_id"] == admin_user.id
    assert payload["type"] == "refresh"


def test_decode_access_rejects_refresh(admin_user):
    token = generate_refresh_token(admin_user)
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(token)


def test_decode_refresh_rejects_access(admin_user):
    token = generate_access_token(admin_user)
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_refresh_token(token)


def test_decode_invalid_token():
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token("not.a.token")


def test_token_required_no_header(client, app):
    """Endpoint protected by @token_required returns 401 without token."""
    rv = client.get("/users")
    assert rv.status_code == 401


def test_token_required_bad_token(client, app):
    rv = client.get("/users", headers={"Authorization": "Bearer bad"})
    assert rv.status_code == 401


def test_token_required_wrong_role(client, client_headers):
    """Client role cannot access admin-only endpoints."""
    rv = client.get("/users", headers=client_headers)
    assert rv.status_code == 403
