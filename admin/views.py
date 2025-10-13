from . import admin_bp
from flask import redirect, url_for
from auth_helpers import admin_required

@admin_bp.route("/")
@admin_required
def dashboard():
    return redirect(url_for("rgsq_staff_html"))
