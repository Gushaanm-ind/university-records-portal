# university_portal/services/reports.py
from portal.db import get_db


def avg_marks_per_branch():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT d.code AS branch_code, d.name AS branch_name,
                   COUNT(e.student_id) AS enrolment_count,
                   ROUND(AVG(e.marks), 2) AS avg_marks
            FROM departments d
            LEFT JOIN students s ON s.department_id = d.id
            LEFT JOIN enrollments e ON e.student_id = s.id
            GROUP BY d.code, d.name
            ORDER BY d.code
        """).fetchall()
        return rows
    finally:
        conn.close()


def students_above_branch_average():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.roll_no, s.name, d.code AS branch, c.code AS course_code,
                   e.marks,
                   (SELECT ROUND(AVG(e2.marks),2)
                    FROM enrollments e2
                    JOIN students s2 ON e2.student_id = s2.id
                    WHERE s2.department_id = d.id
                      AND e2.marks IS NOT NULL
                   ) AS branch_avg
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.marks IS NOT NULL
              AND e.marks > (
                  SELECT AVG(e3.marks)
                  FROM enrollments e3
                  JOIN students s3 ON e3.student_id = s3.id
                  WHERE s3.department_id = d.id
                    AND e3.marks IS NOT NULL
              )
            ORDER BY d.code, s.roll_no, c.code
        """).fetchall()
        return rows
    finally:
        conn.close()


def courses_with_highest_average():
    conn = get_db()
    try:
        max_avg = conn.execute("""
            SELECT MAX(avg_marks) FROM (
                SELECT AVG(marks) AS avg_marks
                FROM enrollments
                WHERE marks IS NOT NULL
                GROUP BY course_id
            ) AS per_course""").fetchone()[0]
        if max_avg is None:
            return []

        rows = conn.execute("""
            SELECT c.code AS course_code, c.title,
                   ROUND(AVG(e.marks), 2) AS avg_marks,
                   COUNT(e.student_id) AS enrolment_count
            FROM courses c
            JOIN enrollments e ON e.course_id = c.id
            WHERE e.marks IS NOT NULL
            GROUP BY c.id
            HAVING AVG(e.marks) = ?
            ORDER BY c.code
        """, (max_avg,)).fetchall()
        return rows
    finally:
        conn.close()


def second_highest_mark():
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT MAX(marks) AS second_highest
            FROM enrollments
            WHERE marks IS NOT NULL
              AND marks < (
                  SELECT MAX(marks)
                  FROM enrollments
                  WHERE marks IS NOT NULL
              )
        """).fetchone()
        return row["second_highest"]
    finally:
        conn.close()


def second_highest_mark_student_course():
    second = second_highest_mark()
    if second is None:
        return None
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT s.roll_no, s.name, c.code AS course_code, c.title, e.marks
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.marks = ?
            LIMIT 1
        """, (second,)).fetchone()
        return row
    finally:
        conn.close()


def students_above_overall_average():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.roll_no, s.name, d.code AS branch, c.code AS course_code,
                   e.marks,
                   (SELECT ROUND(AVG(marks),2) FROM enrollments WHERE marks IS NOT NULL)
                   AS overall_avg
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.marks IS NOT NULL
              AND e.marks > (SELECT AVG(marks) FROM enrollments WHERE marks IS NOT NULL)
            ORDER BY s.roll_no, c.code
        """).fetchall()
        return rows
    finally:
        conn.close()
