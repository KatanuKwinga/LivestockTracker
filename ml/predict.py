"""Score animals with the saved sickness-risk model.

Two layers:
  score_frames(...)       pure pandas in / pandas out, no Flask needed
                          (easy to test, reusable from notebooks)
  predict_for_farmer(...) loads one farmer's herd from the DB and scores
                          it — this is what the /predictions page calls

RISK BANDS. The model outputs a probability. Training picked an "alert
threshold" (the cut-off that best balanced catching sick animals vs.
false alarms on validation data). We translate:
    High    probability >= threshold
    Medium  probability >= threshold / 2
    Low     below that
Animals with an illness recorded in the last 10 days are shown as
"Under treatment" instead — the model predicts NEW illness, and the
farmer already knows about the current one.

"KEY SIGNALS" are plain-language flags computed from the same features
(e.g. "Weight 6% below its growth trend"). They tell the farmer what in
the records looks concerning; they are rule-based summaries, not a
readout of the model's internal reasoning.
"""

from pathlib import Path

import joblib
import pandas as pd

from ml.features import FEATURE_COLUMNS, build_current_features
from ml.synthetic import SPECIES_CONFIG

_model_cache = {}


class ModelNotTrainedError(RuntimeError):
    pass


def load_model(model_path):
    """Load the artifact saved by ml/train.py, cached in memory and
    reloaded automatically if the file changes (e.g. after retraining)."""
    path = Path(model_path)
    if not path.exists():
        raise ModelNotTrainedError(f"No trained model at {path}. Run: python -m ml.train")
    mtime = path.stat().st_mtime
    cached = _model_cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    artifact = joblib.load(path)
    _model_cache[str(path)] = (mtime, artifact)
    return artifact


def _signals(row):
    signals = []
    if pd.notna(row.weight_vs_trend_pct) and row.weight_vs_trend_pct <= -3:
        signals.append(f"Weight {abs(row.weight_vs_trend_pct):.0f}% below its growth trend")
    if pd.notna(row.weight_change_14d_pct) and row.weight_change_14d_pct <= -3:
        signals.append(f"Lost {abs(row.weight_change_14d_pct):.0f}% of body weight in 2 weeks")
    if row.illnesses_90d >= 1:
        n = int(row.illnesses_90d)
        signals.append(f"Sick {n} time{'s' if n > 1 else ''} in the last 90 days")
    if not row.vaccinated_180d:
        signals.append("No vaccination recorded in 6 months")
    maturity = SPECIES_CONFIG.get(row.species, {}).get("maturity_days")
    if maturity and pd.notna(row.age_days) and row.age_days < 0.15 * maturity:
        signals.append("Very young animal (weaker immunity)")
    if row.rainy_season:
        signals.append("Rainy season: higher disease pressure")
    if pd.isna(row.days_since_last_weight):
        signals.append("No weigh-ins recorded; prediction is unreliable")
    elif row.days_since_last_weight > 30:
        signals.append(f"Last weigh-in {int(row.days_since_last_weight)} days ago; prediction less reliable")
    return signals


def _band(probability, threshold, currently_sick):
    if currently_sick:
        return "Under treatment"
    if probability >= threshold:
        return "High"
    if probability >= threshold / 2:
        return "Medium"
    return "Low"


def score_frames(artifact, livestock, weights, health, as_of=None):
    """Return one row per animal: probability, band, signals, sorted with
    the most at-risk first."""
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    if livestock.empty:
        return pd.DataFrame()

    features = build_current_features(livestock, weights, health, as_of)
    proba = artifact["pipeline"].predict_proba(features[FEATURE_COLUMNS])[:, 1]
    threshold = artifact["threshold"]

    result = features.copy()
    result["probability"] = proba
    result["risk_band"] = [
        _band(p, threshold, sick) for p, sick in zip(proba, features["currently_sick"])
    ]
    result["signals"] = [_signals(r) for r in features.itertuples(index=False)]
    result = result.merge(livestock[["animal_id", "breed"]], on="animal_id", how="left")

    band_order = {"High": 0, "Medium": 1, "Under treatment": 2, "Low": 3}
    result["_order"] = result["risk_band"].map(band_order)
    return result.sort_values(["_order", "probability"], ascending=[True, False]).drop(columns="_order")


def predict_for_farmer(farmer_id, model_path, as_of=None):
    """Score every living animal on one farm. Needs a Flask app context."""
    from ml.data import load_frames  # imported here so this module works without Flask

    artifact = load_model(model_path)
    frames = load_frames(farmer_id=farmer_id)
    return score_frames(artifact, frames["livestock"], frames["weights"], frames["health"], as_of), artifact
