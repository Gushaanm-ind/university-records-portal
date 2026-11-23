# university_portal/blueprints/dashboard.py
from flask import Blueprint, render_template, session, redirect, url_for
from repositories.users import get_user_by_id
from repositories.audit import get_audit_logs, count_audit_logs

dashboard_bp = Blueprint("dashboard", __name__)


def get_dashboard_counts(user):
    from db import get_db
    conn = get_db()
    try:
        counts = {}
        username = session.get("username", "")
        if user["role"] == "student":
            sid = user["student_id"]
            if sid:
                counts["enrolments"] = conn.execute(
                    "SELECT COUNT(*) FROM enrollments WHERE student_id=?", (sid,)
                ).fetchone()[0]
                counts["courses_with_marks"] = conn.execute(
                    "SELECT COUNT(*) FROM enrollments WHERE student_id=? AND marks IS NOT NULL",
                    (sid,),
                ).fetchone()[0]
            counts["my_login_history"] = conn.execute(
                "SELECT COUNT(*) FROM login_history WHERE username=?", (username,)
            ).fetchone()[0]
        elif user["role"] == "teacher":
            tid = user["teacher_id"]
            if tid:
                counts["my_courses"] = conn.execute(
                    "SELECT COUNT(*) FROM courses WHERE teacher_id=?", (tid,)
                ).fetchone()[0]
            counts["all_students"] = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            counts["all_teachers"] = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
            counts["my_login_history"] = conn.execute(
                "SELECT COUNT(*) FROM login_history WHERE username=?", (username,)
            ).fetchone()[0]
        elif user["role"] == "hod":
            counts["all_students"] = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            counts["all_teachers"] = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
            counts["all_courses"] = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
            counts["all_enrolments"] = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
            counts["login_history_all"] = conn.execute("SELECT COUNT(*) FROM login_history").fetchone()[0]
            counts["my_login_history"] = conn.execute(
                "SELECT COUNT(*) FROM login_history WHERE username=?", (username,)
            ).fetchone()[0]
        elif user["role"] == "admin":
            counts["all_users"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            counts["all_students"] = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            counts["all_teachers"] = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
            counts["all_courses"] = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
            counts["all_enrolments"] = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
            counts["activity_log_entries"] = len(get_audit_logs())
            counts["login_history_all"] = conn.execute("SELECT COUNT(*) FROM login_history").fetchone()[0]
        return counts
    finally:
        conn.close()


@dashboard_bp.route("/")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    from flask import g
    g.user = user
    counts = get_dashboard_counts(user)

    if user["role"] == "admin":
        return redirect(url_for("admin.index"))
    if user["role"] == "hod":
        return redirect(url_for("hod.index"))
    if user["role"] == "teacher":
        return redirect(url_for("teacher.index"))
    return redirect(url_for("student.index"))
