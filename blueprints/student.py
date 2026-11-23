# university_portal/blueprints/student.py
from flask import Blueprint, render_template, session, abort, redirect, url_for, request, g
from repositories.users import get_user_by_id
from repositories.objects import get_student_by_id
from repositories.audit import get_login_history_for_user
from services.permissions import check_access, student_owns_record

student_bp = Blueprint("student", __name__)


@student_bp.route("/student")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "student":
        abort(403)
    g.user = user
    sid = user["student_id"]
    if not sid:
        abort(404)
    student = get_student_by_id(sid)
    if not student:
        abort(404)
    from db import get_db
    conn = get_db()
    try:
        enrolments = conn.execute("""
            SELECT c.id, c.code, c.title, c.credits, c.teacher_id,
                   t.name AS teacher_name, t.staff_code,
                   d.code AS dept_code, d.name AS dept_name,
                   e.marks
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            JOIN teachers t ON c.teacher_id = t.id
            JOIN departments d ON c.department_id = d.id
            WHERE e.student_id = ?
            ORDER BY c.code
        """, (sid,)).fetchall()
    finally:
        conn.close()
    login_history = get_login_history_for_user(session.get("username", ""))
    return render_template("student/index.html", student=student, enrolments=enrolments, login_history=login_history)


@student_bp.route("/student/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "student":
        abort(403)
    g.user = user
    sid = user["student_id"]
    if not sid:
        abort(404)
    student = get_student_by_id(sid)
    if not student:
        abort(404)
    return render_template("student/profile.html", student=student)


@student_bp.route("/student/<int:student_id>", methods=["GET", "POST"])
def view_other_student(student_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "student":
        abort(403)
    g.user = user
    if request.method == "POST":
        # Students may never edit anything, including their own record.
        from services.permissions import _deny
        _deny(user, f"student attempted to edit student {student_id}")
    if not student_owns_record(student_id, user):
        from services.permissions import _deny
        _deny(user, f"view student {student_id}")
    student = get_student_by_id(student_id)
    if not student:
        abort(404)
    return render_template("student/profile.html", student=student)
