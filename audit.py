# university_portal/audit.py
import datetime
from db import get_db

AUDIT_ACTIONS = {
    "LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT", "ACCOUNT_LOCKED",
    "EDIT_STUDENT", "EDIT_TEACHER", "EDIT_MARK", "EDIT_PROFILE",
    "CREATE_USER", "DEACTIVATE_USER", "ACTIVATE_USER", "PASSWORD_RESET", "PASSWORD_CHANGE",
    "ACCESS_DENIED", "VIEW_SENSITIVE", "EXPORT_CSV",
}


def _actor_identity(conn, actor_id, actor_username, actor_role):
    """Fill in the actor's username and role so every audit row names someone.

    Callers pass only `actor_id`; the name and role are read from `users` so the
    audit trail never shows an empty actor column.
    """
    if actor_id and (not actor_username or not actor_role):
        row = conn.execute(
            "SELECT username, role FROM users WHERE id = ?", (actor_id,)
        ).fetchone()
        if row:
            actor_username = actor_username or row[0]
            actor_role = actor_role or row[1]
    return actor_username or "", actor_role or ""


def write_audit(
    actor_id: int,
    action: str,
    target_type: str = None,
    target_id: int = None,
    target_label: str = None,
    field_changed: str = None,
    old_value: str = None,
    new_value: str = None,
    ip_address: str = None,
    actor_username: str = None,
    actor_role: str = None,
):
    assert action in AUDIT_ACTIONS, f"Invalid audit action: {action}"
    conn = get_db()
    try:
        actor_username, actor_role = _actor_identity(
            conn, actor_id, actor_username, actor_role
        )
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            """INSERT INTO audit_log
               (occurred_at, actor_username, actor_role, action,
                target_type, target_id, target_label,
                field_changed, old_value, new_value, ip_address)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now,
                actor_username,
                actor_role,
                action,
                target_type,
                target_id,
                target_label,
                field_changed,
                old_value,
                new_value,
                ip_address,
            ),
        )
        conn.commit()
    finally:
        conn.close()
