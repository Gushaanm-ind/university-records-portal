# university_portal/app.py
import os
import time
import datetime
from flask import Flask, session, g, abort, request, render_template
from flask_wtf.csrf import CSRFProtect, CSRFError
from portal.config import Config
from portal.db import init_db
from portal.audit import write_audit
from portal.repositories.users import get_user_by_id
from portal.services import presence

from portal.blueprints.auth import auth_bp
from portal.blueprints.dashboard import dashboard_bp
from portal.blueprints.student import student_bp
from portal.blueprints.teacher import teacher_bp
from portal.blueprints.hod import hod_bp
from portal.blueprints.admin import admin_bp


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app():
    # Templates and static files live inside the portal package.
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "portal", "templates"),
        static_folder=os.path.join(BASE_DIR, "portal", "static"),
    )
    app.config.from_object("portal.config.Config")

    # Session cookie hardening (Flask sets these on the real session cookie).
    # Secure is opt-in: a Secure cookie is not sent over http://localhost, which
    # would silently break sign-in for local demos. Enable it with
    # SESSION_COOKIE_SECURE=1 when serving over HTTPS.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(
            minutes=Config.SESSION_TIMEOUT_MINUTES
        ),
    )

    csrf = CSRFProtect(app)

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(admin_bp)

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.before_request
    def check_session_timeout():
        if session.get("user_id"):
            login_at = session.get("login_at")
            if login_at:
                try:
                    started = datetime.datetime.fromisoformat(login_at)
                    idle = (datetime.datetime.utcnow() - started).total_seconds() / 60
                    if idle > Config.SESSION_TIMEOUT_MINUTES:
                        session.clear()
                        return render_template(
                            "auth/login.html",
                            error="Your session expired after 30 minutes of inactivity. "
                                  "Please sign in again.",
                        ), 403
                except (ValueError, TypeError):
                    pass

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                g.user = user
                # Presence: refresh last_seen_at, at most every few seconds so a
                # page with many assets does not write to the database each time.
                now = time.time()
                if now - float(session.get("presence_at") or 0) >= presence.STAMP_EVERY_SECONDS:
                    presence.mark_seen(user_id)
                    session["presence_at"] = now
            else:
                session.clear()
                g.user = None
        else:
            g.user = None

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Never show the raw '400 Bad Request' page for a stale/missing token."""
        return render_template(
            "errors/csrf.html",
            reason=e.description or "The form could not be verified.",
        ), 400

    @app.errorhandler(403)
    def handle_403(e):
        # Every denied request is recorded exactly once, here.
        try:
            user = getattr(g, "user", None)
            write_audit(
                actor_id=user["id"] if user else 0,
                action="ACCESS_DENIED",
                target_type="route",
                target_label=f"{request.method} {request.path}",
                field_changed=getattr(e, "description", None),
                ip_address=request.remote_addr or "",
                actor_username=session.get("username") or "anonymous",
                actor_role=session.get("role") or "anonymous",
            )
        except Exception:
            pass
        return render_template("errors/403.html",
                               message=getattr(e, "description", None)), 403

    @app.errorhandler(404)
    def handle_404(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_500(e):
        if getattr(g, "user", None):
            try:
                write_audit(
                    actor_id=g.user["id"],
                    action="ACCESS_DENIED",
                    target_type="system",
                    target_label="internal server error",
                    ip_address=request.remote_addr or "",
                )
            except Exception:
                pass
        return render_template("errors/500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    debug = os.environ.get("DEBUG", "0") == "1"
    app.run(debug=debug, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
