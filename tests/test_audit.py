# university_portal/tests/test_audit.py
import pytest


class TestAudit:
    def test_login_success_is_logged(self, admin_client):
        """A successful login should create a LOGIN_SUCCESS audit entry."""
        from repositories.audit import get_audit_logs
        logs = get_audit_logs({"action": "LOGIN_SUCCESS", "username": "admin"})
        # Note: the audit log stores actor_username from the session, not a filter param
        logs_all = get_audit_logs()
        login_success = [l for l in logs_all if l["action"] == "LOGIN_SUCCESS"]
        assert len(login_success) > 0, "No LOGIN_SUCCESS audit entries found"

    def test_login_failure_is_logged(self, client):
        """A failed login should create a LOGIN_FAILED audit entry."""
        from repositories.audit import get_audit_logs
        client.post("/login", data={"username": "nonexistent", "password": "wrong"})
        logs = get_audit_logs()
        login_failed = [l for l in logs if l["action"] == "LOGIN_FAILED"]
        assert len(login_failed) > 0, "No LOGIN_FAILED audit entries found"

    def test_edit_student_writes_audit(self, admin_client, hod_client):
        """Editing a student should write EDIT_STUDENT audit with old/new values."""
        # HOD edits student 101
        from repositories.audit import get_audit_logs
        from db import get_db
        from security import hash_password

        # First set password for HOD
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (hash_password("testpass123!"), "hod"),
            )
            conn.commit()
        finally:
            conn.close()

        resp = hod_client.post("/hod/student/1", data={
            "name": "Updated Name",
            "email": "updated@cse.univ.edu",
            "branch": "",
        })
        assert resp.status_code == 200

        logs = get_audit_logs({"action": "EDIT_STUDENT"})
        edit_logs = [l for l in logs if l["action"] == "EDIT_STUDENT"]
        assert len(edit_logs) > 0, "No EDIT_STUDENT audit entries found"

        # Check old/new values present
        found_field = False
        for log in edit_logs:
            if log["field_changed"] and log["old_value"] and log["new_value"]:
                found_field = True
                break
        assert found_field, "No EDIT_STUDENT entry with old_value and new_value"

    def test_edit_teacher_writes_audit(self, admin_client):
        """Editing a teacher should write EDIT_TEACHER audit with old/new values."""
        from repositories.audit import get_audit_logs
        from db import get_db
        from security import hash_password

        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (hash_password("testpass123!"), "admin"),
            )
            conn.commit()
        finally:
            conn.close()

        resp = admin_client.post("/admin/teacher/1", data={
            "name": "Updated Teacher",
            "email": "updated@cse.univ.edu",
            "phone": "9811100099",
            "branch": "",
        })
        assert resp.status_code == 200

        logs = get_audit_logs()
        edit_logs = [l for l in logs if l["action"] == "EDIT_TEACHER"]
        assert len(edit_logs) > 0, "No EDIT_TEACHER audit entries found"

        found_field = any(log["field_changed"] and log["old_value"] and log["new_value"] for log in edit_logs)
        assert found_field, "No EDIT_TEACHER entry with old_value and new_value"

    def test_hod_cannot_view_activity_log(self, hod_client):
        """HOD should get 403 on activity log."""
        resp = hod_client.get("/admin/activity")
        assert resp.status_code == 403

    def test_admin_can_read_activity_log(self, admin_client):
        """Admin should be able to read the activity log."""
        resp = admin_client.get("/admin/activity")
        assert resp.status_code == 200

    def test_admin_can_export_activity_csv(self, admin_client):
        """Admin should be able to export activity log as CSV."""
        resp = admin_client.get("/admin/activity/export-csv")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert b"When,Who,Role" in resp.data

    def test_view_sensitive_writes_audit(self, admin_client):
        """Revealing national ID should write VIEW_SENSITIVE audit."""
        from repositories.audit import get_audit_logs
        resp = admin_client.post("/admin/national-id/1")
        assert resp.status_code == 200

        logs = get_audit_logs({"action": "VIEW_SENSITIVE"})
        view_logs = [l for l in logs if l["action"] == "VIEW_SENSITIVE"]
        assert len(view_logs) > 0, "No VIEW_SENSITIVE audit entry found"
