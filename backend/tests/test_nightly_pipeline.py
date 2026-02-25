"""Tests for utils/nightly_pipeline.py — pipeline orchestrator and email."""

from unittest.mock import MagicMock, patch

import pytest

from models import NightlyConfig, NightlyEmailRecipient, NightlyJob, db


# ---------------------------------------------------------------------------
# run_nightly_pipeline
# ---------------------------------------------------------------------------


class TestRunNightlyPipeline:
    @patch("utils.nightly_pipeline._run_matching_step", return_value=5)
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=2)
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=10)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=True)
    def test_happy_path(self, mock_email, mock_odoo, mock_suppliers, mock_matching):
        from utils.nightly_pipeline import run_nightly_pipeline

        # Add a recipient so email is attempted
        r = NightlyEmailRecipient(email="test@example.com")
        db.session.add(r)
        db.session.commit()

        summary = run_nightly_pipeline()

        assert summary["status"] == "completed"
        assert summary["odoo_synced"] == 10
        assert summary["suppliers_synced"] == 2
        assert summary["matching_submitted"] == 5
        assert summary["email_sent"] is True

        job = NightlyJob.query.order_by(NightlyJob.id.desc()).first()
        assert job is not None
        assert job.status == "completed"
        assert job.odoo_synced == 10

    @patch("utils.nightly_pipeline._run_matching_step", side_effect=RuntimeError("LLM down"))
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=0)
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=0)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=False)
    def test_pipeline_failure(self, mock_email, mock_odoo, mock_suppliers, mock_matching):
        from utils.nightly_pipeline import run_nightly_pipeline

        summary = run_nightly_pipeline()

        assert summary["status"] == "failed"
        assert "LLM down" in summary["error_message"]

        job = NightlyJob.query.order_by(NightlyJob.id.desc()).first()
        assert job.status == "failed"
        assert job.error_message is not None

    @patch("utils.nightly_pipeline._run_matching_step", return_value=0)
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=0)
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=0)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=False)
    def test_no_email_when_no_recipients(self, mock_email, mock_odoo, mock_suppliers, mock_matching):
        from utils.nightly_pipeline import run_nightly_pipeline

        # No recipients in DB
        summary = run_nightly_pipeline()

        assert summary["email_sent"] is False
        mock_email.assert_not_called()


# ---------------------------------------------------------------------------
# send_nightly_email
# ---------------------------------------------------------------------------


class TestSendNightlyEmail:
    def test_returns_false_when_no_recipients(self):
        from utils.nightly_pipeline import send_nightly_email

        job = NightlyJob(status="completed", odoo_synced=5)
        db.session.add(job)
        db.session.commit()

        result = send_nightly_email(job)
        assert result is False

    @patch.dict(
        "os.environ",
        {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "user@example.com",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM": "noreply@example.com",
            "FRONTEND_BASE_URL": "http://localhost:5173",
        },
    )
    @patch("utils.nightly_pipeline.smtplib.SMTP_SSL")
    def test_sends_email_to_active_recipients(self, mock_smtp_cls):
        from utils.nightly_pipeline import send_nightly_email

        r1 = NightlyEmailRecipient(email="alice@example.com", active=True)
        r2 = NightlyEmailRecipient(email="inactive@example.com", active=False)
        db.session.add_all([r1, r2])
        db.session.commit()

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        job = NightlyJob(status="completed", odoo_synced=3, suppliers_synced=1)
        db.session.add(job)
        db.session.commit()

        result = send_nightly_email(job)

        assert result is True
        # sendmail called only for active recipient
        assert mock_server.sendmail.call_count == 1
        call_args = mock_server.sendmail.call_args[0]
        assert "alice@example.com" in call_args

    def test_returns_false_when_smtp_not_configured(self):
        import os
        from utils.nightly_pipeline import send_nightly_email

        # No SMTP_HOST set → skip
        os.environ.pop("SMTP_HOST", None)

        r = NightlyEmailRecipient(email="bob@example.com", active=True)
        db.session.add(r)
        db.session.commit()

        job = NightlyJob(status="completed")
        db.session.add(job)
        db.session.commit()

        result = send_nightly_email(job)
        assert result is False


# ---------------------------------------------------------------------------
# _build_html_report
# ---------------------------------------------------------------------------


class TestBuildHtmlReport:
    @patch.dict("os.environ", {"FRONTEND_BASE_URL": "http://myapp.local"})
    def test_contains_link_and_stats(self):
        from utils.nightly_pipeline import _build_html_report

        job = NightlyJob(
            status="completed",
            odoo_synced=12,
            suppliers_synced=3,
            matching_submitted=50,
        )
        db.session.add(job)
        db.session.commit()

        html = _build_html_report(job)

        assert "http://myapp.local/matching" in html
        assert "12" in html
        assert "3" in html
        assert "50" in html
        assert "B8860B" in html
