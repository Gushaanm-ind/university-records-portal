# university_portal/blueprints/hod.py
from flask import Blueprint, render_template, session, abort, request, redirect, url_for, g
from repositories.users import get_user_by_id
from repositories.objects import get_all_students, get_student_by_id, get_all_teachers, get_teacher_by_id
from repositories.objects import get_all_courses, get_course_by_id
from repositories.audit import get_login_history_for_user, get_login_history
from repositories.departments import get_all_departments, get_department_by_code
from services.permissions import check_access
from services.edits import edit_student_profile, edit_teacher_profile, edit_mark
from security import validate_email
from audit import write_audit

hod_bp = Blueprint("hod", __name__)


@hod_bp.route("/hod")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    all_students = get_all_students()
    all_teachers = get_all_teachers()
    all_courses = get_all_courses()
    from db import get_db
    conn = get_db()
    try:
        enrolments_count = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
    finally:
        conn.close()
    login_history = get_login_history({"success": None})
    login_history = [r for r in login_history if r["username"] != "admin"]
    return render_template("hod/index.html", all_students=all_students, all_teachers=all_teachers,
                           all_courses=all_courses, enrolments_count=enrolments_count,
                           login_history=login_history)


@hod_bp.route("/hod/students")
def list_students():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    students = get_all_students()
    if search:
        students = [s for s in students if search.lower() in s["name"].lower() or search == str(s["roll_no"])]
    if branch:
        students = [s for s in students if s["dept_code"] == branch]
    return render_template("hod/students.html", students=students, search=search, branch=branch)


