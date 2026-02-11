"""Tests for routes/users.py – CRUD user management."""

import json

import pytest


# ── GET /users ──────────────────────────────────────────────────────


def test_list_users(client, admin_headers, admin_user):
    rv = client.get("/users", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert any(u["email"] == "admin@test.com" for u in data)


def test_list_users_forbidden_for_client(client, client_headers):
    rv = client.get("/users", headers=client_headers)
    assert rv.status_code == 403


# ── POST /users ─────────────────────────────────────────────────────


def test_create_user(client, admin_headers, admin_user):
    rv = client.post(
        "/users",
        data=json.dumps({"email": "new@test.com", "role": "client"}),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "client"


def test_create_user_missing_email(client, admin_headers, admin_user):
    rv = client.post(
        "/users",
        data=json.dumps({"role": "client"}),
        headers=admin_headers,
    )
    assert rv.status_code == 400


def test_create_user_duplicate(client, admin_headers, admin_user):
    rv = client.post(
        "/users",
        data=json.dumps({"email": "admin@test.com"}),
        headers=admin_headers,
    )
    assert rv.status_code == 400


# ── PUT /users/<id> ─────────────────────────────────────────────────


def test_update_user(client, admin_headers, admin_user):
    rv = client.put(
        f"/users/{admin_user.id}",
        data=json.dumps({"first_name": "Updated"}),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "success"


# ── DELETE /users/<id> ──────────────────────────────────────────────


def test_delete_user(client, admin_headers, admin_user, client_user):
    rv = client.delete(
        f"/users/{client_user.id}",
        headers=admin_headers,
    )
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "success"
