# tests/conftest.py
import os
import sys
import tempfile
from pathlib import Path
import pytest

# ✅ Ensure the repository root path is added to Python module search path
# This allows pytest to import main.py regardless of the current working directory
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app, db, User, Event


@pytest.fixture(scope="session")
def _tmp_db_path():
    """Create a temporary SQLite database path for testing."""
    fd, path = tempfile.mkstemp(prefix="test_unit_", suffix=".db")
    os.close(fd)
    yield path
    # Clean up temporary file after the test session
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture()
def client(_tmp_db_path):
    """Provide a Flask test client with a temporary isolated database."""
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{_tmp_db_path}",
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost",
    )

    with app.app_context():
        # Recreate tables for a clean test environment
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()
