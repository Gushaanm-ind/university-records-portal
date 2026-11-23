# university_portal/blueprints/auth.py
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from portal.db import get_db
from portal.security import hash_password, verify_password, meets_password_policy
from portal.repositories.users import get_user_by_username, update_last_login, increment_failed_attempts, get_user_by_id, lock_account, reset_failed_attempts
from portal.audit import write_audit
from portal.services import presence

auth_bp = Blueprint("auth", __name__)


def _record_login(username, success):
    """Append one row to login_history: a sign-in that worked, or one that did not."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO login_history (username, logged_in_at, success, ip_address)"
            " VALUES (?,?,?,?)",
            (
                username,
                datetime.datetime.utcnow().isoformat(),
                1 if success else 0,
                request.remote_addr or "",
            ),
        )
        conn.commit()
    finally:
        conn.close()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "")

    if not username or not password:
        return render_template("auth/login.html",
                               error="Username and password are required"), 400

    user = get_user_by_username(username)

    if user is None:
        write_audit(actor_id=0, action="LOGIN_FAILED", target_type="user",
                    target_label=username, ip_address=request.remote_addr or "")
        _record_login(username, success=False)
        return render_template("auth/login.html",
                               error="Invalid username or password. "
                                     "If you are locked out, wait 15 minutes and try again."
                               ), 401

    if user["locked_until"]:
        try:
            lock_until = datetime.datetime.fromisoformat(user["locked_until"])
            if datetime.datetime.utcnow() < lock_until:
                write_audit(actor_id=user["id"], action="LOGIN_FAILED",
                            target_type="user", target_id=user["id"],
                            target_label=username,
                            ip_address=request.remote_addr or "")
                _record_login(username, success=False)
                return render_template("auth/login.html",
                                       error=f"Account locked until {user['locked_until']}. "
                                             "Wait and try again."
                                      ), 423
        except (ValueError, TypeError):
            pass

    if not verify_password(user["password_hash"], password):
        write_audit(actor_id=user["id"], action="LOGIN_FAILED",
                    target_type="user", target_id=user["id"],
                    target_label=username,
                    ip_address=request.remote_addr or "")
        _record_login(username, success=False)
        increment_failed_attempts(user["id"])
        u = get_user_by_id(user["id"])
        if u and u["failed_attempts"] >= 5:
            lock_account(user["id"])
            write_audit(actor_id=user["id"], action="ACCOUNT_LOCKED",
                        target_type="user", target_id=user["id"],
                        target_label=username,
                        ip_address=request.remote_addr or "")
            return render_template("auth/login.html",
                                   error="Too many failed attempts. Account locked for 15 minutes."
                                  ), 423
        remaining = 5 - (u["failed_attempts"] if u else 0)
        return render_template("auth/login.html",
                               error=f"Invalid username or password. Attempts remaining: {remaining}"
                              ), 401

    if user["is_active"] == 0:
        write_audit(actor_id=user["id"], action="LOGIN_FAILED",
                    target_type="user", target_id=user["id"],
                    target_label=username,
                    ip_address=request.remote_addr or "")
        _record_login(username, success=False)
        return render_template("auth/login.html",
                               error="This account has been deactivated. Contact your administrator."
                              ), 403

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = username
    session["role"] = user["role"]
    session["student_id"] = user["student_id"]
    session["teacher_id"] = user["teacher_id"]
    session["login_at"] = datetime.datetime.utcnow().isoformat()
    session.permanent = True

    update_last_login(user["id"], request.remote_addr or "")
    write_audit(actor_id=user["id"], action="LOGIN_SUCCESS",
                target_type="user", target_id=user["id"],
                target_label=username,
                ip_address=request.remote_addr or "")

    _record_login(username, success=True)

    if user["role"] == "admin":
        return redirect(url_for("admin.index"))
    if user["role"] == "hod":
        return redirect(url_for("hod.index"))
    if user["role"] == "teacher":
        return redirect(url_for("teacher.index"))
    return redirect(url_for("student.index"))


@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    username = session.get("username")
    if user_id:
        write_audit(actor_id=user_id, action="LOGOUT", target_type="user",
                    target_id=user_id, target_label=username,
                    ip_address=request.remote_addr or "")
        # Signed out means offline immediately, not "online for two more minutes".
        presence.mark_signed_out(user_id)
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("auth/change_password.html")

    old_password = (request.form.get("old_password") or "")
    new_password = (request.form.get("new_password") or "")
    confirm_password = (request.form.get("confirm_password") or "")

    if not meets_password_policy(new_password):
        return render_template("auth/change_password.html",
                               error=f"Password must be at least {8} characters."
                              ), 400

    if new_password != confirm_password:
        return render_template("auth/change_password.html",
                               error="New passwords do not match."
                              ), 400

    user = get_user_by_id(user_id)
    if not user or not verify_password(user["password_hash"], old_password):
        return render_template("auth/change_password.html",
                               error="Current password is incorrect."
                              ), 400

    new_hash = hash_password(new_password)
    conn = get_db()
    try:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
        conn.commit()
    finally:
        conn.close()

    write_audit(actor_id=user_id, action="PASSWORD_CHANGE",
                target_type="user", target_id=user_id,
                target_label="own password",
                ip_address=request.remote_addr or "")

    session["login_at"] = datetime.datetime.utcnow().isoformat()
    return redirect(url_for("auth.change_password_done"))


@auth_bp.route("/change-password-done")
def change_password_done():
    return render_template("auth/change_password_done.html")
