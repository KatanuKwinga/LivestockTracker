# Handoff notes (from the Claude Cowork sessions, 17–28 Sep 2026)

Everything decided and built so far, what's unverified, and what's still open.
`CLAUDE.md` has the short version; this is the detail.

## 1. Timeline of what was built

| Date | Work | Status |
|---|---|---|
| 17 Sep | Project plan; Flask scaffold; all 10 models; Aiven MySQL provisioned; `flask db upgrade` created the tables on Aiven | Done, running on Vilo's machine |
| ~20 Sep | Week 2 auth: farmer registration, login/logout, farmer-created worker accounts, RBAC, bcrypt; `tests/test_auth.py`, `tests/test_models_load.py`, `tests/conftest.py` | Done; Vilo committed + pushed these himself |
| 24 Sep | Fix: duplicate-email race on register / new worker now caught via `IntegrityError` | Built |
| 26 Sep | Password reset by email (Flask-Mail + Gmail SMTP, itsdangerous tokens); `tests/test_password_reset.py` | Built, **tests never run** (see §4) |
| 28 Sep | ML pipeline (`ml/`), farmer `/predictions` page; `tests/test_ml.py` | Built; core ML tests pass, **route tests never run** |

Files for 26 Sep and 28 Sep were delivered to Vilo as zips to copy in by hand, because the Cowork
sandbox couldn't push to GitHub. Before continuing, confirm his local repo actually contains
`ml/`, `app/templates/predictions.html` and `tests/test_password_reset.py`.

## 2. Environment facts

- Repo: `https://github.com/KatanuKwinga/LivestockTracker` (branch `main`).
- Local path (Windows, OneDrive): `C:/Users/KAT/OneDrive/Documents/My Livestock Tracker/livestock-tracker`.
- Shell: Git Bash. Use `python -m pip`, not `pip`. CRLF warnings are harmless.
- Database: Aiven MySQL 8.4, service `mysql-livestocktracker`, database `defaultdb`, port 17717,
  user `avnadmin`. Full URL is in `.env` as `DATABASE_URL` (`mysql+pymysql://...`).
  Aiven is on a **free trial with ~$50 credits** (seen 26 Sep: 23 days left). Watch expiry before the
  31 Oct deadline; migrate to a free plan or another host if needed.
- DB viewer: HeidiSQL (connect with the same host/port/user/password).
- `.env` must contain: `SECRET_KEY`, `DATABASE_URL`, and for password reset
  `MAIL_USERNAME`, `MAIL_PASSWORD` (a Gmail **app password**), `MAIL_DEFAULT_SENDER`.
  Vilo hadn't set up the Gmail app password yet as of 28 Sep. See `.env.example`.

## 3. Key design decisions (and why)

**Accounts / auth**
- Workers can't self-register. Only a logged-in farmer creates them, hard-linked to that farm.
- Farmer and Worker are separate tables that both link 1:1 to `users`. Flask-Login ids are
  prefixed (`farmer:3`, `worker:7`) so ids from the two tables never collide.
- Login and reset messages are deliberately vague to prevent account enumeration.
- Password reset tokens are stateless (itsdangerous, salt `password-reset`, 30-min max_age), so
  there's no tokens table. Side effect: a token stays valid until it expires even after it's used.
  If that matters for the report's security section, add a password-hash fingerprint to the
  payload so tokens die when the password changes.

**Schema deviations from the submitted diagrams** (all intentional; mention them in the report)
- `age` isn't stored; it's computed from `date_of_birth`.
- `mortality_records` table name (the diagram says `mortalty_record`).
- `yield` column is exposed in Python as `yield_amount`.
- In the diagram, `workers.farmer_id` is `VARCHAR(150) UNIQUE` and `farmers.user_id` is
  `VARCHAR(100)`. The code uses INT foreign keys, and `workers.farmer_id` is *not* unique
  (a farmer can have many workers). The diagram is wrong here.
- Class diagram has `Dashboard`, `Prediction` and `Warning` classes with ids and timestamps.
  These are **not** database tables: predictions are computed live on page load. See open item O3.

**ML**
- Target: will an animal have a **new** illness recorded in the next **14 days**? This is binary
  classification. The brief says "simple regression model", and the sequence diagram says
  "Scikit-learn Regression Model". Logistic regression is one of the three candidates, but a
  random forest classifier won. Vilo should word this carefully in the report, or ask his
  supervisor whether a classifier is acceptable. See O4.
- 14 vs 30 days: on synthetic data, test ROC-AUC was 0.83 at 14 days, 0.77 at 21 and 0.71 at 30.
  An illness 3–4 weeks out usually hasn't changed weight yet: only 39% of 30-day positives showed
  any weight dip at prediction time. `--horizon` keeps 30 available.
