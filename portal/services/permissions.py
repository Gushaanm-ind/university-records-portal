# university_portal/services/permissions.py
from flask import abort, request
from portal.audit import write_audit


def check_access(user, required_role=None, action_label=None):
    if user is None:
        abort(403)
    if required_role and user["role"] not in required_role:
        _deny(user, action_label or "access denied")
        return False
    return True


def _deny(user, label):
    """Refuse access. The audit row is written once, by the 403 handler."""
    abort(403, description=label)


def can_edit_student(user) -> bool:
    return user["role"] in ("hod", "admin")


def can_edit_teacher(user) -> bool:
    return user["role"] in ("hod", "admin")


def can_edit_mark(user) -> bool:
    return user["role"] in ("hod", "admin")


def can_view_national_id(user) -> bool:
    return user["role"] == "admin"


def can_create_user(user) -> bool:
    return user["role"] == "admin"


def can_view_activity_log(user) -> bool:
    return user["role"] == "admin"


def can_view_reports(user) -> bool:
    return user["role"] in ("admin", "hod", "teacher")


def student_owns_record(student_id: int, user) -> bool:
    if user["role"] == "student":
        return student_id is not None and user["student_id"] == student_id
    return True
