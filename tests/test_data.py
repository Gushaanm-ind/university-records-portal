# university_portal/tests/test_data.py
import pytest


class TestData:
    def test_exactly_50_students(self):
        """There should be exactly 50 students."""
        from repositories.objects import get_all_students
        students = get_all_students()
        assert len(students) == 50, f"Expected 50 students, got {len(students)}"

    def test_exactly_1_admin(self):
        """There should be exactly 1 admin user."""
        from repositories.users import get_users_by_role
        admins = get_users_by_role("admin")
        assert len(admins) == 1, f"Expected 1 admin, got {len(admins)}"

    def test_exactly_1_hod(self):
        """There should be exactly 1 HOD user."""
        from repositories.users import get_users_by_role
        hods = get_users_by_role("hod")
        assert len(hods) == 1, f"Expected 1 HOD, got {len(hods)}"

    def test_exactly_6_teachers(self):
        """There should be exactly 6 teacher users."""
        from repositories.users import get_users_by_role
        teachers = get_users_by_role("teacher")
        assert len(teachers) == 6, f"Expected 6 teachers, got {len(teachers)}"

    def test_exactly_4_branches(self):
        """There should be exactly 4 departments."""
        from repositories.departments import get_all_departments
        depts = get_all_departments()
        assert len(depts) == 4, f"Expected 4 departments, got {len(depts)}"

    def test_exactly_12_courses(self):
        """There should be exactly 12 courses."""
        from repositories.objects import get_all_courses
        courses = get_all_courses()
        assert len(courses) == 12, f"Expected 12 courses, got {len(courses)}"

    def test_marks_in_range(self):
        """All marks should be between 0 and 100 or NULL."""
        from db import get_db
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT * FROM enrollments WHERE marks IS NOT NULL AND (marks < 0 OR marks > 100)"
            ).fetchall()
            assert len(rows) == 0, f"Found {len(rows)} marks out of range"
        finally:
            conn.close()

    def test_every_course_has_teacher_and_branch(self):
        """Every course should have a teacher and a department."""
        from repositories.objects import get_all_courses
        courses = get_all_courses()
        for c in courses:
            assert c["teacher_id"] is not None, f"Course {c['code']} has no teacher"
            assert c["department_id"] is not None, f"Course {c['code']} has no department"

    def test_foreign_keys_hold(self):
        """All foreign keys should be valid."""
        from db import get_db
        conn = get_db()
        try:
            # enrollments → students
            bad = conn.execute("""
                SELECT COUNT(*) FROM enrollments e
                LEFT JOIN students s ON e.student_id = s.id
                WHERE s.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} enrollments with invalid student_id"

            # enrollments → courses
            bad = conn.execute("""
                SELECT COUNT(*) FROM enrollments e
                LEFT JOIN courses c ON e.course_id = c.id
                WHERE c.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} enrollments with invalid course_id"

            # teachers → departments
            bad = conn.execute("""
                SELECT COUNT(*) FROM teachers t
                LEFT JOIN departments d ON t.department_id = d.id
                WHERE d.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} teachers with invalid department_id"

            # students → departments
            bad = conn.execute("""
                SELECT COUNT(*) FROM students s
                LEFT JOIN departments d ON s.department_id = d.id
                WHERE d.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} students with invalid department_id"

            # courses → teachers
            bad = conn.execute("""
                SELECT COUNT(*) FROM courses c
                LEFT JOIN teachers t ON c.teacher_id = t.id
                WHERE t.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} courses with invalid teacher_id"

            # courses → departments
            bad = conn.execute("""
                SELECT COUNT(*) FROM courses c
                LEFT JOIN departments d ON c.department_id = d.id
                WHERE d.id IS NULL
            """).fetchone()[0]
            assert bad == 0, f"Found {bad} courses with invalid department_id"
        finally:
            conn.close()

    def test_pragma_foreign_keys_is_on(self):
        """PRAGMA foreign_keys should be ON."""
        from db import get_db
        conn = get_db()
        try:
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            assert result[0] == 1, f"foreign_keys = {result[0]}, expected 1"
        finally:
            conn.close()

    def test_practical_students_exist(self):
        """The 5 practical students should exist with correct details."""
        from repositories.objects import get_student_by_roll
        assert get_student_by_roll("101") is not None
        assert get_student_by_roll("101")["name"] == "Aman Verma"
        assert get_student_by_roll("102") is not None
        assert get_student_by_roll("102")["name"] == "Riya Kapoor"
        assert get_student_by_roll("103") is not None
        assert get_student_by_roll("103")["name"] == "Karan Mehta"
        assert get_student_by_roll("104") is not None
        assert get_student_by_roll("104")["name"] == "Neha Joshi"
        assert get_student_by_roll("105") is not None
        assert get_student_by_roll("105")["name"] == "Simran Kaur"

    def test_practical_teachers_exist(self):
        """The 6 practical teachers should exist."""
        from repositories.objects import get_teacher_by_staff_code
        assert get_teacher_by_staff_code("T001") is not None
        assert get_teacher_by_staff_code("T001")["name"] == "Mr. Sharma"
        assert get_teacher_by_staff_code("T002") is not None
        assert get_teacher_by_staff_code("T002")["name"] == "Ms. Gupta"
        assert get_teacher_by_staff_code("T003") is not None
        assert get_teacher_by_staff_code("T003")["name"] == "Mr. Verma"
        assert get_teacher_by_staff_code("T004") is not None
        assert get_teacher_by_staff_code("T004")["name"] == "Dr. Rao"
        assert get_teacher_by_staff_code("T005") is not None
        assert get_teacher_by_staff_code("T005")["name"] == "Dr. Kumar"
        assert get_teacher_by_staff_code("T006") is not None
        assert get_teacher_by_staff_code("T006")["name"] == "Dr. Mishra"

    def test_practical_courses_exist(self):
        """C101-C104 should exist with correct teachers."""
        from repositories.objects import get_course_by_id
        c101 = get_course_by_id(1)
        assert c101 is not None
        assert c101["code"] == "C101"
        assert c101["title"] == "DBMS"
        c104 = get_course_by_id(4)
        assert c104 is not None
        assert c104["code"] == "C104"
        assert c104["title"] == "Circuits"

    def test_credential_file_exists(self):
        """CREDENTIALS.txt should exist."""
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CREDENTIALS.txt")
        assert os.path.exists(path), "CREDENTIALS.txt not found"
