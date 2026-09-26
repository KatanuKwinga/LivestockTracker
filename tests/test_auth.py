"""Auth flow tests: farmer registration, login/logout, and the
farmer-only worker-creation route. Runs against an in-memory SQLite
database, same as tests/test_models_load.py — no real credentials or
network access needed to run this file.

The `client` fixture used below comes from tests/conftest.py, which
builds the Flask app with a test-only config from the start (see that
file's docstring for why that matters — overriding the database URL
*after* create_app() runs doesn't actually work).

Run with: pytest tests/test_auth.py -v
"""


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


def test_farmer_can_register(client):
    response = register_farmer(client)
    assert response.status_code == 200
    assert b"Account created" in response.data


def test_cannot_register_duplicate_email(client):
    register_farmer(client)
    response = register_farmer(client)  # same email again
    assert b"already exists" in response.data


def test_farmer_can_login_and_reach_dashboard(client):
    register_farmer(client)
    response = login(client)
    assert response.status_code == 200
    assert b"Welcome, Test Farmer" in response.data


def test_login_fails_with_wrong_password(client):
    register_farmer(client)
    response = login(client, password="wrong-password")
    assert b"Invalid email or password" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in to continue" in response.data


def test_farmer_can_create_worker(client):
    register_farmer(client)
    login(client)
    response = client.post(
        "/auth/workers/new",
        data={
            "name": "Test Worker",
            "email": "worker@example.com",
            "phone": "",
            "password": "workerpass1",
            "confirm_password": "workerpass1",
        },
        follow_redirects=True,
    )
    assert b"Worker account created" in response.data

    # And the worker can now log in on their own.
    client.get("/auth/logout")
    response = login(client, email="worker@example.com", password="workerpass1")
    assert b"Welcome, Test Worker" in response.data


def test_worker_cannot_create_another_worker(client):
    register_farmer(client)
    login(client)
    client.post(
        "/auth/workers/new",
        data={
            "name": "Test Worker",
            "email": "worker@example.com",
            "phone": "",
            "password": "workerpass1",
            "confirm_password": "workerpass1",
        },
        follow_redirects=True,
    )
    client.get("/auth/logout")
    login(client, email="worker@example.com", password="workerpass1")

    response = client.post(
        "/auth/workers/new",
        data={
            "name": "Second Worker",
            "email": "worker2@example.com",
            "phone": "",
            "password": "workerpass1",
            "confirm_password": "workerpass1",
        },
        follow_redirects=True,
    )
    assert b"Only a farmer account can add workers" in response.data
