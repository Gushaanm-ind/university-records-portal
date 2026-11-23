# university_portal/config.py
import os
import sys
import uuid
import warnings

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        warnings.warn(
            "SECRET_KEY not set in environment. Generating a random key for local use only. "
            "Set SECRET_KEY in production.",
            RuntimeWarning,
        )
        SECRET_KEY = uuid.uuid4().hex

    # Which database engine the portal talks to: "sqlite" (default, a single
    # file, no server needed) or "mysql" (a running MySQL server).
    DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite").strip().lower()

    # The database file lives in the project root, one level above this package.
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE = os.path.join(PROJECT_ROOT, "university.db")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "portal")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "university_db")

    DEBUG = os.environ.get("DEBUG", "0") == "1"

    FERNET_KEY = os.environ.get("PORTAL_FERNET_KEY")
    if not FERNET_KEY:
        print(
            "ERROR: PORTAL_FERNET_KEY is not set. "
            "Generate one with: python3 -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"",
            file=sys.stderr,
        )
        sys.exit(1)

    SESSION_TIMEOUT_MINUTES = 30
    LOCKOUT_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    MIN_PASSWORD_LENGTH = 8
    MAX_USERNAME_LENGTH = 64
    MAX_NAME_LENGTH = 120
    MAX_EMAIL_LENGTH = 254
    MAX_PHONE_LENGTH = 32
    MAX_BRANCH_CODE_LENGTH = 10
    MAX_COURSE_CODE_LENGTH = 10
    MAX_MARKS = 100
    MIN_MARKS = 0
