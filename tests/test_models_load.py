"""Run this first, before anything else: `pytest tests/test_models_load.py -v`

It doesn't test business logic yet (that comes in later steps) — it only
proves the models import cleanly and every table can actually be created,
which is where circular-FK and typo bugs show up immediately instead of
three steps from now when they're harder to trace.
"""
from app import create_app
from app.extensions import db


def test_app_creates_and_tables_build():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        from app.models import (
            User, Farmer, Worker, Livestock, BreedingRecord,
            WeightRecord, HealthRecord, MortalityRecord,
            CommercialInfo, ProductionData,
        )
        expected_tables = {
            "users", "farmers", "workers", "livestock", "breeding_record",
            "weight_records", "health_records", "mortality_records",
            "commercial_info", "production_data",
        }
        actual_tables = set(db.metadata.tables.keys())
        assert expected_tables.issubset(actual_tables), (
            f"Missing tables: {expected_tables - actual_tables}"
        )
        db.drop_all()
