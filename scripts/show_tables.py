#!/usr/bin/env python3
# university_portal/scripts/show_tables.py
"""
Print the university database in the terminal, laid out like the tables in the
DBMS practical manual.

Usage (from the project root, with the venv active):

    python scripts/show_tables.py                 # department, teacher, student, course, enrollment
    python scripts/show_tables.py --list          # every table name + row count
    python scripts/show_tables.py --schema        # the CREATE TABLE statements
    python scripts/show_tables.py --table users   # any single table
    python scripts/show_tables.py --sql "SELECT ..."
    python scripts/show_tables.py --limit 10      # cap rows of --table / --sql

Only the Python standard library is used, so no extra install and no sqlite3
command-line client is needed.
"""
import argparse
import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# config.py exits when PORTAL_FERNET_KEY is missing, and the SQLite viewer never
# decrypts anything, so read the database path directly instead of importing it.
DB_PATH = os.environ.get("PORTAL_DB") or os.path.join(PROJECT_ROOT, "university.db")

# DB_ENGINE=mysql reads the same tables from the configured MySQL server.
ENGINE = (os.environ.get("DB_ENGINE") or "sqlite").strip().lower()
ROLL_ORDER = "CAST(s.roll_no AS SIGNED)" if ENGINE == "mysql" else "CAST(s.roll_no AS INTEGER)"


def target_label():
    if ENGINE == "mysql":
        user = os.environ.get("MYSQL_USER", "portal")
        host = os.environ.get("MYSQL_HOST", "127.0.0.1")
        port = os.environ.get("MYSQL_PORT", "3306")
        database = os.environ.get("MYSQL_DATABASE", "university_db")
        return f"{user}@{host}:{port}/{database} (MySQL)"
    return os.path.abspath(DB_PATH)

# The five tables from the practical (Experiment 5, 3NF).
# (heading in the manual, SQL query)
MANUAL_TABLES = [
    (
        "department",
        "SELECT code AS dept_code, name AS dept_name FROM departments ORDER BY code",
    ),
    (
        "teacher",
        """SELECT t.staff_code, t.name AS teacher_name, d.code AS dept_code, t.email
             FROM teachers t JOIN departments d ON d.id = t.department_id
            ORDER BY t.staff_code""",
    ),
    (
        "student",
        f"""SELECT s.roll_no, s.name AS student_name, d.code AS dept_code, s.email
              FROM students s JOIN departments d ON d.id = s.department_id
             ORDER BY {ROLL_ORDER}""",
    ),
    (
        "course",
        """SELECT c.code AS course_id, c.title AS course_name, c.credits,
                  t.name AS teacher_name, d.code AS dept_code
             FROM courses c
             JOIN teachers t ON t.id = c.teacher_id
             JOIN departments d ON d.id = c.department_id
            ORDER BY c.code""",
    ),
    (
        "enrollment",
        f"""SELECT s.roll_no, e.course_id, c.code AS course_code, e.marks
              FROM enrollments e
              JOIN students s ON s.id = e.student_id
              JOIN courses c ON c.id = e.course_id
             ORDER BY {ROLL_ORDER}, c.code""",
    ),
]

# Values never printed in clear text, even though this is a local demo DB.
MASKED_COLUMNS = {"national_id_enc", "password_hash"}


def connect():
    if ENGINE == "mysql":
        # Running this file as a script puts scripts/ on sys.path, not the project.
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        from portal.db import get_db

        return get_db()
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}\nRun: python scripts/seed.py")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def quote(name):
    return f"`{name}`" if ENGINE == "mysql" else f'"{name}"'


def table_names(conn):
    if ENGINE == "mysql":
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() ORDER BY table_name"
        ).fetchall()
        return [row[0] for row in rows]
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def create_statements(conn):
    if ENGINE == "mysql":
        return [conn.execute(f"SHOW CREATE TABLE {quote(name)}").fetchone()[1]
                for name in table_names(conn)]
    return [row[0] for row in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]


def render(headers, rows):
    """Draw an ASCII box table (same shape as the manual's output tables)."""
    body = [[cell(value, header) for header, value in zip(headers, row)] for row in rows]
    widths = [len(head) for head in headers]
    for line in body:
        widths = [max(width, len(value)) for width, value in zip(widths, line)]

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    out = [border]
    out.append("|" + "|".join(f" {head:<{w}} " for head, w in zip(headers, widths)) + "|")
    out.append(border)
    for line in body:
        out.append("|" + "|".join(f" {value:<{w}} " for value, w in zip(line, widths)) + "|")
    if not body:
        out.append("|" + "|".join(f" {'(no rows)':<{w}} " if i == 0 else " " * (w + 2)
                                  for i, w in enumerate(widths)) + "|")
    out.append(border)
    return "\n".join(out)


def cell(value, column):
    """Plain-text value: masked secrets, NULL and BLOBs made readable."""
    if value is None:
        return "NULL"
    if column in MASKED_COLUMNS:
        return "(encrypted)" if column == "national_id_enc" else "(hash)"
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    return str(value)


def show_query(conn, title, sql, limit=None, footer=True):
    cursor = conn.execute(sql)
    headers = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    total = len(rows)
    if limit is not None:
        rows = rows[:limit]
    print(f"\n{title}")
    print("=" * len(title))
    print(render(headers, rows))
    if footer:
        count = total if limit is None or total <= limit else f"{len(rows)} of {total}"
        noun = "row" if count in (1, "1") else "rows"
        print(f"{count} {noun}")


def main():
    parser = argparse.ArgumentParser(description="Show the university database as terminal tables.")
    parser.add_argument("--table", help="print one table by name")
    parser.add_argument("--sql", help="run a read-only SELECT and print the result")
    parser.add_argument("--list", action="store_true", help="table names and row counts")
    parser.add_argument("--schema", action="store_true", help="CREATE TABLE statements")
    parser.add_argument("--limit", type=int, default=None, help="max rows to print")
    args = parser.parse_args()

    conn = connect()
    try:
        if args.list:
            label = target_label()
            print(f"\nTables in {label}")
            print("=" * (len(label) + 11))
            rows = [[name, conn.execute(f"SELECT COUNT(*) FROM {quote(name)}").fetchone()[0]]
                    for name in table_names(conn)]
            print(render(["table", "rows"], rows))
            return

        if args.schema:
            label = target_label()
            print(f"\nSchema of {label}")
            print("=" * (len(label) + 11))
            for statement in create_statements(conn):
                print(f"\n{statement};")
            return

        if args.sql:
            if not args.sql.lstrip().lower().startswith(
                ("select", "with", "pragma", "show", "describe")
            ):
                sys.exit("--sql only runs read-only queries (SELECT / WITH / SHOW / DESCRIBE).")
            show_query(conn, "query result", args.sql, limit=args.limit)
            return

        if args.table:
            if args.table not in table_names(conn):
                sys.exit(f"No table called {args.table!r}. Try --list.")
            show_query(conn, args.table, f"SELECT * FROM {quote(args.table)}", limit=args.limit)
            return

        print(f"\nUniversity database: {target_label()}")
        counts = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        print(f"{counts} students. Tables from Experiment 5 of the practical:")
        for title, sql in MANUAL_TABLES:
            show_query(conn, title, sql, limit=args.limit)
        print("\nMore: --list  --schema  --table users  --sql \"SELECT ...\"")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
