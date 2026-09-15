# Livestock Data Tracking and Analytics System

A web-based system for tracking livestock (cattle, chicken, goat, sheep) across
general, health, breeding, production, commercial, and mortality data — with a
farmer-facing analytics dashboard including a trained regression model for
disease risk prediction.

**Stack:** Flask, SQLAlchemy, MySQL, Chart.js, scikit-learn/Pandas/NumPy.

## Project status

- [x] Step 1 — Repo + scaffold + database models
- [ ] Step 2 — Auth
- [ ] Step 3 — Worker flows
- [ ] Step 4 — Farmer flows
- [ ] Step 5 — Analytics engine
- [ ] Step 6 — ML pipeline
- [ ] Step 7 — Predictions + warnings on dashboard
- [ ] Step 8 — Testing + polish

## Local setup

### 1. Prerequisites

- Python 3.11+
- MySQL running locally (XAMPP is fine — start Apache + MySQL from the control panel)

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up the database

In phpMyAdmin (or the MySQL CLI), create an empty database:

```sql
CREATE DATABASE livestock_tracker;
```

Copy the environment file and adjust if your MySQL credentials differ from
XAMPP's defaults:

```bash
cp .env.example .env
```

### 4. Verify the models before anything else

```bash
pytest tests/test_models_load.py -v
```

This runs against an in-memory SQLite database, not your real MySQL — it's
just checking that every model imports and every table can be created. If
this fails, nothing past this point will work, so fix it here first.

### 5. Create the real tables in MySQL

```bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

Open phpMyAdmin and confirm all 10 tables appeared under `livestock_tracker`.

### 6. Run the app

```bash
python run.py
```

Visit `http://localhost:5000/health` — you should see `{"status": "ok"}`.
That route is a temporary placeholder; it'll be replaced by the real login
page in Step 2.

## Project structure

```
app/
  __init__.py          app factory
  config.py            reads .env
  extensions.py         shared db/migrate/login_manager/bcrypt instances
  models/               one file per table, matches Database_schema.drawio
  routes/                blueprints (empty for now — built step by step)
  templates/             Jinja2 templates
  static/                CSS/JS
ml/                      training scripts + saved model artifacts (Step 6)
tests/
run.py                   entry point
```

## Notes on the schema

- `livestock.b_record_id` and `breeding_record.animal_id`/`sire_id` form a
  **circular foreign key** between the two tables (a livestock row points to
  the breeding event it was born from; a breeding event points to the dam and
  sire livestock rows). This is handled with `use_alter=True` on the
  `b_record_id` column — Alembic creates both tables first, then adds that
  specific constraint as a separate `ALTER TABLE` step. If a future migration
  ever fails specifically on this constraint, that's the first place to look.
- `age` on `Livestock` is **not** a stored column in code, even though it's
  drawn that way in the ERD — it's computed live from `date_of_birth` via a
  Python property, so it can never silently go stale.
- `yield` on `ProductionData` is a reserved Python keyword, so the database
  column is still named `yield` (matching your diagram) but the Python
  attribute is `yield_amount`.
