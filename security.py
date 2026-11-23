# university_portal/security.py
import functools
import re
import secrets
import datetime

from flask import session, redirect, url_for, request, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from config import Config

_cipher = None


def get_cipher():
    global _cipher
    if _cipher is None:
        _cipher = Fernet(Config.FERNET_KEY.encode())
    return _cipher


def hash_password(password: str) -> str:
    try:
        return generate_password_hash(password, method="scrypt")
    except Exception:
        return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(hash_value: str, password: str) -> bool:
    return check_password_hash(hash_value, password)


def generate_random_password(length: int = 14) -> str:
    lower = "abcdefghijklmnopqrstuvwxyz"
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    symbols = "!@#$%^&*()_+-="
    alphabet = lower + upper + digits + symbols
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in lower for c in pwd)
                and any(c in upper for c in pwd)
                and any(c in digits for c in pwd)
                and any(c in symbols for c in pwd)):
            return pwd


def encrypt_national_id(national_id: str) -> bytes:
    return get_cipher().encrypt(national_id.encode())


def decrypt_national_id(token: bytes) -> str:
    return get_cipher().decrypt(token).decode()


def is_locked(user) -> bool:
    if not user or not user.get("locked_until"):
        return False
    try:
        lock_until = datetime.datetime.fromisoformat(user["locked_until"])
        return datetime.datetime.utcnow() < lock_until
    except (ValueError, TypeError):
        return False


def meets_password_policy(password: str) -> bool:
    return len(password) >= Config.MIN_PASSWORD_LENGTH


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str):
    email = (email or "").strip()
    if not email or len(email) > Config.MAX_EMAIL_LENGTH:
        return False
    return bool(EMAIL_RE.match(email))


def validate_marks(marks):
    if marks is None:
        return True
    try:
        m = int(marks)
    except (TypeError, ValueError):
        return False
    return Config.MIN_MARKS <= m <= Config.MAX_MARKS
