from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadSignature, SignatureExpired

from app.extensions import db, login_manager


class User(db.Model):
    """Base identity table. A row here is either a Farmer or a Worker,
    linked via the one-to-one farmer/worker tables below."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    farmer = db.relationship("Farmer", back_populates="user", uselist=False)
    worker = db.relationship("Worker", back_populates="user", uselist=False)

    def get_reset_token(self, expires_sec=1800):
        """Build a signed, self-expiring password-reset token — no new
        database table needed for this.

        itsdangerous (a dependency Flask itself already uses, for signed
        session cookies) encodes {"user_id": self.id} together with a
        timestamp, then signs the whole thing with the app's SECRET_KEY.
        Anyone can *read* the token's structure, but nobody can *forge* or
        *edit* one without knowing SECRET_KEY, and verify_reset_token()
        below rejects it outright once expires_sec (default 30 minutes)
        has passed. That combination — tamper-proof and time-limited — is
        exactly what a "reset my password" link needs to be safe to email.
        """
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps({"user_id": self.id}, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """The other half of get_reset_token(): decode + verify a token
        from an incoming request. Returns the matching User, or None if
        the token was tampered with, expired, or malformed."""
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = serializer.loads(token, salt="password-reset", max_age=expires_sec)
        except (BadSignature, SignatureExpired):
            return None
        return db.session.get(User, data.get("user_id"))


class Farmer(UserMixin, db.Model):
    __tablename__ = "farmers"

    farmer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    user = db.relationship("User", back_populates="farmer")
    workers = db.relationship("Worker", back_populates="farmer", cascade="all, delete-orphan")
    livestock = db.relationship("Livestock", back_populates="farmer")

    # Flask-Login needs get_id() to return a string uniquely identifying
    # this account. We prefix so a farmer id and a worker id never collide.
    def get_id(self):
        return f"farmer:{self.farmer_id}"

    @property
    def name(self):
        return self.user.name

    @property
    def email(self):
        return self.user.email


class Worker(UserMixin, db.Model):
    __tablename__ = "workers"

    worker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey("farmers.farmer_id"), nullable=False)

    user = db.relationship("User", back_populates="worker")
    farmer = db.relationship("Farmer", back_populates="workers")

    def get_id(self):
        return f"worker:{self.worker_id}"

    @property
    def name(self):
        return self.user.name

    @property
    def email(self):
        return self.user.email


@login_manager.user_loader
def load_user(prefixed_id):
    """Flask-Login calls this on every request with whatever get_id()
    returned at login time. The prefix tells us which table to query."""
    try:
        kind, raw_id = prefixed_id.split(":")
        raw_id = int(raw_id)
    except (ValueError, AttributeError):
        return None

    if kind == "farmer":
        return Farmer.query.get(raw_id)
    if kind == "worker":
        return Worker.query.get(raw_id)
    return None
