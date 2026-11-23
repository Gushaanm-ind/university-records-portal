# university_portal/repositories/users.py
import datetime
from db import get_db
from config import Config


def get_user_by_username(username: str):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def increment_failed_attempts(user_id: int):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def reset_failed_attempts(user_id: int):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def lock_account(user_id: int):
    until = (datetime.datetime.utcnow()
             + datetime.timedelta(minutes=Config.LOCKOUT_DURATION_MINUTES)).isoformat()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET locked_until = ? WHERE id = ?",
            (until, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_last_login(user_id: int, ip: str):
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET last_login_at = ?, failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (now, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_users():
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users ORDER BY role, username").fetchall()
    finally:
        conn.close()


def get_users_by_role(role: str):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE role=? ORDER BY username", (role,)
        ).fetchall()
    finally:
        conn.close()
