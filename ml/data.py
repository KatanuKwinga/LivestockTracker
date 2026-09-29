"""Moving data between the database and pandas.

load_frames()        DB -> DataFrames, the input to features.py
seed_synthetic(...)  synthetic DataFrames -> DB rows owned by one farmer
remove_synthetic(..) delete those seeded rows again

All functions must be called inside a Flask app context (they use
db.session), e.g. `with app.app_context(): load_frames()`.

Synthetic animals are tagged by starting their description with
SYNTHETIC_TAG, so they can always be told apart from real animals and
cleanly removed before the system goes into real use.
"""

import pandas as pd
from sqlalchemy import delete, insert, select

from app.extensions import db
from app.models import HealthRecord, Livestock, MortalityRecord, WeightRecord

SYNTHETIC_TAG = "[synthetic]"


def load_frames(farmer_id=None, include_dead=False):
    """Read livestock, weights and health records into DataFrames shaped
    like ml/synthetic.py's output. farmer_id=None loads every farm (used
    for training — more data = better model); pass an id to score one
    farmer's herd."""
    animals_q = select(
        Livestock.animal_id, Livestock.farmer_id, Livestock.species,
        Livestock.gender, Livestock.breed, Livestock.date_of_birth,
    )
    if farmer_id is not None:
        animals_q = animals_q.where(Livestock.farmer_id == farmer_id)
    if not include_dead:
        dead_ids = select(MortalityRecord.animal_id)
        animals_q = animals_q.where(Livestock.animal_id.not_in(dead_ids))

    livestock = pd.DataFrame(
        db.session.execute(animals_q).all(),
        columns=["animal_id", "farmer_id", "species", "gender", "breed", "date_of_birth"],
    )
    ids = livestock["animal_id"].tolist()

    if ids:
        weight_rows = db.session.execute(
            select(WeightRecord.animal_id, WeightRecord.date, WeightRecord.weight)
            .where(WeightRecord.animal_id.in_(ids))
        ).all()
        health_rows = db.session.execute(
            select(HealthRecord.animal_id, HealthRecord.date, HealthRecord.disease,
                   HealthRecord.description, HealthRecord.treatment, HealthRecord.dosage)
            .where(HealthRecord.animal_id.in_(ids))
        ).all()
    else:
        weight_rows, health_rows = [], []

    weights = pd.DataFrame(weight_rows, columns=["animal_id", "date", "weight"])
    health = pd.DataFrame(health_rows, columns=["animal_id", "date", "disease", "description", "treatment", "dosage"])

    livestock["date_of_birth"] = pd.to_datetime(livestock["date_of_birth"])
    weights["date"] = pd.to_datetime(weights["date"])
    health["date"] = pd.to_datetime(health["date"])
    return {"livestock": livestock, "weights": weights, "health": health}


def seed_synthetic(frames, farmer_id):
    """Insert synthetic animals + their records under one farmer's account.
    Returns the number of animals inserted."""
    id_map = {}
    for row in frames["livestock"].itertuples(index=False):
        animal = Livestock(
            farmer_id=farmer_id,
            species=row.species,
            gender=row.gender,
            breed=row.breed,
            date_of_birth=row.date_of_birth.date(),
            description=f"{SYNTHETIC_TAG} simulated {row.species.lower()} for ML development",
        )
        db.session.add(animal)
        db.session.flush()  # assigns animal.animal_id so records can point at it
        id_map[row.animal_id] = animal.animal_id

    # Bulk inserts: one round-trip per table instead of one per row,
    # which matters a lot against a cloud database like Aiven.
    weight_dicts = [
        {"animal_id": id_map[r.animal_id], "date": r.date.date(), "weight": float(r.weight)}
        for r in frames["weights"].itertuples(index=False)
    ]
    health_dicts = [
        {
            "animal_id": id_map[r.animal_id], "date": r.date.date(),
            "disease": r.disease if isinstance(r.disease, str) else None,
            "description": r.description, "treatment": r.treatment, "dosage": r.dosage,
        }
        for r in frames["health"].itertuples(index=False)
    ]
    if weight_dicts:
        db.session.execute(insert(WeightRecord), weight_dicts)
    if health_dicts:
        db.session.execute(insert(HealthRecord), health_dicts)
    db.session.commit()
    return len(id_map)


def remove_synthetic(farmer_id):
    """Delete every synthetic animal belonging to this farmer, plus its
    weight and health records. Uses three bulk DELETE statements (children
    first, so foreign keys are never left dangling) rather than deleting
    animal-by-animal, which would be hundreds of round-trips to Aiven."""
    ids = db.session.execute(
        select(Livestock.animal_id).where(
            Livestock.farmer_id == farmer_id,
            Livestock.description.like(f"{SYNTHETIC_TAG}%"),
        )
    ).scalars().all()
    if not ids:
        return 0
    db.session.execute(delete(WeightRecord).where(WeightRecord.animal_id.in_(ids)))
    db.session.execute(delete(HealthRecord).where(HealthRecord.animal_id.in_(ids)))
    db.session.execute(delete(Livestock).where(Livestock.animal_id.in_(ids)))
    db.session.commit()
    return len(ids)
