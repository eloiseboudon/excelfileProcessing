"""Tests for routes/nightly.py — Nightly pipeline API endpoints."""

import json
from unittest.mock import patch

import pytest

from models import NightlyConfig, NightlyEmailRecipient, NightlyJob, db


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestNightlyAuth:
    def test_config_requires_auth(self, client):
        rv = client.get("/nightly/config")
        assert rv.status_code == 401

    def test_config_requires_admin(self, client, client_headers):
        rv = client.get("/nightly/config", headers=client_headers)
        assert rv.status_code == 403

    def test_trigger_requires_auth(self, client):
        rv = client.post("/nightly/trigger")
        assert rv.status_code == 401

    def test_jobs_requires_auth(self, client):
        rv = client.get("/nightly/jobs")
        assert rv.status_code == 401

    def test_recipients_requires_auth(self, client):
        rv = client.get("/nightly/recipients")
        assert rv.status_code == 401


# ---------------------------------------------------------------------------
# GET /nightly/config
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_returns_default_config(self, client, admin_headers):
        rv = client.get("/nightly/config", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["enabled"] is False
        assert "run_hour" in data
        assert "run_minute" in data

    def test_creates_config_if_missing(self, client, admin_headers):
        # Config may have been auto-created; just verify it exists
        rv = client.get("/nightly/config", headers=admin_headers)
        assert rv.status_code == 200
        assert NightlyConfig.query.count() >= 1


# ---------------------------------------------------------------------------
# PUT /nightly/config
# ---------------------------------------------------------------------------


class TestUpdateConfig:
    def test_update_enabled(self, client, admin_headers):
        rv = client.put(
            "/nightly/config",
            headers=admin_headers,
            data=json.dumps({"enabled": True}),
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["enabled"] is True

    def test_update_run_hour(self, client, admin_headers):
        rv = client.put(
            "/nightly/config",
            headers=admin_headers,
            data=json.dumps({"run_hour": 3}),
        )
        assert rv.status_code == 200
        assert rv.get_json()["run_hour"] == 3

    def test_invalid_run_hour(self, client, admin_headers):
        rv = client.put(
            "/nightly/config",
            headers=admin_headers,
            data=json.dumps({"run_hour": 25}),
        )
        assert rv.status_code == 400

    def test_invalid_run_minute(self, client, admin_headers):
        rv = client.put(
            "/nightly/config",
            headers=admin_headers,
            data=json.dumps({"run_minute": 60}),
        )
        assert rv.status_code == 400


# ---------------------------------------------------------------------------
# POST /nightly/trigger
# ---------------------------------------------------------------------------


class TestTrigger:
    @patch("routes.nightly.threading.Thread")
    def test_trigger_returns_202(self, mock_thread, client, admin_headers):
        mock_thread.return_value.start.return_value = None
        rv = client.post("/nightly/trigger", headers=admin_headers)
        assert rv.status_code == 202
        assert rv.get_json()["status"] == "triggered"
        mock_thread.return_value.start.assert_called_once()


# ---------------------------------------------------------------------------
# GET /nightly/jobs
# ---------------------------------------------------------------------------


class TestJobs:
    def test_empty_list(self, client, admin_headers):
        rv = client.get("/nightly/jobs", headers=admin_headers)
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_returns_jobs(self, client, admin_headers):
        job = NightlyJob(status="completed", odoo_synced=10)
        db.session.add(job)
        db.session.commit()

        rv = client.get("/nightly/jobs", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data) == 1
        assert data[0]["status"] == "completed"
        assert data[0]["odoo_synced"] == 10

    def test_get_single_job(self, client, admin_headers):
        job = NightlyJob(status="running")
        db.session.add(job)
        db.session.commit()

        rv = client.get(f"/nightly/jobs/{job.id}", headers=admin_headers)
        assert rv.status_code == 200
        assert rv.get_json()["id"] == job.id

    def test_get_unknown_job_404(self, client, admin_headers):
        rv = client.get("/nightly/jobs/9999", headers=admin_headers)
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Recipients CRUD
# ---------------------------------------------------------------------------


class TestRecipients:
    def test_list_empty(self, client, admin_headers):
        rv = client.get("/nightly/recipients", headers=admin_headers)
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_recipient(self, client, admin_headers):
        rv = client.post(
            "/nightly/recipients",
            headers=admin_headers,
            data=json.dumps({"email": "bob@example.com", "name": "Bob"}),
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["email"] == "bob@example.com"
        assert data["name"] == "Bob"
        assert data["active"] is True

    def test_add_duplicate_returns_409(self, client, admin_headers):
        r = NightlyEmailRecipient(email="alice@example.com")
        db.session.add(r)
        db.session.commit()

        rv = client.post(
            "/nightly/recipients",
            headers=admin_headers,
            data=json.dumps({"email": "alice@example.com"}),
        )
        assert rv.status_code == 409

    def test_add_missing_email_400(self, client, admin_headers):
        rv = client.post(
            "/nightly/recipients",
            headers=admin_headers,
            data=json.dumps({"name": "No Email"}),
        )
        assert rv.status_code == 400

    def test_delete_recipient(self, client, admin_headers):
        r = NightlyEmailRecipient(email="delete@example.com")
        db.session.add(r)
        db.session.commit()

        rv = client.delete(
            f"/nightly/recipients/{r.id}", headers=admin_headers
        )
        assert rv.status_code == 204
        assert NightlyEmailRecipient.query.get(r.id) is None

    def test_delete_unknown_404(self, client, admin_headers):
        rv = client.delete("/nightly/recipients/9999", headers=admin_headers)
        assert rv.status_code == 404
