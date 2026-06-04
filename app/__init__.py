import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, current_app, g, redirect, request, session, url_for


def create_app(test_config=None):
    load_dotenv()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "data/app.db"),
        STORAGE_CERTIFICADOS=os.getenv("STORAGE_CERTIFICADOS", "storage/certificados"),
        STORAGE_CERTIFICADOS_ARQUIVADOS=os.getenv(
            "STORAGE_CERTIFICADOS_ARQUIVADOS", "storage/certificados_arquivados"
        ),
        APP_LOGIN_USER=os.getenv("APP_LOGIN_USER"),
        APP_LOGIN_PASSWORD_HASH=os.getenv("APP_LOGIN_PASSWORD_HASH"),
        AUTH_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)
    if app.config.get("TESTING") and "AUTH_ENABLED" not in (test_config or {}):
        app.config["AUTH_ENABLED"] = False
    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY obrigatoria no .env")
    if app.config.get("AUTH_ENABLED") and (
        not app.config.get("APP_LOGIN_USER")
        or not app.config.get("APP_LOGIN_PASSWORD_HASH")
    ):
        raise RuntimeError("APP_LOGIN_USER e APP_LOGIN_PASSWORD_HASH obrigatorios no .env")

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]) or ".", exist_ok=True)
    os.makedirs(app.config["STORAGE_CERTIFICADOS"], exist_ok=True)
    os.makedirs(app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"], exist_ok=True)

    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.certificados_routes import certificados_bp
    from app.routes.mensagens_routes import mensagens_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(certificados_bp)
    app.register_blueprint(mensagens_bp)

    app.before_request(require_login)
    app.after_request(no_cache_for_authenticated_pages)
    app.teardown_appcontext(close_db)
    app.jinja_env.filters["date_br"] = date_br
    app.jinja_env.filters["telefone_br"] = telefone_br

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


def no_cache_for_authenticated_pages(response):
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


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


def telefone_br(value):
    from app.services.telefone_service import formatar_telefone

    return formatar_telefone(value) or "-"
