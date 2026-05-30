from app import create_app
from app.repositories.db import init_db


app = create_app()

with app.app_context():
    init_db()
    print(f"Banco inicializado em {app.config['DATABASE_PATH']}")
