"""Tests for utils/nightly_pipeline.py — pipeline orchestrator and email."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import LabelCache, NightlyEmailRecipient, NightlyJob, PendingMatch, db


# ---------------------------------------------------------------------------
# run_nightly_pipeline
# ---------------------------------------------------------------------------


class TestRunNightlyPipeline:
    @patch("utils.nightly_pipeline._run_matching_step", return_value={"total_products": 5, "run_id": None})
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=2)
    @patch("utils.nightly_pipeline._run_assign_types_step", return_value={"classified": 3, "unclassified": 1, "total": 4})
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=10)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=True)
    def test_happy_path(self, mock_email, mock_odoo, mock_assign, mock_suppliers, mock_matching):
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

        mock_assign.assert_called_once()

        job = NightlyJob.query.order_by(NightlyJob.id.desc()).first()
        assert job is not None
        assert job.status == "completed"
        assert job.odoo_synced == 10

    @patch("utils.nightly_pipeline._run_matching_step", side_effect=RuntimeError("LLM down"))
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=0)
    @patch("utils.nightly_pipeline._run_assign_types_step", return_value={"classified": 0, "unclassified": 0, "total": 0})
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=0)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=False)
    def test_pipeline_failure(self, mock_email, mock_odoo, mock_assign, mock_suppliers, mock_matching):
        from utils.nightly_pipeline import run_nightly_pipeline

        summary = run_nightly_pipeline()

        assert summary["status"] == "failed"
        assert "LLM down" in summary["error_message"]

        job = NightlyJob.query.order_by(NightlyJob.id.desc()).first()
        assert job.status == "failed"
        assert job.error_message is not None

    @patch("utils.nightly_pipeline._run_matching_step", return_value={"total_products": 0, "run_id": None})
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=0)
    @patch("utils.nightly_pipeline._run_assign_types_step", return_value={"classified": 0, "unclassified": 0, "total": 0})
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=0)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=False)
    def test_no_email_when_no_recipients(self, mock_email, mock_odoo, mock_assign, mock_suppliers, mock_matching):
        from utils.nightly_pipeline import run_nightly_pipeline

        # No recipients in DB
        summary = run_nightly_pipeline()

        assert summary["email_sent"] is False
        mock_email.assert_not_called()

    @patch("utils.nightly_pipeline._run_matching_step", return_value={"total_products": 3, "run_id": None})
    @patch("utils.nightly_pipeline._run_suppliers_step", return_value=1)
    @patch("utils.nightly_pipeline._run_assign_types_step", side_effect=RuntimeError("classifier error"))
    @patch("utils.nightly_pipeline._run_odoo_step", return_value=5)
    @patch("utils.nightly_pipeline.send_nightly_email", return_value=False)
    def test_assign_types_failure_is_non_fatal(self, mock_email, mock_odoo, mock_assign, mock_suppliers, mock_matching):
        """A failing assign-types step must not abort the pipeline."""
        from utils.nightly_pipeline import run_nightly_pipeline

        summary = run_nightly_pipeline()

        assert summary["status"] == "completed"
        assert summary["matching_submitted"] == 3


# ---------------------------------------------------------------------------
# _run_assign_types_step
# ---------------------------------------------------------------------------


class TestRunAssignTypesStep:
    def _make_device_type(self, name: str):
        from models import DeviceType
        dt = DeviceType(type=name)
        db.session.add(dt)
        db.session.flush()
        return dt

    def _make_product(self, model: str, type_id=None):
        from models import Product
        p = Product(description=model, model=model, type_id=type_id)
        db.session.add(p)
        db.session.flush()
        return p

    def test_assigns_type_to_product_with_null_type(self):
        from utils.nightly_pipeline import _run_assign_types_step

        dt_phone = self._make_device_type("Smartphone")
        self._make_device_type("a définir")
        p = self._make_product("iPhone 15 128GB DS")
        db.session.commit()

        result = _run_assign_types_step()

        assert result["classified"] >= 1
        db.session.refresh(p)
        assert p.type_id == dt_phone.id

    def test_reassigns_product_with_skip_type(self):
        from models import DeviceType
        from utils.nightly_pipeline import _run_assign_types_step

        dt_skip = self._make_device_type("a définir")
        dt_audio = self._make_device_type("Audio")
        p = self._make_product("AirPods Pro 2", type_id=dt_skip.id)
        db.session.commit()

        result = _run_assign_types_step()

        assert result["total"] >= 1
        db.session.refresh(p)
        assert p.type_id == dt_audio.id

    def test_returns_zero_when_nothing_to_classify(self):
        from models import DeviceType, Product
        from utils.nightly_pipeline import _run_assign_types_step

        dt = self._make_device_type("Smartphone")
        p = self._make_product("Galaxy S24", type_id=dt.id)
        db.session.commit()

        result = _run_assign_types_step()

        assert result["total"] == 0
        assert result["classified"] == 0
        assert result["unclassified"] == 0

    def test_unclassified_gets_fallback_type(self):
        from utils.nightly_pipeline import _run_assign_types_step

        dt_fallback = self._make_device_type("a définir")
        p = self._make_product("Produit Inconnu XYZ123")
        db.session.commit()

        result = _run_assign_types_step()

        assert result["unclassified"] >= 1
        db.session.refresh(p)
        assert p.type_id == dt_fallback.id


# ---------------------------------------------------------------------------
# _apply_validation_history
# ---------------------------------------------------------------------------


class TestApplyValidationHistory:
    def _make_supplier(self):
        from models import Supplier
        s = Supplier(name="TestSupplier")
        db.session.add(s)
        db.session.flush()
        return s

    def _make_product(self):
        from models import Product
        p = Product(description="iPhone 16 128GB")
        db.session.add(p)
        db.session.flush()
        return p

    def test_auto_validates_matching_top_candidate(self):
        from utils.nightly_pipeline import _apply_validation_history

        s = self._make_supplier()
        p = self._make_product()
        db.session.commit()

        # Tonight's pending match: top candidate == yesterday's validated product
        pm = PendingMatch(
            supplier_id=s.id,
            source_label="iphone 16 128gb",
            extracted_attributes={},
            candidates=[{"product_id": p.id, "score": 75}],
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()

        history = {("iphone 16 128gb", s.id): p.id}
        count = _apply_validation_history(history)

        assert count == 1
        db.session.refresh(pm)
        assert pm.status == "validated"
        assert pm.resolved_product_id == p.id

    def test_leaves_pending_when_match_changed(self):
        from models import Product
        from utils.nightly_pipeline import _apply_validation_history

        s = self._make_supplier()
        p1 = self._make_product()
        p2 = Product(description="iPhone 16 256GB")
        db.session.add(p2)
        db.session.commit()

        # Tonight's top candidate changed (p2 instead of p1)
        pm = PendingMatch(
            supplier_id=s.id,
            source_label="iphone 16 128gb",
            extracted_attributes={},
            candidates=[{"product_id": p2.id, "score": 72}],
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()

        history = {("iphone 16 128gb", s.id): p1.id}
        count = _apply_validation_history(history)

        assert count == 0
        db.session.refresh(pm)
        assert pm.status == "pending"  # stays pending for morning review

    def test_restores_label_cache_product_id(self):
        from utils.nightly_pipeline import _apply_validation_history

        s = self._make_supplier()
        p = self._make_product()
        db.session.commit()

        lc = LabelCache(
            supplier_id=s.id,
            normalized_label="iphone 16 128gb",
            match_source="extracted",
            extracted_attributes={"brand": "apple"},
            product_id=None,
        )
        db.session.add(lc)

        pm = PendingMatch(
            supplier_id=s.id,
            source_label="iphone 16 128gb",
            extracted_attributes={},
            candidates=[{"product_id": p.id, "score": 80}],
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()

        history = {("iphone 16 128gb", s.id): p.id}
        _apply_validation_history(history)

        db.session.refresh(lc)
        assert lc.product_id == p.id


# ---------------------------------------------------------------------------
# _run_matching_step (nightly mode)
# ---------------------------------------------------------------------------


class TestRunMatchingStepNightly:
    @patch("utils.llm_matching.run_matching_job")
    def test_calls_skip_already_matched(self, mock_run):
        from utils.nightly_pipeline import _run_matching_step

        mock_run.return_value = {"total_products": 10, "llm_calls": 2, "auto_matched": 3, "pending_review": 7}

        _run_matching_step()

        mock_run.assert_called_once_with(
            supplier_id=None, limit=None, skip_already_matched=True
        )

    @patch("utils.llm_matching.run_matching_job")
    def test_resets_label_cache_product_ids(self, mock_run):
        from models import Supplier
        from utils.nightly_pipeline import _run_matching_step

        mock_run.return_value = {"total_products": 0, "llm_calls": 0, "auto_matched": 0, "pending_review": 0}

        s = Supplier(name="S2")
        db.session.add(s)
        db.session.commit()

        lc = LabelCache(
            supplier_id=s.id,
            normalized_label="lbl",
            match_source="auto",
            product_id=42,
        )
        db.session.add(lc)
        db.session.commit()

        _run_matching_step()

        # LabelCache product_id should have been cleared before matching
        db.session.refresh(lc)
        assert lc.product_id is None


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

    def test_returns_false_when_webhook_not_configured(self):
        import os
        from utils.nightly_pipeline import send_nightly_email

        os.environ.pop("NIGHTLY_WEBHOOK_URL", None)

        r = NightlyEmailRecipient(email="bob@example.com", active=True)
        db.session.add(r)
        db.session.commit()

        job = NightlyJob(status="completed")
        db.session.add(job)
        db.session.commit()

        result = send_nightly_email(job)
        assert result is False

    @patch.dict(
        "os.environ",
        {
            "NIGHTLY_WEBHOOK_URL": "http://n8n.local/webhook/nightly",
            "FRONTEND_URL": "http://localhost:5173",
        },
    )
    @patch("utils.nightly_pipeline.urllib.request.urlopen")
    def test_calls_webhook_with_recipients(self, mock_urlopen):
        from utils.nightly_pipeline import send_nightly_email

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        r1 = NightlyEmailRecipient(email="alice@example.com", active=True)
        r2 = NightlyEmailRecipient(email="inactive@example.com", active=False)
        db.session.add_all([r1, r2])
        db.session.commit()

        job = NightlyJob(status="completed", odoo_synced=3, suppliers_synced=1)
        db.session.add(job)
        db.session.commit()

        result = send_nightly_email(job)

        assert result is True
        mock_urlopen.assert_called_once()

        # Verify payload contains only active recipient
        import json as _json
        req = mock_urlopen.call_args[0][0]
        payload = _json.loads(req.data)
        assert payload["recipients"] == ["alice@example.com"]
        assert payload["status"] == "completed"
        assert "validation_url" in payload
        assert "html_body" in payload


# ---------------------------------------------------------------------------
# _build_html_report
# ---------------------------------------------------------------------------


class TestBuildHtmlReport:
    @patch.dict("os.environ", {"FRONTEND_URL": "http://myapp.local"})
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
