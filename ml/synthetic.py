"""Synthetic livestock data generator.

WHY THIS EXISTS
---------------
The database is empty until farmers start entering records (Week 3), but
the ML pipeline needs data to be built and tested now. This module
simulates a year of farm records — animals, periodic weigh-ins,
vaccinations and illness episodes — in exactly the shape of our real
tables, so the same feature/training code runs unchanged on real data
later.

HOW THE SIMULATION WORKS (and why the model has something real to learn)
-----------------------------------------------------------------------
Each animal gets:
  * a growth curve toward its species' adult weight (von Bertalanffy-style
    curve: fast growth when young, levelling off at maturity), plus
    small random measurement noise;
  * a hidden "frailty" score — some animals are simply more
    illness-prone, as on a real farm;
  * a daily chance of falling ill that goes UP for very young or old
    animals, in Kenya's rainy seasons (Mar-May, Oct-Dec), and after a
    recent illness, and goes DOWN if vaccinated in the last 6 months.

Crucially, when an illness is coming, the animal's weight starts slipping
about 2-3 weeks BEFORE the illness is detected and recorded (the
"subclinical" phase — reduced feed intake before visible symptoms). That
early weight loss is the main warning sign the model can learn to spot.
Real animals behave this way too, which is why weight monitoring is a
sensible basis for an early-warning model.

Every rule above is a documented assumption, not measured truth — the
report should present results on synthetic data as a proof that the
pipeline works end to end, with retraining on real farm data as the next
step.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

# Per-species settings. Weights in kg; maturity_days is roughly when an
# animal reaches ~90% of adult weight; base_hazard is the baseline daily
# probability of a new illness starting.
SPECIES_CONFIG = {
    "CATTLE": {
        "breeds": ["Friesian", "Ayrshire", "Boran", "Sahiwal", "Jersey"],
        "birth_weight": 35.0, "adult_weight": 450.0, "maturity_days": 900,
        "max_age_days": 8 * 365, "weigh_every_days": 14, "base_hazard": 0.0022,
        "pre_illness_drop": 0.08,
        "diseases": ["East Coast Fever", "Foot and Mouth Disease", "Mastitis", "Anaplasmosis", "Lumpy Skin Disease"],
        "treatments": ["Buparvaquone injection", "Oxytetracycline", "Intramammary antibiotic", "Imidocarb", "Supportive care"],
        "vaccines": ["ECF vaccine", "FMD vaccine", "Lumpy Skin vaccine"],
    },
    "GOAT": {
        "breeds": ["Galla", "Toggenburg", "Saanen", "Small East African"],
        "birth_weight": 3.0, "adult_weight": 45.0, "maturity_days": 365,
        "max_age_days": 6 * 365, "weigh_every_days": 14, "base_hazard": 0.0028,
        "pre_illness_drop": 0.09,
        "diseases": ["PPR", "CCPP", "Pneumonia", "Worm infestation"],
        "treatments": ["Supportive care", "Tylosin", "Oxytetracycline", "Albendazole drench"],
        "vaccines": ["PPR vaccine", "CCPP vaccine"],
    },
    "SHEEP": {
        "breeds": ["Dorper", "Red Maasai", "Merino"],
        "birth_weight": 3.5, "adult_weight": 55.0, "maturity_days": 365,
        "max_age_days": 6 * 365, "weigh_every_days": 14, "base_hazard": 0.0028,
        "pre_illness_drop": 0.09,
        "diseases": ["Foot rot", "Pneumonia", "Worm infestation", "Sheep pox"],
        "treatments": ["Foot bath + Oxytetracycline", "Tylosin", "Albendazole drench", "Supportive care"],
        "vaccines": ["Sheep pox vaccine", "Enterotoxaemia vaccine"],
    },
    "CHICKEN": {
        "breeds": ["Kienyeji", "Kuroiler", "Kenbro", "Broiler"],
        "birth_weight": 0.04, "adult_weight": 2.5, "maturity_days": 150,
        "max_age_days": 2 * 365, "weigh_every_days": 7, "base_hazard": 0.0035,
        "pre_illness_drop": 0.12,
        "diseases": ["Newcastle Disease", "Gumboro", "Coccidiosis", "Fowl Typhoid"],
        "treatments": ["Supportive care + vitamins", "Supportive care", "Amprolium", "Enrofloxacin"],
        "vaccines": ["Newcastle vaccine", "Gumboro vaccine"],
    },
}

RAINY_MONTHS = {3, 4, 5, 10, 11, 12}  # Kenya's long and short rains

PRE_ILLNESS_DAYS = 18   # weight starts slipping this many days before detection
SICK_DAYS = 10          # animal stays at reduced weight while being treated
RECOVERY_DAYS = 30      # then regains weight over this many days
REFRACTORY_DAYS = 21    # no new illness can start this soon after the last


def _expected_weight(cfg, age_days):
    """Growth curve: starts at birth weight, rises toward adult weight,
    reaching ~90% of it at maturity_days."""
    k = np.log(10) / cfg["maturity_days"]
    return cfg["adult_weight"] - (cfg["adult_weight"] - cfg["birth_weight"]) * np.exp(-k * age_days)


def _illness_weight_factor(days_from_onset, drop):
    """Multiplier on normal weight around an illness that starts
    (is detected) at day 0. Negative days = before detection."""
    d = days_from_onset
    if -PRE_ILLNESS_DAYS <= d < 0:
        return 1.0 - drop * (d + PRE_ILLNESS_DAYS) / PRE_ILLNESS_DAYS
    if 0 <= d <= SICK_DAYS:
        return 1.0 - drop
    if SICK_DAYS < d <= SICK_DAYS + RECOVERY_DAYS:
        return 1.0 - drop * (1 - (d - SICK_DAYS) / RECOVERY_DAYS)
    return 1.0


def generate_synthetic_data(n_animals=300, history_days=365, end_date=None, seed=42):
    """Simulate `history_days` of records ending at `end_date` (default:
    today) for `n_animals` animals.

    Returns a dict of three DataFrames shaped like our tables:
      livestock: animal_id, species, gender, breed, date_of_birth
      weights:   animal_id, date, weight
      health:    animal_id, date, disease, description, treatment, dosage
    animal_id here is a temporary id; seeding into the DB assigns real ones.
    """
    rng = np.random.default_rng(seed)
    end_date = end_date or date.today()
    start_date = end_date - timedelta(days=history_days)

    species_names = list(SPECIES_CONFIG)
    species_probs = [0.35, 0.25, 0.15, 0.25]  # CATTLE, GOAT, SHEEP, CHICKEN

    livestock_rows, weight_rows, health_rows = [], [], []

    for animal_id in range(1, n_animals + 1):
        species = rng.choice(species_names, p=species_probs)
        cfg = SPECIES_CONFIG[species]

        # Age at end_date: at least 60 days old, so every animal has some
        # history to learn from.
        age_at_end = int(rng.integers(60, cfg["max_age_days"]))
        dob = end_date - timedelta(days=age_at_end)
        sim_start = max(start_date, dob)

        livestock_rows.append({
            "animal_id": animal_id,
            "species": species,
            "gender": rng.choice(["MALE", "FEMALE"], p=[0.35, 0.65]),
            "breed": rng.choice(cfg["breeds"]),
            "date_of_birth": dob,
        })

        frailty = rng.lognormal(mean=0.0, sigma=0.5)
        size_factor = rng.normal(1.0, 0.07)  # some animals are just bigger

        # --- Pass 1: day-by-day illness simulation ------------------------
        onsets, vaccine_dates = [], []
        last_vaccine = None
        # Start from a random point in a 6-month vaccination cycle so not
        # every animal is vaccinated on the same day.
        next_vaccine_check = sim_start + timedelta(days=int(rng.integers(0, 180)))

        n_days = (end_date - sim_start).days
        for offset in range(n_days + 1):
            day = sim_start + timedelta(days=offset)

            if day >= next_vaccine_check:
                if rng.random() < 0.7:  # ~70% vaccination compliance
                    vaccine_dates.append(day)
                    last_vaccine = day
                next_vaccine_check = day + timedelta(days=180)

            if onsets and (day - onsets[-1]).days < REFRACTORY_DAYS:
                continue

            age = (day - dob).days
            if age < 0.15 * cfg["maturity_days"]:
                age_factor = 2.0          # very young: weaker immunity
            elif age > 0.75 * cfg["max_age_days"]:
                age_factor = 1.5          # old animals
            else:
                age_factor = 1.0

            recent_illness = any(0 < (day - o).days <= 90 for o in onsets)
            vaccinated = last_vaccine is not None and (day - last_vaccine).days <= 180

            hazard = (
                cfg["base_hazard"] * frailty * age_factor
                * (1.4 if day.month in RAINY_MONTHS else 1.0)
                * (1.8 if recent_illness else 1.0)
                * (0.55 if vaccinated else 1.0)
            )
            if rng.random() < hazard:
                onsets.append(day)

        # --- Pass 2: weigh-ins, reflecting growth + illness dips ----------
        interval = cfg["weigh_every_days"]
        day = sim_start + timedelta(days=int(rng.integers(0, interval)))
        while day <= end_date:
            if rng.random() > 0.08:  # ~8% of scheduled weigh-ins get missed
                age = (day - dob).days
                weight = _expected_weight(cfg, age) * size_factor
                for onset in onsets:
                    weight *= _illness_weight_factor((day - onset).days, cfg["pre_illness_drop"])
                weight *= rng.normal(1.0, 0.015)  # scale/measurement noise
                weight_rows.append({
                    "animal_id": animal_id,
                    "date": day,
                    "weight": round(float(weight), 3 if species == "CHICKEN" else 1),
                })
            day += timedelta(days=int(interval + rng.integers(-2, 3)))

        # --- Health records: illnesses + vaccinations ---------------------
        for onset in onsets:
            idx = int(rng.integers(0, len(cfg["diseases"])))
            health_rows.append({
                "animal_id": animal_id,
                "date": onset,
                "disease": cfg["diseases"][idx],
                "description": "Detected on routine inspection",
                "treatment": cfg["treatments"][idx],
                "dosage": "As per vet instructions",
            })
        for vdate in vaccine_dates:
            health_rows.append({
                "animal_id": animal_id,
                "date": vdate,
                "disease": None,  # no disease => routine/preventive record
                "description": "Routine vaccination",
                "treatment": rng.choice(cfg["vaccines"]),
                "dosage": "1 dose",
            })

    livestock = pd.DataFrame(livestock_rows)
    weights = pd.DataFrame(weight_rows)
    health = pd.DataFrame(health_rows, columns=["animal_id", "date", "disease", "description", "treatment", "dosage"])
    for df, col in [(livestock, "date_of_birth"), (weights, "date"), (health, "date")]:
        df[col] = pd.to_datetime(df[col])
    return {"livestock": livestock, "weights": weights, "health": health}
