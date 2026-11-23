# university_portal/tests/test_reports.py
import pytest


class TestReports:
    def test_avg_marks_per_branch_returns_data(self, admin_client):
        """Reports should return average marks per branch."""
        from services.reports import avg_marks_per_branch
        data = avg_marks_per_branch()
        assert len(data) == 4, f"Expected 4 branches, got {len(data)}"
        for row in data:
            assert row["branch_code"] in ("CSE", "ECE", "ME", "CE")

    def test_students_above_branch_average(self, admin_client):
        """Students above branch average report should work."""
        from services.reports import students_above_branch_average
        data = students_above_branch_average()
        # May be empty if no students above average, but should not error
        assert isinstance(data, list)

    def test_courses_with_highest_average(self, admin_client):
        """Courses with highest average report should work."""
        from services.reports import courses_with_highest_average
        data = courses_with_highest_average()
        assert isinstance(data, list)

    def test_second_highest_mark(self, admin_client):
        """Second highest mark report should work."""
        from services.reports import second_highest_mark
        val = second_highest_mark()
        # May be None if not enough data, but should not error
        assert val is None or (isinstance(val, int) and 0 <= val <= 100)

    def test_students_above_overall_average(self, admin_client):
        """Students above overall average report should work."""
        from services.reports import students_above_overall_average
        data = students_above_overall_average()
        assert isinstance(data, list)

    def test_practical_query_2_group_by(self, admin_client):
        """Verify the Practical 2 Query 2 equivalent: GROUP BY with LEFT JOIN."""
        from db import get_db
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT d.code, COUNT(e.student_id), ROUND(AVG(e.marks), 2)
                FROM departments d
                LEFT JOIN students s ON s.department_id = d.id
                LEFT JOIN enrollments e ON e.student_id = s.id
                GROUP BY d.code
                ORDER BY d.code
            """).fetchall()
            assert len(rows) == 4
            for row in rows:
                assert row[0] in ("CSE", "ECE", "ME", "CE")
        finally:
            conn.close()

    def test_practical_query_5_subquery(self, admin_client):
        """Verify the Practical 2 Query 5 equivalent: subquery for above-average."""
        from db import get_db
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT s.name, e.marks
                FROM enrollments e
                JOIN students s ON e.student_id = s.id
                WHERE e.marks IS NOT NULL
                  AND e.marks > (SELECT AVG(marks) FROM enrollments WHERE marks IS NOT NULL)
                ORDER BY e.marks DESC
            """).fetchall()
            assert isinstance(rows, list)
        finally:
            conn.close()

    def test_practical_query_7_second_highest(self, admin_client):
        """Verify the Practical 2 Query 7 equivalent: second highest mark."""
        from db import get_db
        conn = get_db()
        try:
            row = conn.execute("""
                SELECT MAX(marks) FROM enrollments
                WHERE marks IS NOT NULL
                  AND marks < (SELECT MAX(marks) FROM enrollments WHERE marks IS NOT NULL)
            """).fetchone()
            val = row[0]
            assert val is None or (isinstance(val, int) and 0 <= val <= 100)
        finally:
            conn.close()
