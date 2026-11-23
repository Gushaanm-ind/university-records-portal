# university_portal/services/presence.py
"""
Who is signed in right now.

Flask's session is a signed cookie, so the server has no session table to read.
Presence is therefore kept on the users table: every authenticated request
stamps `last_seen_at` (throttled by the caller), signing out clears it, and an
account counts as online while that stamp is younger than ONLINE_WINDOW_SECONDS.

Note the distinction the UI makes:

    is_active     the account is enabled (an administrator switched it on)
    last_seen_at  somebody actually has a signed-in session right now
"""
import datetime

from portal.db import get_db

# A user stays "online" for this long after their last request.
ONLINE_WINDOW_SECONDS = 120

# app.py rewrites last_seen_at at most this often, not on every request.
STAMP_EVERY_SECONDS = 15


def _now():
    return datetime.datetime.utcnow()


def _parse(value):
    try:
        return datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def seconds_since(value):
    seen = _parse(value)
    if seen is None:
        return None
    return max(0, int((_now() - seen).total_seconds()))


def is_online(value):
    age = seconds_since(value)
    return age is not None and age <= ONLINE_WINDOW_SECONDS


def ago(value):
    """Human wording for how long ago a stamp was written."""
    age = seconds_since(value)
    if age is None:
        return "never"
    if age < 10:
        return "just now"
    if age < 60:
        return f"{age}s ago"
    minutes = age // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def mark_seen(user_id):
    """Record that this account is signed in and active right now."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET last_seen_at = ? WHERE id = ?",
            (_now().isoformat(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_signed_out(user_id):
    """Clear presence so the account shows as offline the moment it logs out."""
    conn = get_db()
    try:
        conn.execute("UPDATE users SET last_seen_at = NULL WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def online_users():
    """Enabled accounts with a live session, most recently active first."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, role, last_seen_at FROM users"
            " WHERE is_active = 1 AND last_seen_at IS NOT NULL"
            " ORDER BY last_seen_at DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "username": row["username"],
            "role": row["role"],
            "last_seen": ago(row["last_seen_at"]),
        }
        for row in rows
        if is_online(row["last_seen_at"])
    ]


def describe(value):
    """Presence wording for one account, for the users table."""
    if is_online(value):
        return {"online": True, "label": "active " + ago(value)}
    if value is None:
        return {"online": False, "label": "never signed in"}
    return {"online": False, "label": "last seen " + ago(value)}


def snapshot(users):
    """{username: describe(last_seen_at)} for a list of user rows."""
    return {row["username"]: describe(row["last_seen_at"]) for row in users}
