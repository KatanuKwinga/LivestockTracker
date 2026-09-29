"""Tests for the password-reset flow added in Week 2: request a reset
link by email, then use the link's token to set a new password.

Uses the same in-memory-SQLite `app`/`client` fixtures as test_auth.py
(see tests/conftest.py). MAIL_SUPPRESS_SEND=True in TestConfig means
mail.send() runs its normal code path — so a real bug building the
message would still raise — but no actual SMTP connection happens, so
these tests need no real Gmail credentials and never send a real email.

Run with: pytest tests/test_password_reset.py -v
"""
from app.extensions import mail
from app.models import User


def register_farmer(client, email="farmer@example.com", password="password123"):
    return client.post(
        "/auth/register",
        data={
            "name": "Test Farmer",
            "email": email,
            "phone": "",
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="farmer@example.com", password="password123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_reset_request_sends_email_for_existing_user(app, client):
    register_farmer(client)

    # record_messages() is Flask-Mail's test hook: while this block is
    # active, every message that would have been sent is instead appended
    # to `outbox`, so we can inspect it without touching a real inbox.
    with mail.record_messages() as outbox:
        response = client.post(
            "/auth/reset-password",
            data={"email": "farmer@example.com"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"If an account with that email exists" in response.data
    assert len(outbox) == 1
    assert outbox[0].recipients == ["farmer@example.com"]
    assert "reset-password" in outbox[0].body


def test_reset_request_shows_same_message_for_unknown_email(app, client):
    # No account was registered with this email at all.
    with mail.record_messages() as outbox:
        response = client.post(
            "/auth/reset-password",
            data={"email": "nobody@example.com"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    # Same generic message as the "real account" case above — this is
    # what stops the form being used to check which emails are registered.
    assert b"If an account with that email exists" in response.data
    assert len(outbox) == 0


def test_reset_password_with_valid_token_changes_password(app, client):
    register_farmer(client, password="original-pass1")

    with app.app_context():
        user = User.query.filter_by(email="farmer@example.com").first()
        token = user.get_reset_token()

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "brand-new-pass1", "confirm_password": "brand-new-pass1"},
        follow_redirects=True,
    )
    assert b"Your password has been updated" in response.data

    # Old password should no longer work...
    response = login(client, password="original-pass1")
    assert b"Invalid email or password" in response.data

    # ...but the new one should.
    response = login(client, password="brand-new-pass1")
    assert b"Welcome, Test Farmer" in response.data


def test_reset_password_rejects_garbage_token(client):
    response = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_reset_password_rejects_expired_token(app, client, monkeypatch):
    register_farmer(client)

    with app.app_context():
        user = User.query.filter_by(email="farmer@example.com").first()
        token = user.get_reset_token()

    # Rather than actually waiting 30+ minutes, move itsdangerous's clock
    # forward 31 minutes. (Verifying with max_age=0 doesn't work: timestamps
    # are whole seconds and a token only expires when age > max_age, so a
    # token made this same second has age 0 and still passes.) This goes
    # through the real route, so it proves the 30-minute expiry end to end.
    import time as real_time
    from itsdangerous import timed

    future = real_time.time() + 31 * 60
    monkeypatch.setattr(timed.time, "time", lambda: future)
    response = client.get(f"/auth/reset-password/{token}", follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_reset_password_rejects_tampered_token(app, client):
    register_farmer(client)

    with app.app_context():
        token = User.query.filter_by(email="farmer@example.com").first().get_reset_token()

    # Change the FIRST character of the signature (the part after the last
    # "."). Changing the last character isn't reliable: base64 packs a
    # couple of unused padding bits into it, so some edits there decode to
    # the exact same signature and the "tampered" token would still pass.
    payload, sig = token.rsplit(".", 1)
    tampered = f"{payload}.{'A' if sig[0] != 'A' else 'B'}{sig[1:]}"
    response = client.get(f"/auth/reset-password/{tampered}", follow_redirects=True)
    assert b"invalid or has expired" in response.data
