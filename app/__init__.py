import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, g


def create_app(test_config=None):
    load_dotenv()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "data/app.db"),
        STORAGE_CERTIFICADOS=os.getenv("STORAGE_CERTIFICADOS", "storage/certificados"),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]) or ".", exist_ok=True)
    os.makedirs(app.config["STORAGE_CERTIFICADOS"], exist_ok=True)

    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.certificados_routes import certificados_bp
    from app.routes.mensagens_routes import mensagens_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(certificados_bp)
    app.register_blueprint(mensagens_bp)

    app.teardown_appcontext(close_db)
    app.jinja_env.filters["date_br"] = date_br

    from app.repositories.db import init_db

    with app.app_context():
        init_db()

    return app


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
