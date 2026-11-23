# university_portal/blueprints/admin.py
import re
from flask import Blueprint, render_template, session, abort, request, redirect, url_for, make_response, g
from portal.db import get_db
from portal.repositories.users import get_user_by_id, get_user_by_username, get_all_users
from portal.repositories.objects import get_all_students, get_student_by_id, get_student_by_roll, get_all_teachers, get_teacher_by_id, get_teacher_by_staff_code
from portal.repositories.objects import get_all_courses, get_course_by_id
from portal.repositories.audit import get_audit_logs, get_login_history
from portal.repositories.departments import get_all_departments, get_department_by_code
from portal.services.permissions import (
    check_access, can_view_national_id, can_create_user,
    can_view_activity_log, can_view_reports,
)
from portal.services.edits import edit_student_profile, edit_teacher_profile, edit_mark
from portal.services.user_management import create_user, deactivate_user, reset_password
from portal.security import validate_email, meets_password_policy, decrypt_national_id
from portal.audit import write_audit

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
def index():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    all_students = get_all_students()
    all_teachers = get_all_teachers()
    all_courses = get_all_courses()
    all_users = get_all_users()
    conn = get_db()
    try:
        enrolments_count = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
        graded_count = conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE marks IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    login_history = get_login_history({"success": None})
    role_counts = {}
    for row in all_users:
        role_counts[row["role"]] = role_counts.get(row["role"], 0) + 1
    active_users = sum(1 for row in all_users if row["is_active"])
    recent_logs = get_audit_logs()[:8]
    return render_template("admin/index.html", all_students=all_students, all_teachers=all_teachers,
                           all_courses=all_courses, all_users=all_users,
                           enrolments_count=enrolments_count, graded_count=graded_count,
                           login_history=login_history, role_counts=role_counts,
                           active_users=active_users,
                           inactive_users=len(all_users) - active_users,
                           recent_logs=recent_logs)


@admin_bp.route("/admin/students")
def list_students():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    students = get_all_students()
    if search:
        students = [s for s in students if search.lower() in s["name"].lower() or search == str(s["roll_no"])]
    if branch:
        students = [s for s in students if s["dept_code"] == branch]
    return render_template("admin/students.html", students=students, search=search, branch=branch)


