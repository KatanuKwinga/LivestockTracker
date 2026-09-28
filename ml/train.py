"""Train, evaluate and save the sickness-risk model (default: will this
animal fall sick within the next 14 days?).

Run from the project root (venv active):

    python -m ml.train                    # train on data in the database
    python -m ml.train --source synthetic # train on freshly generated data,
                                          # no database needed
    python -m ml.train --horizon 30       # predict 30 days ahead instead

THE METHOD (worth describing in the report)
-------------------------------------------
1. Split by ANIMAL, not by row: 80% of animals for training, 20% held back
   for the final test. Each animal contributes many snapshot rows; if the
   same animal appeared on both sides, the model could "recognise" it and
   the test score would be inflated. Grouped splitting prevents that.
2. Inside the training animals, split again (fit / validation) to compare
   three candidate models fairly:
     * Logistic Regression  — simple, interpretable baseline
     * Random Forest        — many decision trees voting
     * Gradient Boosting    — trees built to fix each other's mistakes
   The winner is the one with the best ROC-AUC on validation. The
   validation set also picks the alert threshold that best balances
   precision and recall (max F1).
3. Retrain the winner on all training animals and score it ONCE on the
   untouched test animals — the honest number to report.
4. Retrain on everything and save to ml/artifacts/ for the app to use.

WHY THESE METRICS: only a minority of snapshots are followed by illness,
so plain accuracy is misleading (always guessing "healthy" scores high).
ROC-AUC = how well the model ranks sick-soon animals above healthy ones
(0.5 = coin flip, 1.0 = perfect). Precision = of animals flagged, how many
really got sick. Recall = of animals that got sick, how many were flagged.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, HORIZON_DAYS, NUMERIC_FEATURES, build_training_set

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACT_DIR / "sickness_model.joblib"
RANDOM_STATE = 42


def make_candidates():
    """Each candidate is a full Pipeline: preprocessing + model, so the
    exact same transformations are applied at training and prediction."""
    def preprocess():
        return ColumnTransformer([
            # Fill gaps (e.g. no weigh-in yet) with the median, then put
            # numbers on a comparable scale.
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                              ("scale", StandardScaler())]), NUMERIC_FEATURES),
            # Turn species/gender text into 0/1 columns.
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ])

    return {
        "logistic_regression": Pipeline([
            ("prep", preprocess()),
            ("model", LogisticRegression(max_iter=2000)),
        ]),
        "random_forest": Pipeline([
            ("prep", preprocess()),
            ("model", RandomForestClassifier(
                n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=RANDOM_STATE)),
        ]),
        "gradient_boosting": Pipeline([
            ("prep", preprocess()),
            ("model", HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.05, max_leaf_nodes=15, random_state=RANDOM_STATE)),
        ]),
    }


def _group_split(frame, test_size, seed):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    a, b = next(splitter.split(frame, frame["label"], groups=frame["animal_id"]))
    return frame.iloc[a], frame.iloc[b]


def _best_f1_threshold(y_true, proba):
    precision, recall, thresholds = precision_recall_curve(y_true, proba)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-9, None)
    best = int(np.nanargmax(f1[:-1])) if len(thresholds) else 0
    return float(thresholds[best]) if len(thresholds) else 0.5


def _metrics(y_true, proba, threshold):
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_true, proba)), 4),
        "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "positive_rate": round(float(np.mean(y_true)), 4),
        "n_rows": int(len(y_true)),
    }


def train_from_frames(livestock, weights, health, model_path=DEFAULT_MODEL_PATH, data_source="unknown",
                      horizon_days=HORIZON_DAYS, verbose=True):
    """Full train/evaluate/save cycle from raw DataFrames. Returns the
    saved artifact dict (model + threshold + metrics)."""
    log = print if verbose else (lambda *a, **k: None)

    dataset = build_training_set(livestock, weights, health, horizon_days=horizon_days)
    if dataset.empty or dataset["label"].nunique() < 2:
        raise ValueError(
            "Not enough history to train: need animals with weigh-ins spanning 60+ days "
            "and at least some recorded illnesses. Seed synthetic data (python -m ml.seed) "
            "or use --source synthetic."
        )
    log(f"Built {len(dataset)} snapshots from {dataset['animal_id'].nunique()} animals "
        f"({dataset['label'].mean():.1%} followed by illness within {horizon_days} days).")

    train, test = _group_split(dataset, test_size=0.2, seed=RANDOM_STATE)
    fit, val = _group_split(train, test_size=0.25, seed=RANDOM_STATE + 1)

    # --- Step 2: model selection on validation ---------------------------
    comparison = {}
    for name, pipe in make_candidates().items():
        pipe.fit(fit[FEATURE_COLUMNS], fit["label"])
        proba = pipe.predict_proba(val[FEATURE_COLUMNS])[:, 1]
        comparison[name] = round(float(roc_auc_score(val["label"], proba)), 4)
        log(f"  validation ROC-AUC  {name:<20} {comparison[name]:.3f}")
    best_name = max(comparison, key=comparison.get)

    best = make_candidates()[best_name]
    best.fit(fit[FEATURE_COLUMNS], fit["label"])
    threshold = _best_f1_threshold(val["label"], best.predict_proba(val[FEATURE_COLUMNS])[:, 1])
    log(f"Selected: {best_name} (alert threshold {threshold:.2f})")

    # --- Step 3: one honest evaluation on untouched test animals ---------
    best = make_candidates()[best_name]
    best.fit(train[FEATURE_COLUMNS], train["label"])
    test_metrics = _metrics(test["label"].values, best.predict_proba(test[FEATURE_COLUMNS])[:, 1], threshold)
    log(f"Test set: ROC-AUC {test_metrics['roc_auc']:.3f} | precision {test_metrics['precision']:.2f} | "
        f"recall {test_metrics['recall']:.2f} | F1 {test_metrics['f1']:.2f}")

    # --- Step 4: final model on all data --------------------------------
    final = make_candidates()[best_name]
    final.fit(dataset[FEATURE_COLUMNS], dataset["label"])

    metadata = {
        "model_name": best_name,
        "threshold": threshold,
        "horizon_days": horizon_days,
        "feature_columns": FEATURE_COLUMNS,
        "validation_roc_auc_by_model": comparison,
        "test_metrics": test_metrics,
        "data_source": data_source,
        "n_animals": int(dataset["animal_id"].nunique()),
        "n_snapshots": int(len(dataset)),
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
    }
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final, **metadata}, model_path)
    # Human-readable copy of the results (safe to commit, useful for the report).
    model_path.with_name(model_path.stem + "_metrics.json").write_text(json.dumps(metadata, indent=2))
    log(f"Saved model to {model_path}")
    return {"pipeline": final, **metadata}


def main():
    parser = argparse.ArgumentParser(description="Train the sickness-risk model.")
    parser.add_argument("--source", choices=["db", "synthetic"], default="db")
    parser.add_argument("--animals", type=int, default=300, help="Animals to simulate with --source synthetic.")
    parser.add_argument("--horizon", type=int, default=HORIZON_DAYS, help="Days ahead to predict illness.")
    parser.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    args = parser.parse_args()

    if args.source == "synthetic":
        from ml.synthetic import generate_synthetic_data
        frames = generate_synthetic_data(n_animals=args.animals)
        train_from_frames(frames["livestock"], frames["weights"], frames["health"], args.out, "synthetic", args.horizon)
    else:
        from app import create_app
        from ml.data import load_frames
        app = create_app()
        with app.app_context():
            frames = load_frames()
        train_from_frames(frames["livestock"], frames["weights"], frames["health"], args.out, "database", args.horizon)


if __name__ == "__main__":
    main()
