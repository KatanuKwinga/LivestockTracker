"""Landing/dashboard routes. This is intentionally a thin placeholder —
the real farmer and worker dashboards (livestock lists, analytics, etc.)
get built in Weeks 3-5. Its job right now is to give login/register
somewhere real to redirect to, and to demonstrate the role-based
rendering pattern (checking isinstance(current_user, Farmer)) that later
routes will reuse.
"""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import Farmer

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    is_farmer = isinstance(current_user, Farmer)
    return render_template("dashboard.html", is_farmer=is_farmer)