- Features (`ml/features.py`): species, gender, age_days, weight change 14d/30d %, 30-day weight
  slope, **weight vs. the animal's own growth trend** (catches "stopped gaining" in young
  animals), days since last weigh-in, weigh-ins in 90d, illnesses in 90/365d, days since last
  illness (capped at 730), vaccinated in 180d, rainy season (Mar–May, Oct–Dec).
  Every feature uses only records dated ≤ the snapshot date; a test enforces this (no leakage).
- Method (`ml/train.py`): split by animal 80/20 (GroupShuffleSplit); an inner split compares
  logistic regression, random forest and HistGradientBoosting on validation ROC-AUC; the alert
  threshold is chosen by max F1 on validation; one evaluation on held-out test animals; the final
  model is refit on all data and saved to `ml/artifacts/sickness_model.joblib` plus
  `sickness_model_metrics.json`.
- Result on synthetic data (300 animals, 14-day horizon): random forest, test ROC-AUC ≈ 0.83,
  PR-AUC ≈ 0.38, base rate ≈ 5%. These numbers come from **simulated** data. They prove the
  pipeline works, not real-world accuracy.
- Risk bands on `/predictions`: High ≥ threshold, Medium ≥ threshold/2, Low below that, and
  "Under treatment" if an illness was recorded in the last 10 days. "Key signals" are rule-based
  plain-language flags, not model explanations.
- Synthetic data (`ml/synthetic.py`) simulates growth curves, frailty, age/season/vaccination
  effects, and a pre-illness weight dip starting 18 days before detection. All of these are
  documented assumptions. Seeded animals are tagged `[synthetic]` and removable. The data ends
  "today", so re-seed before a demo held weeks later.
- The `.joblib` model is gitignored and must be trained on each machine (`python -m ml.train`),
  because pickles don't transfer across scikit-learn versions.

## 4. Verification status (updated 28 Sep, Claude Code)

Done:
- Full suite passes (23 tests) on Python 3.11 with the `>=` pins. First real run of
  `tests/test_password_reset.py` and the 3 ML route tests found two test-side problems, now fixed:
  `TestConfig` had no `MAIL_DEFAULT_SENDER` (Flask-Mail refused to send), and the expiry test used
  `max_age=0`, which never expires a same-second token (itsdangerous rejects only `age > max_age`).
  The expiry test now advances the clock 31 minutes; the tampered-token check now edits the first
  signature character (editing the last one sometimes still verified: base64 padding bits).
- `python -m ml.seed`, `python -m ml.train` and `/predictions` run end to end (on SQLite).
- `flask db check`: models match the initial migration, so no new migration is needed.
- Password-reset, ML and docs work committed on branch `claude/trusting-cerf-19j3g9`; needs
  a pull request into `main`.

Still to do on Vilo's machine:
1. `python -m pip install -r requirements.txt` and `python -m pytest -v` in his venv.
2. Real password reset in the browser once the Gmail app password is in `.env`.
3. `python -m ml.seed ...` against Aiven, then `python -m ml.train`, then open `/predictions`.

## 5. Open items / decisions for Vilo

- **O1 — Email verification.** The use-case diagram shows "Register Account «include» Verify
  email". It isn't built. Could reuse the itsdangerous token pattern from password reset.
- **O2 — Bootstrap 5 / Chart.js.** The brief lists both; the UI currently uses plain CSS. Chart.js
  is needed for the Week 4 dashboard. Decide whether to adopt Bootstrap now (a cheap restyle
  before more pages exist) or keep the custom CSS.
- **O3 — Persist predictions/warnings?** The class diagram implies stored Prediction/Warning
  records. They're currently computed live. Storing them would enable history and warning
  "resolve" (from the class diagram) but needs new tables and a migration.
- **O4 — "Regression" wording.** See ML decisions above.
- **O5 — Password-reset token reuse.** See the auth decisions above.
- **O6 — Aiven trial expiry** before 31 Oct.
- **O7 — Login rate limiting** is planned for Week 6 (e.g. Flask-Limiter).
- **O8 — Mortality/sale should end predictions.** Dead animals are already excluded
  (`load_frames(include_dead=False)`). Sold animals (`commercial_info` SELL) aren't yet excluded.

## 6. Where the Week 3 data-entry forms touch the ML

- Health form: an illness = `disease` filled in. Vaccination = `disease` empty and `treatment`
  containing "vaccin". Consider a dropdown record type (Illness / Vaccination / Treatment)
  that sets these consistently, or add an explicit `record_type` column and update
  `ml/features.py` + `ml/synthetic.py` together.
- Weight entry is the most valuable input for predictions; make it quick to log for many
  animals (e.g. a batch weigh-in screen).
