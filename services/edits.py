# university_portal/services/edits.py
from db import get_db
from audit import write_audit


def edit_student_profile(
    user_id, student_id, name=None, email=None, department_id=None,
    actor_username=None, actor_role=None, ip=None,
):
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT * FROM students WHERE id=?", (student_id,)
        ).fetchone()
        if not student:
            return None

        changed = {}
        if name is not None and name != student["name"]:
            old = student["name"]
            conn.execute("UPDATE students SET name=? WHERE id=?", (name, student_id))
            changed["name"] = {"old": old, "new": name}
        if email is not None and email != student["email"]:
            old = student["email"]
            conn.execute("UPDATE students SET email=? WHERE id=?", (email, student_id))
            changed["email"] = {"old": old, "new": email}
        if department_id is not None and department_id != student["department_id"]:
            old = student["department_id"]
            conn.execute("UPDATE students SET department_id=? WHERE id=?", (department_id, student_id))
            changed["department_id"] = {"old": old, "new": department_id}

        conn.commit()

        if changed:
            for field, vals in changed.items():
                write_audit(
                    actor_id=user_id,
                    action="EDIT_STUDENT",
                    target_type="student",
                    target_id=student_id,
                    target_label=f"student {student['name']} (roll {student['roll_no']})",
                    field_changed=field,
                    old_value=str(vals["old"]),
                    new_value=str(vals["new"]),
                    ip_address=ip,
                    actor_username=actor_username,
                    actor_role=actor_role,
                )
        return changed
    finally:
        conn.close()


def edit_teacher_profile(
    user_id, teacher_id, name=None, email=None, phone=None, department_id=None,
    actor_username=None, actor_role=None, ip=None,
):
    conn = get_db()
    try:
        teacher = conn.execute(
            "SELECT * FROM teachers WHERE id=?", (teacher_id,)
        ).fetchone()
        if not teacher:
            return None

        changed = {}
        if name is not None and name != teacher["name"]:
            old = teacher["name"]
            conn.execute("UPDATE teachers SET name=? WHERE id=?", (name, teacher_id))
            changed["name"] = {"old": old, "new": name}
        if email is not None and email != teacher["email"]:
            old = teacher["email"]
            conn.execute("UPDATE teachers SET email=? WHERE id=?", (email, teacher_id))
            changed["email"] = {"old": old, "new": email}
        if phone is not None and phone != teacher["phone"]:
            old = teacher["phone"]
            conn.execute("UPDATE teachers SET phone=? WHERE id=?", (phone, teacher_id))
            changed["phone"] = {"old": old, "new": phone}
        if department_id is not None and department_id != teacher["department_id"]:
            old = teacher["department_id"]
            conn.execute("UPDATE teachers SET department_id=? WHERE id=?", (department_id, teacher_id))
            changed["department_id"] = {"old": old, "new": department_id}

        conn.commit()

        if changed:
            for field, vals in changed.items():
                write_audit(
                    actor_id=user_id,
                    action="EDIT_TEACHER",
                    target_type="teacher",
                    target_id=teacher_id,
                    target_label=f"teacher {teacher['name']} ({teacher['staff_code']})",
                    field_changed=field,
                    old_value=str(vals["old"]),
                    new_value=str(vals["new"]),
                    ip_address=ip,
                    actor_username=actor_username,
                    actor_role=actor_role,
                )
        return changed
    finally:
        conn.close()


def edit_mark(
    user_id, student_id, course_id, new_marks,
    actor_username=None, actor_role=None, ip=None,
):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT marks FROM enrollments WHERE student_id=? AND course_id=?",
            (student_id, course_id),
        ).fetchone()
        if not row:
            return None
        old_marks = row["marks"]
        if old_marks == new_marks:
            return (old_marks, new_marks)
        conn.execute(
            "UPDATE enrollments SET marks=? WHERE student_id=? AND course_id=?",
            (new_marks, student_id, course_id),
        )
        conn.commit()
        return (old_marks, new_marks)
    finally:
        conn.close()
