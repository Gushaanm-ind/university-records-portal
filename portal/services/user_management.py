# university_portal/services/user_management.py
from portal.db import get_db
from portal.audit import write_audit
from portal.security import hash_password, generate_random_password
from portal.repositories.users import get_user_by_id


def create_user(
    actor_id, username, password, role, student_id=None, teacher_id=None,
    actor_username=None, actor_role=None, ip=None,
):
    if role not in ("student", "teacher", "hod", "admin"):
        raise ValueError("Invalid role")
    h = hash_password(password)
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO users
               (username, password_hash, role, student_id, teacher_id, is_active)
               VALUES (?,?,?,?,?,1)""",
            (username, h, role, student_id, teacher_id),
        )
        new_id = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()["id"]
        conn.commit()
        write_audit(
            actor_id=actor_id,
            action="CREATE_USER",
            target_type="user",
            target_id=new_id,
            target_label=f"user {username} ({role})",
            ip_address=ip,
            actor_username=actor_username,
            actor_role=actor_role,
        )
        return new_id
    finally:
        conn.close()


def deactivate_user(
    actor_id, user_id, actor_username=None, actor_role=None, ip=None,
):
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return False
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        conn.commit()
        write_audit(
            actor_id=actor_id,
            action="DEACTIVATE_USER",
            target_type="user",
            target_id=user_id,
            target_label=f"user {user['username']} ({user['role']})",
            ip_address=ip,
            actor_username=actor_username,
            actor_role=actor_role,
        )
        return True
    finally:
        conn.close()


def reset_password(
    actor_id, user_id, actor_username=None, actor_role=None, ip=None,
):
    new_pwd = generate_random_password()
    h = hash_password(new_pwd)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?", (h, user_id)
        )
        conn.commit()
        write_audit(
            actor_id=actor_id,
            action="PASSWORD_RESET",
            target_type="user",
            target_id=user_id,
            ip_address=ip,
            actor_username=actor_username,
            actor_role=actor_role,
        )
        return new_pwd
    finally:
        conn.close()
