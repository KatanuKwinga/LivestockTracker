# Project plan & schedule

**Start:** 17 Sep 2026 · **Deadline:** 31 Oct 2026 (6 weeks + 3-day buffer)
**Method:** OOAD + prototyping, with unit/integration/system/UAT testing throughout.
Each week ends with something that runs and is tested, not just a document.

## Progress (as of 28 Sep)

- **Week 1: done.** Flask scaffold, Aiven MySQL, all 10 tables migrated.
- **Week 2: done; tests pass.** Farmer signup/login, farmer-created workers,
  RBAC, bcrypt, duplicate-email race handling, password reset by email.
- **Week 5 ML: core built early.** Sickness-risk model + farmer `/predictions` page (see
  `HANDOFF.md` §3).
- **Next: Week 3.**

## Weekly schedule

### Week 1 (Sep 17–23): environment, schema, skeleton ✅
Cloud MySQL (Aiven), final schema, Flask app factory, SQLAlchemy, Flask-Migrate, Flask-Login,
base template, core tables. Deliverable: app boots and `flask db upgrade` creates all tables.

### Week 2 (Sep 24–30): authentication & accounts ✅
Farmer signup/login (root account); worker creation by the farmer only; role-based access control;
bcrypt; sessions; password reset via email. Deliverable: working auth + unit tests.

### Week 3 (Oct 1–7): data entry module (worker side) ⏭ NEXT
Worker flow: select livestock type → select category (general / commercial / health / breeding /
production / mortality) → new record or update existing. Forms + validation for all 6 categories
across the 4 species. Table view of entered data; search/filter by animal. Deliverable: a worker
can create, view, search and update every record type end to end.

### Week 4 (Oct 8–14): analytics dashboard (farmer side)
Aggregations (means, percentages, trends, comparisons across animals/categories); Chart.js
visualisations; warnings/flags (e.g. abnormal weight loss, high mortality in a category).
Deliverable: farmer dashboard with live charts and summary stats from real data.

### Week 5 (Oct 15–21): predictive analytics (ML)
Pipeline already built (synthetic data, features, model comparison, predictions page). Remaining:
retrain on entered data, compare with synthetic results, fold predictions/warnings into the
Week 4 dashboard, write up method and metrics for the report.

### Week 6 (Oct 22–28): testing, security hardening, polish
Unit + integration + system tests across all modules; bug fixes; UAT (Vilo as farmer/worker on
real scenarios); input validation, injection-safe queries (SQLAlchemy), HTTPS notes, login
rate-limiting, UI/UX consistency pass. Deliverable: stable, tested system ready for write-up.

### Oct 29–31: buffer
Optional deployment (a local demo against the Aiven DB also meets the brief), documentation,
screenshots/report material, contingency.

## Working agreement

At the start of each step, deliver the concrete code plus an explanation of what each piece does
and why. Vilo runs it, tests it and reports what broke or should change before moving on.
Nothing counts as "done" until it runs on his machine.
