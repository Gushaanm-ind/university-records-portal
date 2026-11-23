# university_portal/tests/test_tamper.py
"""
A student requesting another student's record gets 403.
A student or teacher posting an edit gets 403.
Every denied attempt is logged as ACCESS_DENIED.
"""
import pytest


class TestTamper:
    def test_student_cannot_view_other_student(self, student_client):
        resp = student_client.get("/student/2")
        assert resp.status_code == 403

    def test_student_cannot_view_teacher_index(self, student_client):
        resp = student_client.get("/teacher")
        assert resp.status_code == 403

    def test_student_cannot_view_hod_index(self, student_client):
        resp = student_client.get("/hod")
        assert resp.status_code == 403

    def test_student_cannot_view_admin_index(self, student_client):
        resp = student_client.get("/admin")
        assert resp.status_code == 403

    def test_student_cannot_post_edit_student(self, student_client):
        resp = student_client.post("/hod/student/1", data={"name": "Hacked", "email": "x@x.com"})
        assert resp.status_code == 403

    def test_student_cannot_post_admin_student(self, student_client):
        resp = student_client.post("/admin/student/1", data={"name": "Hacked", "email": "x@x.com"})
        assert resp.status_code == 403

    def test_student_cannot_post_national_id(self, student_client):
        resp = student_client.post("/admin/national-id/1")
        assert resp.status_code == 403

    def test_teacher_cannot_post_edit_student(self, teacher_client):
        resp = teacher_client.post("/hod/student/1", data={"name": "Hacked", "email": "x@x.com"})
        assert resp.status_code == 403

    def test_teacher_cannot_post_admin_student(self, teacher_client):
        resp = teacher_client.post("/admin/student/1", data={"name": "Hacked", "email": "x@x.com"})
        assert resp.status_code == 403

    def test_teacher_cannot_post_course_marks(self, teacher_client):
        resp = teacher_client.post("/hod/course/1", data={"marks_101": "99"})
        assert resp.status_code == 403

    def test_hod_cannot_post_admin_student(self, hod_client):
        resp = hod_client.post("/admin/student/1", data={"name": "Hacked", "email": "x@x.com"})
        assert resp.status_code == 403

    def test_hod_cannot_post_admin_national_id(self, hod_client):
        resp = hod_client.post("/admin/national-id/1")
        assert resp.status_code == 403

    def test_access_denied_audit_logged(self, app, db_file):
        """Verify ACCESS_DENIED is written to audit_log when a student is blocked."""
        from portal.repositories.audit import get_audit_logs

        c = app.test_client()
        c.post("/login", data={"username": "101", "password": "testpass123!"})

        # A student poking at the admin area must be blocked and recorded.
        resp = c.get("/admin/students")
        assert resp.status_code == 403

        logs = get_audit_logs({"action": "ACCESS_DENIED"})
        assert len(logs) > 0, "No ACCESS_DENIED audit entries found"
        assert logs[0]["actor_username"] in ("", "101")
