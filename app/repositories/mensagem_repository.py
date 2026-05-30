from app.repositories.db import get_db


def create_mensagem(certificado_id, telefone_limpo, tipo_mensagem, mensagem):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO mensagens (certificado_id, telefone_limpo, tipo_mensagem, mensagem)
        VALUES (?, ?, ?, ?)
        """,
        (certificado_id, telefone_limpo, tipo_mensagem, mensagem),
    )
    db.commit()
    return cursor.lastrowid


def get_mensagem(mensagem_id):
    return get_db().execute(
        "SELECT * FROM mensagens WHERE id = ?", (mensagem_id,)
    ).fetchone()
