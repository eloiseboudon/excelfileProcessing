import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"

# Map PostgreSQL JSONB to SQLite-compatible JSON before importing models
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

_orig_process = SQLiteTypeCompiler.process


def _patched_process(self, type_, **kw):
    if isinstance(type_, JSONB):
        return self.visit_JSON(type_, **kw)
    return _orig_process(self, type_, **kw)


SQLiteTypeCompiler.process = _patched_process

# Force Werkzeug to use pbkdf2 (scrypt unavailable on Python 3.9)
import werkzeug.security as _ws

_orig_gen = _ws.generate_password_hash


def _compat_gen(password, method="pbkdf2:sha256", salt_length=16):
    return _orig_gen(password, method=method, salt_length=salt_length)


_ws.generate_password_hash = _compat_gen

import pytest
from app import create_app
from models import db as _db, User


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config["TESTING"] = True
    with application.app_context():
        _db.create_all()
    yield application


@pytest.fixture(autouse=True)
def _push_ctx(app):
    """Push an app context for every test and clean up after."""
    ctx = app.app_context()
    ctx.push()
    yield
    # clean all rows
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()
    ctx.pop()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user():
    user = User(
        username="admin_test",
        email="admin@test.com",
        role="admin",
    )
    user.set_password("password123")
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def client_user():
    user = User(
        username="client_test",
        email="client@test.com",
        role="client",
    )
    user.set_password("password123")
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def admin_headers(admin_user):
    from utils.auth import generate_access_token

    token = generate_access_token(admin_user)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture()
def client_headers(client_user):
    from utils.auth import generate_access_token

    token = generate_access_token(client_user)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
