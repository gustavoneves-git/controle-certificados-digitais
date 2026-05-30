import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, current_app, g, redirect, request, session, url_for


def create_app(test_config=None):
    load_dotenv()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "data/app.db"),
        STORAGE_CERTIFICADOS=os.getenv("STORAGE_CERTIFICADOS", "storage/certificados"),
        LOGIN_USUARIO=os.getenv("LOGIN_USUARIO", "legal"),
        LOGIN_SENHA=os.getenv("LOGIN_SENHA", "consiste"),
        AUTH_ENABLED=True,
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)
    if app.config.get("TESTING") and "AUTH_ENABLED" not in (test_config or {}):
        app.config["AUTH_ENABLED"] = False

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]) or ".", exist_ok=True)
    os.makedirs(app.config["STORAGE_CERTIFICADOS"], exist_ok=True)

    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.certificados_routes import certificados_bp
    from app.routes.mensagens_routes import mensagens_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(certificados_bp)
    app.register_blueprint(mensagens_bp)

    app.before_request(require_login)
    app.teardown_appcontext(close_db)
    app.jinja_env.filters["date_br"] = date_br

    from app.repositories.db import init_db

    with app.app_context():
        init_db()

    return app


def require_login():
    if not current_app.config.get("AUTH_ENABLED", True):
        return None
    allowed_endpoints = {"auth.login", "static"}
    if request.endpoint in allowed_endpoints:
        return None
    if session.get("autenticado"):
        return None
    return redirect(url_for("auth.login"))


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def date_br(value):
    if not value:
        return "-"
    if hasattr(value, "strftime") and not isinstance(value, str):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.strftime("%d/%m/%Y")
