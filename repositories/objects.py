# university_portal/repositories/objects.py
from db import get_db


def get_all_teachers():
    conn = get_db()
    try:
        return conn.execute(
            """SELECT t.*, d.code AS dept_code, d.name AS dept_name
               FROM teachers t
               JOIN departments d ON t.department_id = d.id
               ORDER BY t.staff_code"""
        ).fetchall()
    finally:
        conn.close()


def get_teacher_by_id(tid: int):
    conn = get_db()
    try:
        return conn.execute(
            """SELECT t.*, d.code AS dept_code, d.name AS dept_name
               FROM teachers t
               JOIN departments d ON t.department_id = d.id
               WHERE t.id=?""",
            (tid,),
        ).fetchone()
    finally:
        conn.close()


def get_teacher_by_staff_code(code: str):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM teachers WHERE staff_code=?", (code,)
        ).fetchone()
    finally:
        conn.close()


def get_all_students():
    conn = get_db()
    try:
        return conn.execute(
            """SELECT s.*, d.code AS dept_code, d.name AS dept_name
               FROM students s
               JOIN departments d ON s.department_id = d.id
               ORDER BY s.roll_no"""
        ).fetchall()
    finally:
        conn.close()


def get_student_by_roll(roll_no: str):
    conn = get_db()
    try:
        return conn.execute(
            """SELECT s.*, d.code AS dept_code, d.name AS dept_name
               FROM students s
               JOIN departments d ON s.department_id = d.id
               WHERE s.roll_no=?""",
            (roll_no,),
        ).fetchone()
    finally:
        conn.close()


def get_student_by_id(sid: int):
    conn = get_db()
    try:
        return conn.execute(
            """SELECT s.*, d.code AS dept_code, d.name AS dept_name
               FROM students s
               JOIN departments d ON s.department_id = d.id
               WHERE s.id=?""",
            (sid,),
        ).fetchone()
    finally:
        conn.close()


def get_all_courses():
    conn = get_db()
    try:
        return conn.execute(
            """SELECT c.*, t.name AS teacher_name, t.staff_code,
                      d.code AS dept_code, d.name AS dept_name
               FROM courses c
               JOIN teachers t ON c.teacher_id = t.id
               JOIN departments d ON c.department_id = d.id
               ORDER BY c.code"""
        ).fetchall()
    finally:
        conn.close()


def get_course_by_id(cid: int):
    conn = get_db()
    try:
        return conn.execute(
            """SELECT c.*, t.name AS teacher_name, t.staff_code,
                      d.code AS dept_code, d.name AS dept_name
               FROM courses c
               JOIN teachers t ON c.teacher_id = t.id
               JOIN departments d ON c.department_id = d.id
               WHERE c.id=?""",
            (cid,),
        ).fetchone()
    finally:
        conn.close()
