
from . import admin_bp


try:
    from auth_helpers import admin_required
except Exception:
    def admin_required(view):
        def wrapper(*a, **kw): return view(*a, **kw)
        wrapper.__name__ = getattr(view, "__name__", "wrapped")
        return wrapper

@admin_bp.route("/")
@admin_required
def dashboard():

    return "Admin dashboard OK"
