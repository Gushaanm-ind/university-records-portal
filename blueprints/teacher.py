# university_portal/blueprints/teacher.py
from flask import Blueprint, render_template, session, abort, request, redirect, url_for, g
from repositories.users import get_user_by_id
from repositories.objects import get_all_students, get_student_by_id, get_all_courses, get_course_by_id
from repositories.audit import get_login_history_for_user
from services.permissions import check_access
from audit import write_audit

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/teacher")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "teacher":
        abort(403)
    g.user = user
    tid = user["teacher_id"]
    courses = []
    if tid:
        from db import get_db
        conn = get_db()
        try:
            courses = conn.execute("""
                SELECT c.*, d.code AS dept_code, d.name AS dept_name
                FROM courses c
                JOIN departments d ON c.department_id = d.id
                WHERE c.teacher_id = ?
                ORDER BY c.code
            """, (tid,)).fetchall()
        finally:
            conn.close()
    all_students = get_all_students()
    login_history = get_login_history_for_user(session.get("username", ""))
    return render_template("teacher/index.html", courses=courses, all_students=all_students, login_history=login_history)


@teacher_bp.route("/teacher/students")
def list_students():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "teacher":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    students = get_all_students()
    if search:
        students = [s for s in students if search.lower() in s["name"].lower() or search == str(s["roll_no"])]
    if branch:
        students = [s for s in students if s["dept_code"] == branch]
    return render_template("teacher/students.html", students=students, search=search, branch=branch)


@teacher_bp.route("/teacher/student/<int:student_id>", methods=["GET", "POST"])
def view_student(student_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "teacher":
        abort(403)
    g.user = user
    if request.method == "POST":
        # Teachers may view students but never edit them.
        write_audit(
            actor_id=user["id"],
            action="ACCESS_DENIED",
            target_type="student",
            target_id=student_id,
            target_label=f"teacher attempted to edit student {student_id}",
            ip_address=request.remote_addr or "",
            actor_username=session.get("username"),
            actor_role=user["role"],
        )
        abort(403)
    student = get_student_by_id(student_id)
    if not student:
        abort(404)
    from db import get_db
    conn = get_db()
    try:
        enrolments = conn.execute("""
            SELECT c.id, c.code, c.title, c.credits,
                   t.name AS teacher_name, t.staff_code,
                   d.code AS dept_code, d.name AS dept_name,
                   e.marks
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            JOIN teachers t ON c.teacher_id = t.id
            JOIN departments d ON c.department_id = d.id
            WHERE e.student_id = ?
            ORDER BY c.code
        """, (student_id,)).fetchall()
    finally:
        conn.close()
    return render_template("teacher/student_detail.html", student=student, enrolments=enrolments, editable=False)


@teacher_bp.route("/teacher/courses")
def list_courses():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "teacher":
        abort(403)
    g.user = user
    courses = get_all_courses()
    return render_template("teacher/courses.html", courses=courses)


@teacher_bp.route("/teacher/course/<int:course_id>", methods=["GET", "POST"])
def view_course(course_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "teacher":
        abort(403)
    g.user = user
    if request.method == "POST":
        # Teachers may read marks but never change them.
        write_audit(
            actor_id=user["id"],
            action="ACCESS_DENIED",
            target_type="course",
            target_id=course_id,
            target_label=f"teacher attempted to edit marks for course {course_id}",
            ip_address=request.remote_addr or "",
            actor_username=session.get("username"),
            actor_role=user["role"],
        )
        abort(403)
    course = get_course_by_id(course_id)
    if not course:
        abort(404)
    from db import get_db
    conn = get_db()
    try:
        enrolments = conn.execute("""
            SELECT s.roll_no, s.name, s.email, d.code AS dept_code, d.name AS dept_name,
                   e.marks
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE e.course_id = ?
            ORDER BY s.roll_no
        """, (course_id,)).fetchall()
    finally:
        conn.close()
    return render_template("teacher/course_detail.html", course=course, enrolments=enrolments, editable=False)
