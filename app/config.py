import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail settings for password-reset emails, read from .env so no real
    # credentials ever get committed to the repo. Defaults here point at
    # Gmail's SMTP server on the standard STARTTLS port (587) — pairing
    # this with a Gmail "app password" (not your real Gmail password) is
    # the quickest way to get outgoing email working for a project this
    # size. MAIL_USERNAME/MAIL_PASSWORD/MAIL_DEFAULT_SENDER are left unset
    # by default so a missing .env fails loudly (an auth error when
    # sending) rather than silently mailing from nowhere.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    # Falls back to MAIL_USERNAME so you only have to set one value for a
    # simple setup where the sending account and the "from" address are
    # the same Gmail account.
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # Where ml/train.py saves the sickness-risk model and the /predictions
    # page loads it from. Overridable so tests can point at a temp file.
    ML_MODEL_PATH = os.environ.get(
        "ML_MODEL_PATH", os.path.join(BASE_DIR, "ml", "artifacts", "sickness_model.joblib")
    )
