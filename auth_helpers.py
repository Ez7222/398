from functools import wraps
from flask import session, redirect, url_for, flash
from main import User

def login_required(view):
    """Require an authenticated user via session['user_id'].""" 
    @wraps(view)
    def wrapper(*a, **kw):
        if not session.get("user_id"):
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapper

def admin_required(view):
    """Allow only 'admin' or 'staff' roles to access the view."""
    @wraps(view)
    def wrapper(*a, **kw):
        uid = session.get("user_id")
        if not uid:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        u = User.query.get(uid)
        role = (getattr(u, "role", "member") or "member").lower() if u else "member"
        if role not in ("admin", "staff"):
            flash("Insufficient permissions.", "danger")
            return redirect(url_for("Home"))
        return view(*a, **kw)
    return wrapper