@admin_bp.route("/admin/student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label=f"edit student {student_id}")

    student = get_student_by_id(student_id)
    if not student:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None
        branch_code = (request.form.get("branch") or "").strip() or None

        if name and len(name) > 120:
            return render_template("admin/student_detail.html", student=student, error="Name too long",
                                   departments=get_all_departments(), editable=True), 400
        if email and not validate_email(email):
            return render_template("admin/student_detail.html", student=student, error="Invalid email",
                                   departments=get_all_departments(), editable=True), 400
        department_id = None
        if branch_code:
            dept = get_department_by_code(branch_code)
            if not dept:
                return render_template("admin/student_detail.html", student=student,
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
        from portal.db import get_db
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
        return render_template("admin/student_detail.html", student=student, enrolments=enrolments,
                               success="Student updated", changed=changed, departments=get_all_departments())

    from portal.db import get_db
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
    return render_template("admin/student_detail.html", student=student, enrolments=enrolments,
                           departments=get_all_departments(), editable=True)


@admin_bp.route("/admin/national-id/<int:student_id>", methods=["POST"])
def reveal_national_id(student_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label=f"view national ID for student {student_id}")

    student = get_student_by_id(student_id)
    if not student:
        abort(404)

    national_id = None
    if student["national_id_enc"]:
        try:
            national_id = decrypt_national_id(student["national_id_enc"])
        except Exception:
            national_id = "<decryption error>"

    write_audit(actor_id=user_id, action="VIEW_SENSITIVE", target_type="student",
                target_id=student_id,
                target_label=f"national ID of student {student['name']} (roll {student['roll_no']})",
                ip_address=request.remote_addr or "",
                actor_username=session.get("username"),
                actor_role=user["role"])

    return render_template("admin/national_id_reveal.html", student=student, national_id=national_id)


@admin_bp.route("/admin/teachers")
def list_teachers():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    teachers = get_all_teachers()
    if search:
        teachers = [t for t in teachers if search.lower() in t["name"].lower() or search.lower() == t["staff_code"].lower()]
    if branch:
        teachers = [t for t in teachers if t["dept_code"] == branch]
    return render_template("admin/teachers.html", teachers=teachers, search=search, branch=branch)


@admin_bp.route("/admin/teacher/<int:teacher_id>", methods=["GET", "POST"])
def edit_teacher(teacher_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label=f"edit teacher {teacher_id}")

    teacher = get_teacher_by_id(teacher_id)
    if not teacher:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None
        phone = (request.form.get("phone") or "").strip() or None
        branch_code = (request.form.get("branch") or "").strip() or None

        if name and len(name) > 120:
            return render_template("admin/teacher_detail.html", teacher=teacher, error="Name too long",
                                   departments=get_all_departments(), editable=True), 400
        if email and not validate_email(email):
            return render_template("admin/teacher_detail.html", teacher=teacher, error="Invalid email",
                                   departments=get_all_departments(), editable=True), 400
        if phone and len(phone) > 32:
            return render_template("admin/teacher_detail.html", teacher=teacher, error="Phone too long",
                                   departments=get_all_departments(), editable=True), 400
        department_id = None
        if branch_code:
            dept = get_department_by_code(branch_code)
            if not dept:
                return render_template("admin/teacher_detail.html", teacher=teacher,
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
        return render_template("admin/teacher_detail.html", teacher=teacher, success="Teacher updated",
                               changed=changed, departments=get_all_departments())

    return render_template("admin/teacher_detail.html", teacher=teacher,
                           departments=get_all_departments(), editable=True)


@admin_bp.route("/admin/courses")
def list_courses():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    courses = get_all_courses()
    return render_template("admin/courses.html", courses=courses)


@admin_bp.route("/admin/course/<int:course_id>", methods=["GET", "POST"])
def edit_course_marks(course_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label=f"edit marks for course {course_id}")

    course = get_course_by_id(course_id)
    if not course:
        abort(404)

    from portal.db import get_db
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
                        return render_template("admin/course_detail.html", course=course,
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
                    return render_template("admin/course_detail.html", course=course,
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
        return render_template("admin/course_detail.html", course=course, enrolments=enrolments,
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
    return render_template("admin/course_detail.html", course=course, enrolments=enrolments, editable=True)


@admin_bp.route("/admin/users")
def list_users():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    search = (request.args.get("search") or "").strip()
    role_filter = (request.args.get("role") or "").strip()
    status_filter = (request.args.get("status") or "").strip()

    all_users = get_all_users()
    role_counts = {}
    for row in all_users:
        role_counts[row["role"]] = role_counts.get(row["role"], 0) + 1

    users = all_users
    if search:
        needle = search.lower()
        users = [u for u in users if needle in u["username"].lower()]
    if role_filter:
        users = [u for u in users if u["role"] == role_filter]
    if status_filter == "active":
        users = [u for u in users if u["is_active"]]
    elif status_filter == "inactive":
        users = [u for u in users if not u["is_active"]]

    return render_template(
        "admin/users.html",
        users=users,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        role_counts=role_counts,
        total_users=len(all_users),
        active_count=sum(1 for u in all_users if u["is_active"]),
        inactive_count=sum(1 for u in all_users if not u["is_active"]),
    )


@admin_bp.route("/admin/create-user", methods=["GET", "POST"])
def create_user_view():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "")
        role = (request.form.get("role") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip() or None
        branch_code = (request.form.get("branch") or "").strip() or None
        phone = (request.form.get("phone") or "").strip() or None

        errors = []
        if not username or len(username) > 64:
            errors.append("Username is required (max 64 chars).")
        elif not re.match(r"^[A-Za-z0-9._-]+$", username):
            errors.append("Username may only contain letters, numbers, dots, dashes and underscores.")
        if not password or not meets_password_policy(password):
            errors.append("Password must be at least 8 characters.")
        if role not in ("student", "teacher", "hod", "admin"):
            errors.append("Role must be student, teacher, hod, or admin.")
        if role in ("student", "hod", "teacher") and not branch_code:
            errors.append("Branch is required for this role.")
        if role in ("student", "teacher") and not full_name:
            errors.append(f"Full name is required for {role}.")
        if role == "teacher" and not phone:
            errors.append("Phone is required for teacher.")
        if email and not validate_email(email):
            errors.append("Invalid email address.")

        dept = get_department_by_code(branch_code) if branch_code else None
        if branch_code and not dept:
            errors.append(f"Branch {branch_code} does not exist.")

        if username and get_user_by_username(username):
            errors.append(f"The username {username} is already taken.")

        if email:
            conn = get_db()
            try:
                taken = conn.execute(
                    "SELECT 1 FROM students WHERE email=? UNION SELECT 1 FROM teachers WHERE email=?",
                    (email, email),
                ).fetchone()
            finally:
                conn.close()
            if taken:
                errors.append("That email address already belongs to another student or teacher.")

        if errors:
            return render_template("admin/create_user.html",
                                   error=" ".join(errors),
                                   departments=get_all_departments(),
                                   username=username, role=role, full_name=full_name,
                                   email=email, branch_code=branch_code, phone=phone), 400

        department_id = dept["id"] if dept else None

        student_id = None
        teacher_id = None
        conn = get_db()
        try:
            if role == "student":
                conn.execute(
                    "INSERT INTO students (roll_no, name, email, department_id, national_id_enc) VALUES (?,?,?,?,NULL)",
                    (username, full_name,
                     email or f"{username}@student.univ.edu",
                     department_id),
                )
                student_id = conn.execute(
                    "SELECT id FROM students WHERE roll_no=?", (username,)
                ).fetchone()["id"]
            elif role == "teacher":
                conn.execute(
                    "INSERT INTO teachers (staff_code, name, email, phone, department_id) VALUES (?,?,?,?,?)",
                    (username, full_name, email or f"{username}@cse.univ.edu",
                     phone or "", department_id),
                )
                teacher_id = conn.execute(
                    "SELECT id FROM teachers WHERE staff_code=?", (username,)
                ).fetchone()["id"]
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            return render_template("admin/create_user.html",
                                   error="That roll number, staff code or email is already in use. "
                                         "Check the values and try again.",
                                   departments=get_all_departments(),
                                   username=username, role=role, full_name=full_name,
                                   email=email, branch_code=branch_code, phone=phone), 400
        finally:
            try:
                conn.close()
            except Exception:
                pass

        try:
            new_user_id = create_user(actor_id=user_id, username=username, password=password, role=role,
                                      student_id=student_id, teacher_id=teacher_id,
                                      actor_username=session.get("username"),
                                      actor_role=user["role"],
                                      ip=request.remote_addr or "")
        except Exception:
            # Never leave a student/teacher row behind without its login account.
            conn = get_db()
            try:
                if student_id:
                    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
                if teacher_id:
                    conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
                conn.commit()
            finally:
                conn.close()
            return render_template("admin/create_user.html",
                                   error="The login account could not be created. "
                                         "The username may already be in use.",
                                   departments=get_all_departments(),
                                   username=username, role=role, full_name=full_name,
                                   email=email, branch_code=branch_code, phone=phone), 400

        return render_template("admin/create_user_done.html", username=username, role=role,
                               full_name=full_name, password=password, user_id=new_user_id)

    return render_template("admin/create_user.html", departments=get_all_departments())


@admin_bp.route("/admin/deactivate-user/<int:user_id>", methods=["POST"])
def deactivate_user_view(user_id):
    caller_id = session.get("user_id")
    if not caller_id:
        return redirect(url_for("auth.login"))
    caller = get_user_by_id(caller_id)
    if not caller or caller["role"] != "admin":
        abort(403)
    g.user = caller
    check_access(caller, required_role=("admin",), action_label=f"deactivate user {user_id}")

    if caller["id"] == user_id:
        return render_template("admin/users.html", users=get_all_users(),
                               error="You cannot deactivate your own account."), 400

    success = deactivate_user(actor_id=caller_id, user_id=user_id,
                              actor_username=session.get("username"),
                              actor_role=caller["role"],
                              ip=request.remote_addr or "")
    if not success:
        abort(404)
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/admin/activate-user/<int:user_id>", methods=["POST"])
def activate_user_view(user_id):
    caller_id = session.get("user_id")
    if not caller_id:
        return redirect(url_for("auth.login"))
    caller = get_user_by_id(caller_id)
    if not caller or caller["role"] != "admin":
        abort(403)
    g.user = caller
    check_access(caller, required_role=("admin",), action_label=f"activate user {user_id}")

    target = get_user_by_id(user_id)
    if not target:
        abort(404)

    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET is_active=1, failed_attempts=0, locked_until=NULL WHERE id=?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    write_audit(actor_id=caller_id, action="ACTIVATE_USER", target_type="user",
                target_id=user_id,
                target_label=f"user {target['username']} ({target['role']})",
                ip_address=request.remote_addr or "",
                actor_username=session.get("username"),
                actor_role=caller["role"])
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/admin/reset-password/<int:user_id>", methods=["POST"])
def reset_password_view(user_id):
    caller_id = session.get("user_id")
    if not caller_id:
        return redirect(url_for("auth.login"))
    caller = get_user_by_id(caller_id)
    if not caller or caller["role"] != "admin":
        abort(403)
    g.user = caller
    check_access(caller, required_role=("admin",), action_label=f"reset password for user {user_id}")

    target = get_user_by_id(user_id)
    if not target:
        abort(404)

    new_pwd = reset_password(actor_id=caller_id, user_id=user_id,
                             actor_username=session.get("username"),
                             actor_role=caller["role"],
                             ip=request.remote_addr or "")

    return render_template("admin/reset_password_result.html",
                           username=target["username"], role=target["role"], new_password=new_pwd)


@admin_bp.route("/admin/activity")
def activity_log():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label="view activity log")

    username_filter = (request.args.get("username") or "").strip()
    action_filter = (request.args.get("action") or "").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()
    target_type = (request.args.get("target_type") or "").strip()
    target_id = request.args.get("target_id")
    if target_id:
        try:
            target_id = int(target_id)
        except ValueError:
            target_id = None

    filters = {}
    if username_filter:
        filters["username"] = username_filter
    if action_filter:
        filters["action"] = action_filter
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    if target_type:
        filters["target_type"] = target_type
    if target_id is not None:
        filters["target_id"] = target_id

    logs = get_audit_logs(filters)
    return render_template("admin/activity.html", logs=logs,
                           username_filter=username_filter, action_filter=action_filter,
                           start_date=start_date, end_date=end_date,
                           target_type=target_type, target_id=target_id)


@admin_bp.route("/admin/activity/export-csv")
def export_activity_csv():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    check_access(user, required_role=("admin",), action_label="export activity log")

    username_filter = (request.args.get("username") or "").strip()
    action_filter = (request.args.get("action") or "").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    filters = {}
    if username_filter:
        filters["username"] = username_filter
    if action_filter:
        filters["action"] = action_filter
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    logs = get_audit_logs(filters)

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["When", "Who", "Role", "What happened", "On whom",
                     "Changed from", "Changed to", "IP address"])
    for row in logs:
        writer.writerow([
            row["occurred_at"],
            row["actor_username"],
            row["actor_role"],
            row["action"],
            f"{row['target_type']} {row['target_id']} ({row['target_label']})"
            if row["target_label"] else f"{row['target_type']} {row['target_id']}",
            row["old_value"] or "",
            row["new_value"] or "",
            row["ip_address"] or "",
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=activity_log.csv"
    write_audit(actor_id=user_id, action="EXPORT_CSV", target_type="audit_log",
                ip_address=request.remote_addr or "",
                actor_username=session.get("username"),
                actor_role=user["role"])
    return response


@admin_bp.route("/admin/login-history")
def admin_login_history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user
    username_filter = (request.args.get("username") or "").strip()
    success_filter = request.args.get("success")
    filters = {}
    if username_filter:
        filters["username"] = username_filter
    if success_filter is not None:
        filters["success"] = success_filter == "1"
    logs = get_login_history(filters)
    return render_template("admin/login_history.html", logs=logs,
                           username_filter=username_filter, success_filter=success_filter)


@admin_bp.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] != "admin":
        abort(403)
    g.user = user

    if request.method == "POST":
        new_username = (request.form.get("username") or "").strip()

        errors = []
        if not new_username:
            errors.append("Username is required.")
        elif len(new_username) > 64:
            errors.append("Username must be 64 characters or fewer.")
        elif not re.match(r"^[A-Za-z0-9._-]+$", new_username):
            errors.append("Use only letters, numbers, dots, dashes and underscores.")
        elif new_username != user["username"] and get_user_by_username(new_username):
            errors.append("That username is already taken.")

        if errors:
            return render_template("admin/profile.html", user=user,
                                   error=" ".join(errors)), 400

        if new_username == user["username"]:
            return render_template("admin/profile.html", user=user,
                                   success="No changes to save.")

        old_username = user["username"]
        conn = get_db()
        try:
            conn.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))
            conn.commit()
        finally:
            conn.close()

        write_audit(actor_id=user_id, action="EDIT_PROFILE", target_type="user",
                    target_id=user_id, target_label=f"admin {old_username}",
                    field_changed="username", old_value=old_username, new_value=new_username,
                    ip_address=request.remote_addr or "",
                    actor_role=user["role"])

        session["username"] = new_username
        user = get_user_by_id(user_id)
        g.user = user
        return render_template("admin/profile.html", user=user, success="Profile updated.")

    return render_template("admin/profile.html", user=user)


def _make_context_processors():
    """Register template context processors for admin blueprint."""
    @admin_bp.app_context_processor
    def inject_helpers():
        return {
            "get_student_by_roll": get_student_by_roll,
            "get_teacher_by_staff_code": get_teacher_by_staff_code,
        }


_make_context_processors()


@admin_bp.route("/admin/reports")
def reports():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = get_user_by_id(user_id)
    if not user or user["role"] not in ("admin", "hod", "teacher"):
        abort(403)
    g.user = user
    check_access(user, required_role=("admin", "hod", "teacher"), action_label="view reports")

    from portal.services.reports import (
        avg_marks_per_branch, students_above_branch_average,
        courses_with_highest_average, second_highest_mark,
        second_highest_mark_student_course, students_above_overall_average,
    )

    return render_template("admin/reports.html",
                           avg_marks_per_branch=avg_marks_per_branch(),
                           students_above_branch_average=students_above_branch_average(),
                           courses_with_highest_average=courses_with_highest_average(),
                           second_highest_mark=second_highest_mark(),
                           second_highest_student_course=second_highest_mark_student_course(),
                           students_above_overall_average=students_above_overall_average())
