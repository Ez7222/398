# tests/conftest.py
import os
import tempfile
import pytest

from main import app, db, User, Event

@pytest.fixture(scope="session")
def _tmp_db_path():
    fd, path = tempfile.mkstemp(prefix="test_unit_", suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass

@pytest.fixture()
def client(_tmp_db_path):
    # avoid influence events.db
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{_tmp_db_path}",
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost",
    )
    with app.app_context():
        # remake table
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()
