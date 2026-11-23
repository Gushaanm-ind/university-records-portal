# university_portal/repositories/departments.py
from portal.db import get_db


def get_all_departments():
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM departments ORDER BY code").fetchall()
    finally:
        conn.close()


def get_department_by_id(dept_id: int):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM departments WHERE id=?", (dept_id,)
        ).fetchone()
    finally:
        conn.close()


def get_department_by_code(code: str):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM departments WHERE code=?", (code,)
        ).fetchone()
    finally:
        conn.close()
