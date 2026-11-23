# university_portal/tests/test_login_history.py
"""
login_history should contain sign-in attempts only, each labelled correctly,
and every audit row should name the account that acted.
"""
from db import get_db
from repositories.audit import get_audit_logs, get_login_history


def _history(username):
    return [r for r in get_login_history({"username": username})]


def test_successful_login_is_recorded_as_success(client):
    client.post("/login", data={"username": "101", "password": "testpass123!"},
                follow_redirects=True)
    rows = _history("101")
    assert rows, "successful login was not written to login_history"
    assert all(row["success"] == 1 for row in rows)


def test_failed_login_is_recorded_as_failure(client):
    client.post("/login", data={"username": "101", "password": "wrong-password"})
    rows = _history("101")
    assert rows, "failed attempt was not written to login_history"
    assert all(row["success"] == 0 for row in rows)


def test_logout_does_not_create_a_login_row(client):
    client.post("/login", data={"username": "101", "password": "testpass123!"},
                follow_redirects=True)
    before = len(_history("101"))
    client.get("/logout")
    after = _history("101")
    assert len(after) == before
    # A logout is an audit event, not a failed login.
    assert all(row["success"] == 1 for row in after)


def test_logout_writes_audit_entry(client):
    client.post("/login", data={"username": "101", "password": "testpass123!"},
                follow_redirects=True)
    client.get("/logout")
    logouts = [r for r in get_audit_logs() if r["action"] == "LOGOUT"]
    assert logouts
    assert logouts[-1]["actor_username"] == "101"


def test_audit_rows_name_the_actor(client):
    client.post("/login", data={"username": "T001", "password": "testpass123!"},
                follow_redirects=True)
    logins = [
        r for r in get_audit_logs()
        if r["action"] == "LOGIN_SUCCESS" and r["target_label"] == "T001"
    ]
    assert logins, "no LOGIN_SUCCESS audit row for T001"
    row = logins[-1]
    assert row["actor_username"] == "T001"
    assert row["actor_role"] == "teacher"


def test_unknown_username_keeps_an_empty_actor(client):
    client.post("/login", data={"username": "ghost", "password": "whatever1!"})
    rows = [
        r for r in get_audit_logs()
        if r["action"] == "LOGIN_FAILED" and r["target_label"] == "ghost"
    ]
    assert rows
    # No account exists, so there is no username or role to record.
    assert rows[-1]["actor_username"] == ""
    assert rows[-1]["actor_role"] == ""


def test_history_keeps_the_ip_address(client):
    client.post("/login", data={"username": "101", "password": "testpass123!"},
                follow_redirects=True)
    assert _history("101")[-1]["ip_address"] is not None


def test_two_accounts_do_not_mix_their_history(client):
    client.post("/login", data={"username": "101", "password": "testpass123!"},
                follow_redirects=True)
    client.get("/logout")
    client.post("/login", data={"username": "102", "password": "testpass123!"},
                follow_redirects=True)

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, success FROM login_history ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    assert [(r[0], r[1]) for r in rows] == [("101", 1), ("102", 1)]
