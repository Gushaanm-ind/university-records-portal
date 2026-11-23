# university_portal/repositories/audit.py
from portal.db import get_db


def get_audit_logs(filters: dict = None):
    conn = get_db()
    try:
        sql = """
            SELECT * FROM audit_log
            WHERE 1=1
        """
        params = []
        if filters:
            if filters.get("username"):
                sql += " AND actor_username = ?"
                params.append(filters["username"])
            if filters.get("action"):
                sql += " AND action = ?"
                params.append(filters["action"])
            if filters.get("target_type"):
                sql += " AND target_type = ?"
                params.append(filters["target_type"])
            if filters.get("target_id") is not None:
                sql += " AND target_id = ?"
                params.append(filters["target_id"])
            if filters.get("start_date"):
                sql += " AND occurred_at >= ?"
                params.append(filters["start_date"])
            if filters.get("end_date"):
                sql += " AND occurred_at <= ?"
                params.append(filters["end_date"])
        sql += " ORDER BY occurred_at DESC"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_login_history(filters: dict = None):
    conn = get_db()
    try:
        sql = "SELECT * FROM login_history WHERE 1=1"
        params = []
        if filters:
            if filters.get("username"):
                sql += " AND username = ?"
                params.append(filters["username"])
            if filters.get("success") is not None:
                sql += " AND success = ?"
                params.append(1 if filters["success"] else 0)
        sql += " ORDER BY logged_in_at DESC"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_login_history_for_user(username: str):
    return get_login_history({"username": username})


def count_audit_logs(filters: dict = None):
    rows = get_audit_logs(filters)
    return len(rows)
