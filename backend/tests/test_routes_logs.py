"""Tests for routes/logs.py – activity logs and app logs endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from models import ActivityLog, db


def test_activity_logs_requires_auth(client):
    rv = client.get("/logs/activity")
    assert rv.status_code == 401


def test_activity_logs_requires_admin(client, client_headers):
    rv = client.get("/logs/activity", headers=client_headers)
    assert rv.status_code == 403


def test_activity_logs_empty(client, admin_headers):
    rv = client.get("/logs/activity", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["items"] == []
    assert data["total"] == 0


def test_activity_logs_returns_entries(client, admin_headers, admin_user):
    entry = ActivityLog(
        action="user.login",
        category="auth",
        user_id=admin_user.id,
        details={"email": "admin@test.com"},
        ip_address="127.0.0.1",
    )
    db.session.add(entry)
    db.session.commit()

    rv = client.get("/logs/activity", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "user.login"
    assert data["items"][0]["username"] == "admin_test"


def test_activity_logs_filter_by_category(client, admin_headers):
    db.session.add(ActivityLog(action="user.login", category="auth"))
    db.session.add(ActivityLog(action="matching.run", category="matching"))
    db.session.commit()

    rv = client.get("/logs/activity?category=auth", headers=admin_headers)
    data = rv.get_json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "auth"


def test_activity_logs_filter_by_action(client, admin_headers):
    db.session.add(ActivityLog(action="user.login", category="auth"))
    db.session.add(ActivityLog(action="matching.run", category="matching"))
    db.session.commit()

    rv = client.get("/logs/activity?action=matching", headers=admin_headers)
    data = rv.get_json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "matching.run"


def test_activity_logs_pagination(client, admin_headers):
    for i in range(5):
        db.session.add(ActivityLog(action=f"test.{i}", category="test"))
    db.session.commit()

    rv = client.get("/logs/activity?page=1&per_page=2", headers=admin_headers)
    data = rv.get_json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2


def test_app_logs_requires_auth(client):
    rv = client.get("/logs/app")
    assert rv.status_code == 401


def test_app_logs_requires_admin(client, client_headers):
    rv = client.get("/logs/app", headers=client_headers)
    assert rv.status_code == 403


def test_app_logs_returns_200(client, admin_headers):
    rv = client.get("/logs/app", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert "lines" in data
    assert "total_lines" in data
    assert isinstance(data["lines"], list)


def test_app_logs_reads_file(client, admin_headers, app):
    log_dir = Path(app.root_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    try:
        rv = client.get("/logs/app?lines=2", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data["lines"]) == 2
        assert data["lines"] == ["line2", "line3"]
        assert data["total_lines"] == 3
    finally:
        log_file.unlink(missing_ok=True)
