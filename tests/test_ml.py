"""Tests for the ML pipeline (ml/) and the /predictions page.

The first group needs only pandas/scikit-learn; the route tests at the
bottom use the usual in-memory SQLite `app`/`client` fixtures from
tests/conftest.py.

Run with: pytest tests/test_ml.py -v
"""
import json
from datetime import date

import pandas as pd
import pytest

from ml.features import FEATURE_COLUMNS, build_current_features, build_training_set
from ml.predict import load_model, score_frames
from ml.synthetic import generate_synthetic_data
from ml.train import train_from_frames


@pytest.fixture(scope="module")
def trained_model_path(tmp_path_factory):
    """Train once on synthetic data and share the model across tests —
    training is the slow part, so we don't repeat it per test."""
    frames = generate_synthetic_data(n_animals=150, seed=1)
    path = tmp_path_factory.mktemp("model") / "sickness_model.joblib"
    train_from_frames(frames["livestock"], frames["weights"], frames["health"], path, "synthetic", verbose=False)
    return path


def tiny_farm(extra_weights=(), extra_health=()):
    """One goat with a hand-written history, for precise feature checks."""
    livestock = pd.DataFrame([{"animal_id": 1, "species": "GOAT", "gender": "FEMALE",
                               "breed": "Galla", "date_of_birth": "2025-01-01"}])
    weights = pd.DataFrame(
        [{"animal_id": 1, "date": d, "weight": w} for d, w in [
            ("2026-01-01", 30.0), ("2026-01-15", 31.0), ("2026-01-29", 32.0),
            ("2026-02-12", 33.0), ("2026-02-26", 31.0),  # last one: a dip
        ]] + list(extra_weights)
    )
    health = pd.DataFrame(
        [{"animal_id": 1, "date": "2025-12-01", "disease": None, "description": "",
          "treatment": "PPR vaccine", "dosage": "1 dose"}] + list(extra_health),
        columns=["animal_id", "date", "disease", "description", "treatment", "dosage"],
    )
    return livestock, weights, health


# ---------------------------------------------------------------- core ML

def test_synthetic_data_has_expected_shape():
    frames = generate_synthetic_data(n_animals=30, seed=3)
    assert len(frames["livestock"]) == 30
    assert set(frames["livestock"]["species"]) <= {"CATTLE", "GOAT", "SHEEP", "CHICKEN"}
    assert frames["weights"]["date"].max().date() <= date.today()
    assert frames["health"]["disease"].notna().any(), "simulation should produce some illnesses"


def test_features_never_use_records_after_the_snapshot_date():
    """The data-leakage guard: adding records dated AFTER the snapshot
    must not change any feature value."""
    as_of = "2026-03-01"
    before = build_current_features(*tiny_farm(), as_of=as_of)
    after = build_current_features(*tiny_farm(
        extra_weights=[{"animal_id": 1, "date": "2026-03-05", "weight": 20.0}],
        extra_health=[{"animal_id": 1, "date": "2026-03-04", "disease": "PPR", "description": "",
                       "treatment": "Supportive care", "dosage": ""}],
    ), as_of=as_of)
    pd.testing.assert_frame_equal(before[FEATURE_COLUMNS], after[FEATURE_COLUMNS])


def test_weight_dip_shows_up_in_features():
    features = build_current_features(*tiny_farm(), as_of="2026-03-01").iloc[0]
    assert features["weight_change_14d_pct"] < 0     # 33 -> 31 kg
    assert features["weight_vs_trend_pct"] < -5      # trend predicted ~34 kg
    assert features["vaccinated_180d"] == 1


def test_label_is_illness_within_horizon():
    illness_soon = [{"animal_id": 1, "date": "2026-03-20", "disease": "PPR", "description": "",
                     "treatment": "Supportive care", "dosage": ""}]
    # Extend weigh-ins so there's room for snapshots before the illness.
    more_weights = [{"animal_id": 1, "date": f"2026-{m:02d}-01", "weight": 33.0} for m in range(3, 8)]
    ds = build_training_set(*tiny_farm(more_weights, illness_soon), horizon_days=14, step_days=1)
    labels = ds.set_index("snapshot_date")["label"]
    assert labels[pd.Timestamp("2026-03-10")] == 1   # 10 days before illness
    assert labels[pd.Timestamp("2026-03-01")] == 0   # 19 days before: outside 14-day window


def test_training_saves_model_that_beats_chance(trained_model_path):
    artifact = load_model(trained_model_path)
    assert artifact["test_metrics"]["roc_auc"] > 0.6
    assert artifact["model_name"] in {"logistic_regression", "random_forest", "gradient_boosting"}
    metrics_file = trained_model_path.with_name("sickness_model_metrics.json")
    assert json.loads(metrics_file.read_text())["horizon_days"] == artifact["horizon_days"]


def test_scoring_a_new_farm(trained_model_path):
    artifact = load_model(trained_model_path)
    farm = generate_synthetic_data(n_animals=20, seed=99)
    result = score_frames(artifact, farm["livestock"], farm["weights"], farm["health"])
    assert len(result) == 20
    assert result["probability"].between(0, 1).all()
    assert set(result["risk_band"]) <= {"High", "Medium", "Low", "Under treatment"}


# ---------------------------------------------------------------- routes

def register_and_login(client, email="farmer@example.com"):
    client.post("/auth/register", data={
        "name": "Test Farmer", "email": email, "phone": "",
        "password": "password123", "confirm_password": "password123",
    })
    client.post("/auth/login", data={"email": email, "password": "password123"})


def test_predictions_page_when_model_missing(app, client, tmp_path):
    app.config["ML_MODEL_PATH"] = str(tmp_path / "nope.joblib")
    register_and_login(client)
    response = client.get("/predictions")
    assert b"hasn&#39;t been trained yet" in response.data or b"hasn't been trained yet" in response.data


def test_predictions_page_lists_seeded_animals(app, client, trained_model_path):
    from app.models import User
    from ml.data import remove_synthetic, seed_synthetic

    app.config["ML_MODEL_PATH"] = str(trained_model_path)
    register_and_login(client)
    farmer_id = User.query.filter_by(email="farmer@example.com").first().farmer.farmer_id
    seed_synthetic(generate_synthetic_data(n_animals=15, seed=5), farmer_id)

    response = client.get("/predictions")
    assert response.status_code == 200
    assert b"Health risk predictions" in response.data
    assert response.data.count(b'class="badge ') >= 15 + 4  # 15 rows + 4 summary tiles

    assert remove_synthetic(farmer_id) == 15


def test_workers_cannot_see_predictions(client):
    register_and_login(client)
    client.post("/auth/workers/new", data={
        "name": "Test Worker", "email": "worker@example.com", "phone": "",
        "password": "workerpass1", "confirm_password": "workerpass1",
    })
    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "worker@example.com", "password": "workerpass1"})
    response = client.get("/predictions", follow_redirects=True)
    assert b"Only a farmer account can view health predictions" in response.data
