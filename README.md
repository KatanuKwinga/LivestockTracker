# Livestock Data Tracking and Analytics System

A web-based system for tracking livestock (cattle, chicken, goat, sheep) across general,
health, breeding, production, commercial and mortality data, with a farmer-facing analytics
dashboard and a machine-learning model that flags animals at risk of falling sick.

**Stack:** Flask, SQLAlchemy, MySQL (Aiven cloud), scikit-learn / pandas / NumPy, pytest.
Chart.js and Bootstrap 5 are planned for the dashboard.

Working on this with Claude Code? Start with `CLAUDE.md`, then `docs/HANDOFF.md`.

## Project status

- [x] Week 1: scaffold, cloud database, all 10 tables
- [x] Week 2: authentication (farmer/worker accounts, RBAC, password reset by email)
- [x] ML pipeline + farmer predictions page (Week 5 work, done early)
- [ ] Week 3: worker data-entry module
- [ ] Week 4: analytics dashboard (Chart.js)
- [ ] Week 5: retrain on real data, predictions on dashboard, write-up
- [ ] Week 6: testing, security hardening, polish

Details: `docs/PROJECT_PLAN.md`.

## Local setup (Windows / Git Bash)

```bash
python -m venv venv
source venv/Scripts/activate          # macOS/Linux: source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env                  # then fill in SECRET_KEY, DATABASE_URL, MAIL_* values
```

`DATABASE_URL` points at the Aiven MySQL database (the brief requires a non-local database),
e.g. `mysql+pymysql://avnadmin:<password>@<host>:17717/defaultdb`.

```bash
flask db upgrade        # create/update tables
pytest -v               # all tests run on in-memory SQLite, no network needed
python run.py           # http://localhost:5000
```

## Machine learning

```bash
python -m ml.seed --farmer-email demo@example.com   # load a year of simulated animals
python -m ml.train                                  # train + evaluate + save the model
```

Then log in as that farmer and open **Health risk predictions**. See `ml/__init__.py` for how
the pipeline fits together and `docs/HANDOFF.md` §3 for the method and results.

## Project structure

```
app/            Flask app: config, models (one file per table), routes, forms, templates, CSS
ml/             synthetic data, feature engineering, training, prediction, DB seeding
tests/          pytest suite (conftest.py builds the app against SQLite)
docs/           requirements, plan, design summary, handoff notes
run.py          entry point
```

## Notes on the schema

- `livestock.b_record_id` and `breeding_record.animal_id` / `sire_id` form a circular foreign
  key, handled with `use_alter=True`. If a migration ever fails on that constraint, look there
  first.
- `age` on `Livestock` is computed from `date_of_birth`, not stored, so it can't go stale.
- `yield` is a Python keyword, so the column stays `yield` in the database but the Python
  attribute is `yield_amount`.
