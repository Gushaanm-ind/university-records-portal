# university_portal/tests/test_workflows.py
import pytest


class TestWorkflows:
    def test_hod_changes_student_mark_appears_in_admin_activity_log(self, hod_client, admin_client):
        """HOD changes a student's mark; change appears in admin activity log."""
        from portal.repositories.audit import get_audit_logs
        from portal.db import get_db
        from portal.security import hash_password

        # Set passwords for hod and admin (both fixtures already logged in)
        conn = get_db()
        try:
            h = hash_password("testpass123!")
            conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "hod"))
            conn.execute("UPDATE users SET password_hash=? WHERE username=?", (h, "admin"))
            conn.commit()
        finally:
            conn.close()

        # HOD updates marks for course 1
        resp = hod_client.post("/hod/course/1", data={"marks_101": "95"})
        assert resp.status_code == 200, f"HOD POST course marks failed: {resp.status_code}"

        # Admin checks activity log for EDIT_MARK
        logs = get_audit_logs({"action": "EDIT_MARK"})
        edit_marks = [l for l in logs if l["action"] == "EDIT_MARK"]
        assert len(edit_marks) > 0, "No EDIT_MARK audit entries found after HOD changed marks"

        # Check the target label mentions the student
        found = any("student" in str(l["target_label"] or "").lower() for l in edit_marks)
        assert found, "EDIT_MARK entry should reference the student"

    def test_teacher_can_view_student_but_not_edit(self, teacher_client):
        """Teacher can view a student but not edit."""
        resp = teacher_client.get("/teacher/student/1")
        assert resp.status_code == 200

        resp = teacher_client.post("/teacher/student/1", data={"name": "Hacked"})
        assert resp.status_code == 403

    def test_student_changes_password_and_logs_in_with_new_password(self, student_client):
        """Student changes password and logs in with the new one."""
        from portal.db import get_db
        from portal.security import hash_password

        # Set initial password (student_client fixture already logged in with testpass123!)
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (hash_password("oldpass123!"), "101"),
            )
            conn.commit()
        finally:
            conn.close()

        # Change password using the SESSION (still valid from fixture login)
        resp = student_client.post("/change-password", data={
            "old_password": "oldpass123!",
            "new_password": "newpass123!",
            "confirm_password": "newpass123!",
        })
        assert resp.status_code == 302, f"Expected 302 redirect, got {resp.status_code}"

        # Login with old password should fail
        resp = student_client.post("/login", data={
            "username": "101",
            "password": "oldpass123!",
        })
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

        # Login with new password should succeed
        resp = student_client.post("/login", data={
            "username": "101",
            "password": "newpass123!",
        })
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"

        # Reset password back for other tests
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (hash_password("testpass123!"), "101"),
            )
            conn.commit()
        finally:
            conn.close()

    def test_admin_creates_user_and_user_can_login(self, admin_client):
        """Admin creates a user and that user can log in."""
        from portal.db import get_db
        from portal.security import hash_password

        # Ensure admin has known password
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (hash_password("testpass123!"), "admin"),
            )
            conn.commit()
        finally:
            conn.close()

        # Create a new teacher user
        resp = admin_client.post("/admin/create-user", data={
            "username": "T999",
            "password": "NewTeacher123!",
            "role": "teacher",
            "full_name": "Test Teacher",
            "email": "test@cse.univ.edu",
            "branch": "CSE",
            "phone": "9811199999",
        })
        assert resp.status_code == 200

        # Log in as the new user
        resp = admin_client.post("/login", data={
            "username": "T999",
            "password": "NewTeacher123!",
        })
        assert resp.status_code == 302
