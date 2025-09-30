from functools import wraps
from flask import session, redirect, url_for, flash

try:
    from main import User  # adjust if your model lives elsewhere
except Exception:
    User = None

def login_required(view):
    """Ensure a user is logged in via session['user_id']."""
    @wraps(view)
    def wrapper(*a, **kw):
        if not session.get("user_id"):
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapper

def admin_required(view):
    """Allow only 'staff' or 'admin' roles to access a view."""
    @wraps(view)
    def wrapper(*a, **kw):
        uid = session.get("user_id")
        if not uid:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if User is None:
            flash("User model not found. Fix imports in auth_helpers.py.", "danger")
            return redirect(url_for("Home"))
        u = User.query.get(uid)
        role = (u.role or "member") if u else "member"
        if role not in ("staff", "admin"):
            flash("Insufficient permissions.", "danger")
            return redirect(url_for("Home"))
        return view(*a, **kw)
    return wrapper
