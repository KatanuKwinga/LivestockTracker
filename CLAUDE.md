# CLAUDE.md — Livestock Data Tracking and Analytics System

Read this first, then `docs/HANDOFF.md` for full history and open items.

## What this is

Vilo's 4th-year university final project (Strathmore University, Kenya): a web app where a
**farmer** stores and tracks livestock data (cattle, chicken, goat, sheep) and gets analytics
and ML predictions to support decisions. **Workers** (created by the farmer) do data entry.
Full requirements: `docs/PROJECT_DESCRIPTION.md`. Schedule: `docs/PROJECT_PLAN.md`.

**Hard deadline: 31 October 2026.** Built week by week (see plan). Today's position: Weeks 1-2
done, ML (Week 5) pulled forward and built; **Week 3 (worker data-entry module) is next.**

## How Vilo wants to work (important)

- Go **step by step**. Each step ends with something that runs and is tested.
- **Explain what the code does and why** — Vilo is learning and must defend this project in a
  report/presentation. Comments in code explain *why*, not just *what*. Keep that style.
- **Incremental testing**: add/extend pytest tests with every feature; run them.
- Non-functional requirements matter: security (hashed passwords, CSRF, RBAC, no secrets in
  git), ease of use, reliability, clean UI/UX.
- Resolve bugs as they come up; don't leave known-broken code.
- Vilo is on **Windows, using Git Bash**, project inside OneDrive:
  `C:/Users/KAT/OneDrive/Documents/My Livestock Tracker/livestock-tracker`, venv at `venv/`.
  - Use `python -m pip install ...` — calling `pip` directly gave "Permission denied" in Git Bash.
  - Git warns "LF will be replaced by CRLF" — harmless, ignore.
- Database GUI: **HeidiSQL** works (MySQL Workbench froze). Aiven's console only lists databases.

## Stack

Flask 3 (app factory + blueprints), Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-Login,
Flask-Bcrypt, Flask-WTF (CSRF + validation), Flask-Mail, **MySQL on Aiven (cloud)** via PyMySQL,
Jinja2 templates + plain CSS (Bootstrap 5 and Chart.js are planned per the brief, not yet used),
pandas / NumPy / scikit-learn / joblib for ML, pytest.

The brief requires the database **not** be local — production data lives in Aiven MySQL
(`defaultdb`). Tests use in-memory SQLite.

## Commands

```bash
source venv/Scripts/activate                  # Git Bash on Windows
python -m pip install -r requirements.txt
python run.py                                 # dev server, http://localhost:5000
flask db migrate -m "msg" && flask db upgrade # after ANY model change
pytest -v                                     # all tests (SQLite, no network needed)
pytest tests/test_ml.py -v                    # one file

python -m ml.seed --farmer-email demo@x.com            # load synthetic animals into the DB
python -m ml.seed --farmer-email demo@x.com --remove   # delete them again
python -m ml.train                                     # train on DB data
python -m ml.train --source synthetic                  # train without the DB
python -m ml.train --horizon 30                        # predict 30 days ahead instead of 14
```

## Layout

```
app/__init__.py        create_app(config_class) — tests pass TestConfig here
app/config.py          Config: all secrets from .env; MAIL_*; ML_MODEL_PATH
app/extensions.py      db, migrate, login_manager, bcrypt, mail singletons
app/forms.py           WTForms: registration, worker creation, login, password reset
app/models/            one file per table (user.py holds User/Farmer/Worker + user_loader)
app/routes/auth.py     register, login, logout, workers/new, reset-password (+ /<token>)
app/routes/main.py     dashboard, /predictions (farmer only)
app/templates/         base.html, dashboard.html, predictions.html, auth/*.html
app/static/css/style.css
ml/                    synthetic.py, features.py, train.py, predict.py, data.py, seed.py
ml/artifacts/          trained model (*.joblib is gitignored; *_metrics.json is not)
tests/conftest.py      TestConfig (SQLite, CSRF off, MAIL_SUPPRESS_SEND) + app/client fixtures
docs/                  requirements, plan, design summary, handoff notes
```

## Architecture rules and conventions

- **Accounts:** `users` holds identity (name, email, password_hash, phone). A user is exactly one
  of `Farmer` or `Worker` (1:1 tables). Flask-Login logs in the *Farmer/Worker* object;
  `get_id()` returns `"farmer:<id>"` / `"worker:<id>"` and `load_user` in `models/user.py` parses
  the prefix. `current_user.name` / `.email` are properties proxied from `User`.
- **RBAC pattern:** `if not isinstance(current_user, Farmer): flash(...); redirect(...)`.
  Farmers: analytics, predictions, create workers. Workers: data entry, view/search records.
  Workers never self-register; a worker is always tied to `current_user.farmer_id`.
- **Data scoping:** every query for livestock/records must be filtered to the logged-in
  farmer's farm (`Livestock.farmer_id == <farmer_id>`; for a worker use `current_user.farmer_id`).
  Never trust an animal_id from the URL/form without checking it belongs to that farm.
- **Security:** bcrypt hashes only; generic "Invalid email or password"; password reset shows the
  same message whether or not the email exists (no account enumeration); reset tokens are
  itsdangerous-signed, 30-min expiry, no DB table. Catch `IntegrityError` on inserts that can
  race a UNIQUE constraint. Never commit `.env`.
- **Schema quirks (keep them):** `Livestock.age` is a computed property (not a column);
  `ProductionData.yield_amount` maps to DB column `yield` (Python keyword);
  `livestock.b_record_id` ↔ `breeding_record` is a circular FK handled with `use_alter=True`;
  mortality table is `mortality_records` (the ERD's "mortalty_record" typo was fixed).
- **Tests:** always build the app via the `app`/`client` fixtures (`create_app(TestConfig)`);
  never override the DB URI after `create_app()` — the engine is already bound by then.
- **Templates:** extend `base.html`; forms render `form.hidden_tag()` for CSRF; show field
  errors in `<ul class="errors">`. CSS tokens live in `:root` in `style.css`.
- **ML** (details in `docs/HANDOFF.md`): predicts "new illness within 14 days". An illness is a
  `health_records` row with `disease` filled; a vaccination is a row with no disease and
  "vaccin" in `treatment` — Week 3 health forms must preserve that convention or update
  `ml/features.py`. Synthetic animals have `description` starting with `[synthetic]`.

## Verification status

All 23 tests pass (password reset and ML route tests included), and seed → train → `/predictions`
has been run end to end. Still to check on Vilo's own machine: `pytest -v` in his venv, a real
reset email once the Gmail app password is in `.env`, and seeding/training against Aiven.
See `docs/HANDOFF.md` §4.

## Next up: Week 3 — worker data-entry module

Worker flow from the brief: choose species → choose category (general, commercial, health,
breeding, production, mortality) → register a new animal or update an existing one.
Plus a table view of records with search/filter. Forms + server-side validation for all six
categories, all scoped to the worker's farm, with tests. See `docs/PROJECT_PLAN.md` and the
open items in `docs/HANDOFF.md` (e.g. email verification appears in the use-case diagram but
isn't built).
