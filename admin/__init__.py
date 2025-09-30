from flask import Blueprint

# Minimal admin blueprint. Templates 可放在 templates/admin 下（可选）
admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../templates"
)

# route
from . import views  # noqa: E402,F401
