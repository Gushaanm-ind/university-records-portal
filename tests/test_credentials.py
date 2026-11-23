# university_portal/tests/test_credentials.py
"""
CREDENTIALS.txt must always describe the database that actually exists.

These tests cover the shared writer in credentials.py, which both seed.py and
set_demo_passwords.py use, so the two files cannot drift apart again.
"""
import os

from credentials import (
    NOT_RECORDED,
    parse_credentials_file,
    verify_credentials_file,
    write_credentials_file,
)
from db import get_db

# conftest gives every account in the test database this one password.
TEST_PASSWORD = "testpass123!"


def _demo_map(conn):
    """The password map that actually matches the test database."""
    rows = conn.execute("SELECT username FROM users").fetchall()
    return {row["username"]: TEST_PASSWORD for row in rows}


def _write(db_file, tmp_path, passwords=None):
    conn = get_db()
    try:
        mapping = passwords if passwords is not None else _demo_map(conn)
        path = os.path.join(str(tmp_path), "CREDENTIALS.txt")
        write_credentials_file(mapping, conn=conn, path=path)
    finally:
        conn.close()
    return path


def test_file_lists_every_account(db_file, tmp_path):
    conn = get_db()
    usernames = {row["username"] for row in conn.execute("SELECT username FROM users")}
    conn.close()

    path = _write(db_file, tmp_path)
    listed = {username for username, _password in parse_credentials_file(path)}

    assert listed == usernames
    assert "admin" in listed and "hod" in listed
    assert "T001" in listed and "101" in listed and "150" in listed


def test_header_counts_come_from_the_database(db_file, tmp_path):
    conn = get_db()
    counts = {
        row["role"]: row["n"]
        for row in conn.execute(
            "SELECT role, COUNT(*) AS n FROM users GROUP BY role"
        )
    }
    conn.close()

    path = _write(db_file, tmp_path)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    assert (
        f"Accounts: {sum(counts.values())} users "
        f"({counts['admin']} admin, {counts['hod']} HOD, "
        f"{counts['teacher']} teachers, {counts['student']} students)"
    ) in text
    assert "Generated:" in text


def test_written_passwords_verify_against_the_database(db_file, tmp_path):
    path = _write(db_file, tmp_path)
    ok, problems = verify_credentials_file(path)
    assert ok, problems


def test_verify_detects_a_wrong_password(db_file, tmp_path):
    path = _write(db_file, tmp_path)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    tampered = text.replace("password: testpass123!", "password: WrongPass1!")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(tampered)

    ok, problems = verify_credentials_file(path)
    assert not ok
    assert any("admin" in problem for problem in problems)


def test_verify_detects_a_missing_account(db_file, tmp_path):
    path = _write(db_file, tmp_path)
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    # Drop the login-history student line (roll 150) from the file.
    kept = [line for line in lines if "roll: 150 |" not in line]
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(kept)

    ok, problems = verify_credentials_file(path)
    assert not ok
    assert any("150" in problem for problem in problems)


def test_unrecorded_password_is_flagged_not_invented(db_file, tmp_path):
    conn = get_db()
    mapping = _demo_map(conn)
    conn.close()

    path = _write(db_file, tmp_path, passwords={})
    with open(path, encoding="utf-8") as handle:
        assert NOT_RECORDED in handle.read()

    ok, problems = verify_credentials_file(path)
    assert not ok
    assert problems  # every account is reported, none silently accepted
