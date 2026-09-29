# Design diagrams: text summary

Vilo's original diagrams are draw.io files in the claude.ai project (and on his machine):
`Use Case Diagram.drawio`, `ERD.drawio`, `ERD (2).drawio`, `Class Diagram (1).drawio`,
`Sequence Diagram.drawio`, `Database schema.drawio`. Drop copies into `docs/design/` if useful.
This file summarises what they specify so the code can be checked against them.

## Use case diagram

**Farmer:** Register Account («include» Verify email), Login («extend» Password reset), Create
worker account, Search/filter records, View analytics / summaries / insights / predictions /
visualisations / warnings, View livestock records, Log out.

**Worker:** Login, Select livestock type, Register new animal, Update existing records, Input new
livestock records, View livestock records, Log out.

Built so far: register, login, password reset, create worker, logout, view predictions.
**Not built:** verify email (see HANDOFF O1), all record viewing/search/entry (Week 3), analytics
and warnings (Week 4).

## Database schema diagram (what the code implements)

| Table | Columns (code) | Notes |
|---|---|---|
| users | id PK, name, email UNIQUE, password_hash, phone | |
| farmers | farmer_id PK, user_id FK→users UNIQUE | diagram shows user_id VARCHAR; code uses INT |
| workers | worker_id PK, user_id FK→users UNIQUE, farmer_id FK→farmers | diagram says farmer_id VARCHAR(150) UNIQUE; wrong, a farmer has many workers |
| livestock | animal_id PK, farmer_id FK, species ENUM(CATTLE,CHICKEN,GOAT,SHEEP), gender ENUM(MALE,FEMALE), breed, date_of_birth, description, b_record_id FK→breeding_record (birth event) | `age` computed, not stored |
| weight_records | w_record_id PK, animal_id FK, date, weight FLOAT | class diagram also lists `age`; not stored |
| health_records | h_record_id PK, animal_id FK, date, disease, description, treatment, dosage | illness vs vaccination convention: see HANDOFF §6 |
| breeding_record | b_record_id PK, animal_id FK (dam), sire_id FK, status ENUM(EXPECTANT, SUCCESSFUL BIRTH, NO BIRTH), expected_delivery_date, actual_delivery_date, num_stillborn | num_born_alive computed from offspring |
| mortality_records | m_record_id PK, animal_id FK UNIQUE, date_of_death, age_at_death, cause_of_death, description | diagram typo "mortalty_record" |
| commercial_info | transaction_id PK, animal_id FK, transaction_type ENUM(BUY,SELL), date, amount FLOAT, other_party, location | |
| production_data | product_id PK, animal_id FK, date, item, yield FLOAT (Python: yield_amount), metric VARCHAR(10) | |

Cardinalities: farmer 1–N workers; farmer 1–N livestock; livestock 0–N of weight / health /
commercial / production / breeding; livestock 0–1 mortality.

## Class diagram

- `User` (login, logout, changePassword, updateProfile) generalises `Farmer` (createWorker,
  viewAnalytics, viewPredictions, viewWarnings, manageAccount) and `Worker` (registerLivestock,
  selectLivestockType, updateLivestock, searchRecords, viewRecords).
- `Livestock` (addGeneralInfo, updateGeneralInfo, getRecords) is associated 1–0..* with
  HealthRecord, ProductionData, CommercialInfo, WeightRecords, BreedingRecord and 0..1 with
  MortalityRecord. Each record class has add/update/get methods.
- `Dashboard` (dashboard_id, farmer_id, generated_at; getAnalytics, getPredictions, getWarnings)
  uses 0..* `Prediction` (prediction_id, animal_id, predicted_value, confidence, generated_at) and
  0..* `Warning` (warning_id, farmer_id, animal_id, message, severity low/medium/high,
  created_at; resolve, getWarnings). These are currently computed live, not stored (HANDOFF O3).
  The predictions page's High/Medium/Low bands correspond to Warning.severity.

## Sequence diagram

1. User → Web UI: login → Flask controller → SQLAlchemy → MySQL: validate user → auth result →
   "login success".
2. Worker → UI: enter livestock data → Flask: submit → SQLAlchemy: validate → MySQL: save/update →
   success → "display success message".
3. Farmer → UI: request analytics/predictions → Flask: request analytics → SQLAlchemy/MySQL: fetch
   data → process data (Pandas, NumPy) → predict ("Scikit-learn Regression Model") → results →
   display dashboard.
