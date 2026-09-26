"""Shared pytest fixtures for the whole test suite.

Why this file exists: every test needs a Flask app wired to a throwaway
in-memory SQLite database instead of the real Aiven database. The naive
way to do that — call create_app() then overwrite
app.config["SQLALCHEMY_DATABASE_URI"] afterward — looks like it works but
doesn't: Flask-SQLAlchemy builds its actual database engine *inside*
db.init_app(), which runs during create_app() itself, using whatever
DATABASE_URL is in .env at that exact moment. Once that engine object
exists it's permanently bound to that URL; changing app.config afterward
doesn't rebuild it. So test code that "overrides" the database URL after
the fact is silently still pointed at production.

The fix: create_app() accepts a config_class argument specifically so
tests can hand it a different Config subclass *before* db.init_app() ever
runs. TestConfig below is that subclass — every test in this project
should build its app through the `app` fixture here rather than calling
create_app() directly.
"""
import pytest

from app import create_app
from app.config import Config
from app.extensions import db


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
    # Forms carry a CSRF token that a real browser submits automatically.
    # A plain test client doesn't render/parse HTML, so we turn CSRF
    # checking off here rather than hand-scraping the token from every
    # page just to test the view logic.
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