@hod_bp.route("/hod/student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    check_access(user, required_role=("hod", "admin"), action_label=f"edit student {student_id}")

    student = get_student_by_id(student_id)
    if not student:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None
        branch_code = (request.form.get("branch") or "").strip() or None

        if name and len(name) > 120:
            return render_template("hod/student_detail.html", student=student, error="Name too long",
                                   departments=get_all_departments(), editable=True), 400
        if email and not validate_email(email):
            return render_template("hod/student_detail.html", student=student, error="Invalid email",
                                   departments=get_all_departments(), editable=True), 400
        department_id = None
        if branch_code:
            dept = get_department_by_code(branch_code)
            if not dept:
                return render_template("hod/student_detail.html", student=student,
                                       error="Branch not found",
                                       departments=get_all_departments(), editable=True), 400
            department_id = dept["id"]

        changed = edit_student_profile(user_id=user_id, student_id=student_id, name=name, email=email,
                                       department_id=department_id,
                                       actor_username=session.get("username"),
                                       actor_role=user["role"],
                                       ip=request.remote_addr or "")
        if changed is None:
            abort(404)
        student = get_student_by_id(student_id)
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
        return render_template("hod/student_detail.html", student=student, enrolments=enrolments,
                               success="Student updated", changed=changed, departments=get_all_departments())

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
    return render_template("hod/student_detail.html", student=student, enrolments=enrolments,
                           departments=get_all_departments(), editable=True)


@hod_bp.route("/hod/teachers")
def list_teachers():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    teachers = get_all_teachers()
    if search:
        teachers = [t for t in teachers if search.lower() in t["name"].lower() or search.lower() == t["staff_code"].lower()]
    if branch:
        teachers = [t for t in teachers if t["dept_code"] == branch]
    return render_template("hod/teachers.html", teachers=teachers, search=search, branch=branch)


@hod_bp.route("/hod/teacher/<int:teacher_id>", methods=["GET", "POST"])
def edit_teacher(teacher_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    check_access(user, required_role=("hod", "admin"), action_label=f"edit teacher {teacher_id}")

    teacher = get_teacher_by_id(teacher_id)
    if not teacher:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None
        phone = (request.form.get("phone") or "").strip() or None
        branch_code = (request.form.get("branch") or "").strip() or None

        if name and len(name) > 120:
            return render_template("hod/teacher_detail.html", teacher=teacher, error="Name too long",
                                   departments=get_all_departments(), editable=True), 400
        if email and not validate_email(email):
            return render_template("hod/teacher_detail.html", teacher=teacher, error="Invalid email",
                                   departments=get_all_departments(), editable=True), 400
        if phone and len(phone) > 32:
            return render_template("hod/teacher_detail.html", teacher=teacher, error="Phone too long",
                                   departments=get_all_departments(), editable=True), 400
        department_id = None
        if branch_code:
            dept = get_department_by_code(branch_code)
            if not dept:
                return render_template("hod/teacher_detail.html", teacher=teacher,
                                       error="Branch not found",
                                       departments=get_all_departments(), editable=True), 400
            department_id = dept["id"]

        changed = edit_teacher_profile(user_id=user_id, teacher_id=teacher_id, name=name, email=email,
                                       phone=phone, department_id=department_id,
                                       actor_username=session.get("username"),
                                       actor_role=user["role"],
                                       ip=request.remote_addr or "")
        if changed is None:
            abort(404)
        teacher = get_teacher_by_id(teacher_id)
        return render_template("hod/teacher_detail.html", teacher=teacher, success="Teacher updated",
                               changed=changed, departments=get_all_departments())

    return render_template("hod/teacher_detail.html", teacher=teacher,
                           departments=get_all_departments(), editable=True)


@hod_bp.route("/hod/courses")
def list_courses():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    courses = get_all_courses()
    return render_template("hod/courses.html", courses=courses)


@hod_bp.route("/hod/course/<int:course_id>", methods=["GET", "POST"])
def edit_course_marks(course_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    check_access(user, required_role=("hod", "admin"), action_label=f"edit marks for course {course_id}")

    course = get_course_by_id(course_id)
    if not course:
        abort(404)

    from db import get_db
    conn = get_db()

    if request.method == "POST":
        rows = conn.execute("""
            SELECT e.student_id, s.roll_no, s.name, e.marks
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            WHERE e.course_id = ?
            ORDER BY s.roll_no
        """, (course_id,)).fetchall()

        changed_marks = []
        for row in rows:
            student_id = row["student_id"]
            new_marks_str = request.form.get(f"marks_{row['roll_no']}")
            if new_marks_str is not None and new_marks_str.strip() != "":
                try:
                    marks_val = int(new_marks_str)
                    if not (0 <= marks_val <= 100):
                        conn.close()
                        return render_template("hod/course_detail.html", course=course,
                                               enrolments=rows, error=f"Marks for {row['name']} must be 0-100"), 400
                    result = edit_mark(user_id=user_id, student_id=student_id, course_id=course_id,
                                       new_marks=marks_val,
                                       actor_username=session.get("username"),
                                       actor_role=user["role"],
                                       ip=request.remote_addr or "")
                    if result:
                        old, new = result
                        changed_marks.append({"roll_no": row["roll_no"], "name": row["name"], "old": old, "new": new})
                        write_audit(actor_id=user_id, action="EDIT_MARK", target_type="enrollment",
                                    target_label=f"student {row['name']} (roll {row['roll_no']}), course {course['code']}",
                                    field_changed="marks",
                                    old_value=str(old) if old is not None else "NULL",
                                    new_value=str(new),
                                    ip_address=request.remote_addr or "",
                                    actor_username=session.get("username"),
                                    actor_role=user["role"])
                except ValueError:
                    conn.close()
                    return render_template("hod/course_detail.html", course=course,
                                           enrolments=rows, error=f"Invalid marks for {row['name']}"), 400

        enrolments = conn.execute("""
            SELECT s.roll_no, s.name, s.email, d.code AS dept_code, d.name AS dept_name,
                   e.marks
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE e.course_id = ?
            ORDER BY s.roll_no
        """, (course_id,)).fetchall()
        conn.close()
        return render_template("hod/course_detail.html", course=course, enrolments=enrolments,
                               success="Marks updated", changed_marks=changed_marks, editable=True)

    enrolments = conn.execute("""
        SELECT s.roll_no, s.name, s.email, d.code AS dept_code, d.name AS dept_name,
               e.marks
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN departments d ON s.department_id = d.id
        WHERE e.course_id = ?
        ORDER BY s.roll_no
    """, (course_id,)).fetchall()
    conn.close()
    return render_template("hod/course_detail.html", course=course, enrolments=enrolments, editable=True)


@hod_bp.route("/hod/login-history")
def login_history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "hod":
        abort(403)
    g.user = user
    all_logins = get_login_history({"success": None})
    logins = [r for r in all_logins if r["username"] != "admin"]
    username_filter = (request.args.get("username") or "").strip()
    if username_filter:
        logins = [r for r in logins if username_filter.lower() in r["username"].lower()]
    return render_template("hod/login_history.html", logins=logins, username_filter=username_filter)
