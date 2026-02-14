"""Helper to record user activity in the activity_logs table."""

import logging

from flask import has_request_context, request

from models import ActivityLog, db

logger = logging.getLogger(__name__)

_CATEGORY_MAP = {
    "user": "auth",
    "import": "import",
    "calculation": "calculation",
}


def _derive_category(action: str) -> str:
    prefix = action.split(".")[0] if "." in action else action
    return _CATEGORY_MAP.get(prefix, prefix)


def log_activity(action, details=None, user_id=None, commit=False):
    """Record an activity log entry.

    Parameters
    ----------
    action : str
        Dotted action name, e.g. ``"user.login"``, ``"matching.run"``.
    details : dict | None
        Arbitrary JSON-serialisable context.
    user_id : int | None
        Explicit user id.  Falls back to ``g.current_user.id``.
    commit : bool
        If ``True``, commit immediately (useful when there is no
        surrounding transaction, e.g. login).  Default is ``False``
        (flush only, letting the caller commit).
    """
    try:
        if user_id is None and has_request_context():
            current_user = getattr(request, "user", None)
            if current_user is not None:
                user_id = current_user.id

        ip_address = None
        if has_request_context():
            ip_address = request.remote_addr

        entry = ActivityLog(
            action=action,
            category=_derive_category(action),
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
    except Exception:
        logger.exception("Failed to record activity log for action=%s", action)
