"""Landing/dashboard routes. This is intentionally a thin placeholder —
the real farmer and worker dashboards (livestock lists, analytics, etc.)
get built in Weeks 3-5. Its job right now is to give login/register
somewhere real to redirect to, and to demonstrate the role-based
rendering pattern (checking isinstance(current_user, Farmer)) that later
routes will reuse.
"""

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Farmer

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    is_farmer = isinstance(current_user, Farmer)
    return render_template("dashboard.html", is_farmer=is_farmer)


@main_bp.route("/predictions")
@login_required
def predictions():
    """Farmer-only page listing every animal's sickness risk, highest
    first. Workers enter data; analytics belong to the farm owner, same
    role split as the rest of the app."""
    if not isinstance(current_user, Farmer):
        flash("Only a farmer account can view health predictions.", "danger")
        return redirect(url_for("main.dashboard"))

    # Imported inside the route so the app still starts (and every other
    # page works) even on a machine without pandas/scikit-learn installed.
    from ml.predict import ModelNotTrainedError, predict_for_farmer

    try:
        results, artifact = predict_for_farmer(current_user.farmer_id, current_app.config["ML_MODEL_PATH"])
    except ModelNotTrainedError:
        return render_template("predictions.html", model_missing=True)

    rows = results.to_dict("records") if not results.empty else []
    counts = {band: sum(r["risk_band"] == band for r in rows) for band in ("High", "Medium", "Under treatment", "Low")}
    return render_template(
        "predictions.html",
        model_missing=False,
        rows=rows,
        counts=counts,
        horizon=artifact["horizon_days"],
        base_rate=artifact["test_metrics"]["positive_rate"],
        model_info=artifact,
    )
