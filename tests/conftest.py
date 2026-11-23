# university_portal/tests/conftest.py
"""
Every test gets its own freshly seeded database.

A single seeded template database is built once per session in a temp
directory. Each test copies it, points the app at the copy, and deletes it
afterwards. This keeps tests independent: an edit or password change in one
test cannot leak into another.
"""
import os
import sys
import uuid
import shutil
import tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Required environment for the app + Fernet encryption
if not os.environ.get("PORTAL_FERNET_KEY"):
    from cryptography.fernet import Fernet
    os.environ["PORTAL_FERNET_KEY"] = Fernet.generate_key().decode()
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = uuid.uuid4().hex

TEST_PASSWORD = "testpass123!"

from portal import config  # noqa: E402

_original_db = config.Config.DATABASE
_tmp_dir = tempfile.mkdtemp(prefix="university_tests_")
_template_db = os.path.join(_tmp_dir, "template.db")
config.Config.DATABASE = _template_db

# Build the seeded template database now, before any test module imports data.
from portal.db import init_db, get_db  # noqa: E402
from scripts.seed import seed  # noqa: E402
from portal.security import hash_password  # noqa: E402

init_db()
seed(write_credentials_file=False)

# Every account gets the same known password so tests can log in deterministically.
_conn = get_db()
try:
    _conn.execute(
        """UPDATE users
              SET password_hash = ?,
                  failed_attempts = 0,
                  locked_until = NULL,
                  is_active = 1""",
        (hash_password(TEST_PASSWORD),),
    )
    _conn.commit()
finally:
    _conn.close()


@pytest.fixture(scope="session")
def app():
    from app import create_app

    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    yield application


@pytest.fixture
def db_file():
    """Give this test its own copy of the seeded database."""
    path = os.path.join(_tmp_dir, f"test_{uuid.uuid4().hex}.db")
    shutil.copyfile(_template_db, path)
    config.Config.DATABASE = path
    try:
        yield path
    finally:
        config.Config.DATABASE = _template_db
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def client(app, db_file):
    return app.test_client()


def login_as(client, username, password=TEST_PASSWORD):
    """Log the client in as `username` and return the client."""
    client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    return client


# Each role fixture gets its own client, so asking for both hod_client and
# admin_client in one test does not leave the session logged in as the last one.
@pytest.fixture
def student_client(app, db_file):
    return login_as(app.test_client(), "101")


@pytest.fixture
def teacher_client(app, db_file):
    return login_as(app.test_client(), "T001")


@pytest.fixture
def hod_client(app, db_file):
    return login_as(app.test_client(), "hod")


@pytest.fixture
def admin_client(app, db_file):
    return login_as(app.test_client(), "admin")
