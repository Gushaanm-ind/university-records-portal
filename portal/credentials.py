#!/usr/bin/env python3
"""
Single writer and checker for CREDENTIALS.txt.

Both scripts/seed.py and scripts/set_demo_passwords.py go through
write_credentials_file(), so
the file can never drift from the database: accounts, names, branches and the
headline counts are all read from the live tables, and the file records when it
was generated.

Passwords are not stored in the clear anywhere in the database, so the caller
supplies the plain-text passwords it just wrote. Any account missing from that
mapping still appears in the file, marked as not recorded, instead of silently
disappearing.
"""
import os
import re
from datetime import datetime, timezone

# CREDENTIALS.txt lives in the project root, one level above this package.
DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CREDENTIALS.txt"
)

# Roll numbers are TEXT; sort them numerically on either engine.
def _roll_order(engine_name):
    return "CAST(s.roll_no AS SIGNED)" if engine_name == "mysql" else "CAST(s.roll_no AS INTEGER)"

NOT_RECORDED = "(not recorded)"

USERNAME_RE = re.compile(r"username:\s*(\S+)")
PASSWORD_RE = re.compile(r"password:\s*(\S+)")


def _fetch(conn, sql):
    return conn.execute(sql).fetchall()


def _section(lines, title):
    lines.append(title)
    lines.append("-" * 40)


def write_credentials_file(passwords, conn=None, path=None):
    """Rewrite CREDENTIALS.txt from the current database contents.

    passwords: dict of username -> plain-text password.
    conn:      optional open sqlite3 connection (one is opened if omitted).
    path:      optional output path (defaults to CREDENTIALS.txt in the project root).
    """
    from portal.db import get_db, engine

    path = path or DEFAULT_PATH
    own_connection = conn is None
    if own_connection:
        conn = get_db()
    roll_order = _roll_order(engine())
    try:
        admins = _fetch(
            conn,
            """SELECT username FROM users
                WHERE role = 'admin' ORDER BY username""",
        )
        hods = _fetch(
            conn,
            """SELECT username FROM users
                WHERE role = 'hod' ORDER BY username""",
        )
        teachers = _fetch(
            conn,
            """SELECT u.username, t.staff_code, t.name, d.code AS branch
                 FROM users u
                 JOIN teachers t ON t.id = u.teacher_id
                 JOIN departments d ON d.id = t.department_id
                WHERE u.role = 'teacher'
                ORDER BY t.staff_code""",
        )
        students = _fetch(
            conn,
            """SELECT u.username, s.roll_no, s.name, d.code AS branch
                 FROM users u
                 JOIN students s ON s.id = u.student_id
                 JOIN departments d ON d.id = s.department_id
                WHERE u.role = 'student'
                ORDER BY d.code, {roll_order}""".format(roll_order=roll_order),
        )
        # Any account the joins above did not reach still gets listed, so the
        # file always covers every row in users.
        listed = (
            {r["username"] for r in admins}
            | {r["username"] for r in hods}
            | {r["username"] for r in teachers}
            | {r["username"] for r in students}
        )
        all_users = _fetch(conn, "SELECT username, role FROM users ORDER BY username")
        orphans = [u for u in all_users if u["username"] not in listed]
        total = len(all_users)
    finally:
        if own_connection:
            conn.close()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        from portal.config import Config

        if engine() == "mysql":
            database_label = f"{Config.MYSQL_DATABASE} (MySQL)"
        else:
            database_label = os.path.basename(Config.DATABASE)
    except Exception:  # pragma: no cover - label only
        database_label = "university.db"

    lines = []
    lines.append("DEMO ACCOUNTS. Passwords are shown in plain text for testing only.")
    lines.append("Delete this file before any real use. The database stores only hashes.")
    lines.append(f"Generated: {generated} from {database_label}")
    lines.append(
        f"Accounts: {total} users "
        f"({len(admins)} admin, {len(hods)} HOD, {len(teachers)} teachers, "
        f"{len(students)} students)"
    )
    lines.append("=" * 70)
    lines.append("")

    _section(lines, f"Admin ({len(admins)})")
    for row in admins:
        lines.append(f"  username: {row['username']}")
        lines.append("  role: admin")
        lines.append(f"  password: {passwords.get(row['username'], NOT_RECORDED)}")
        lines.append("")

    _section(lines, f"HOD ({len(hods)})")
    for row in hods:
        lines.append(f"  username: {row['username']}")
        lines.append("  role: hod")
        lines.append(f"  password: {passwords.get(row['username'], NOT_RECORDED)}")
        lines.append("")

    _section(lines, f"Teachers ({len(teachers)})")
    for row in teachers:
        lines.append(f"  username: {row['username']}")
        lines.append("  role: teacher")
        lines.append(f"  name: {row['name']}")
        lines.append(f"  branch: {row['branch']}")
        lines.append(f"  staff_code: {row['staff_code']}")
        lines.append(f"  password: {passwords.get(row['username'], NOT_RECORDED)}")
        lines.append("")

    _section(lines, f"Students ({len(students)}, grouped by branch)")
    current_branch = None
    for row in students:
        if row["branch"] != current_branch:
            if current_branch is not None:
                lines.append("")
            current_branch = row["branch"]
            lines.append(f"  Branch: {current_branch}")
        lines.append(
            f"    roll: {row['roll_no']} | name: {row['name']} | "
            f"username: {row['username']} | "
            f"password: {passwords.get(row['username'], NOT_RECORDED)}"
        )
    lines.append("")

    if orphans:
        _section(lines, f"Other accounts ({len(orphans)}) - no linked student or teacher record")
        for row in orphans:
            lines.append(f"  username: {row['username']}")
            lines.append(f"  role: {row['role']}")
            lines.append(f"  password: {passwords.get(row['username'], NOT_RECORDED)}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return path


def parse_credentials_file(path=None):
    """Return [(username, password), ...] read back from CREDENTIALS.txt."""
    path = path or DEFAULT_PATH
    pairs = []
    pending = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            username = USERNAME_RE.search(line)
            if username:
                pending = username.group(1)
            password = PASSWORD_RE.search(line)
            if password and pending is not None:
                pairs.append((pending, password.group(1)))
                pending = None
    return pairs


def verify_credentials_file(path=None):
    """Check every account in CREDENTIALS.txt against the live database.

    Returns (ok, problems): problems is a list of human-readable strings.
    """
    from portal.db import get_db
    from portal.security import verify_password

    path = path or DEFAULT_PATH
    pairs = parse_credentials_file(path)
    problems = []

    conn = get_db()
    try:
        stored = {
            row["username"]: row
            for row in conn.execute(
                "SELECT username, role, password_hash, is_active FROM users"
            ).fetchall()
        }
    finally:
        conn.close()

    seen = set()
    for username, password in pairs:
        seen.add(username)
        row = stored.get(username)
        if row is None:
            problems.append(f"{username}: listed in CREDENTIALS.txt but not in the database")
            continue
        if password == NOT_RECORDED:
            problems.append(f"{username}: password not recorded in CREDENTIALS.txt")
            continue
        if not verify_password(row["password_hash"], password):
            problems.append(
                f"{username}: password in CREDENTIALS.txt does not match the stored hash"
            )
        elif not row["is_active"]:
            problems.append(f"{username}: password is correct but the account is deactivated")

    for username in stored:
        if username not in seen:
            problems.append(f"{username}: in the database but missing from CREDENTIALS.txt")

    return (not problems), problems
