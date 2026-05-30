from app.repositories.db import get_db


def registrar_evento(certificado_id, tipo_evento, descricao):
    db = get_db()
    db.execute(
        """
        INSERT INTO eventos_auditoria (certificado_id, tipo_evento, descricao)
        VALUES (?, ?, ?)
        """,
        (certificado_id, tipo_evento, descricao),
    )
    db.commit()


def listar_eventos(certificado_id):
    return get_db().execute(
        """
        SELECT * FROM eventos_auditoria
        WHERE certificado_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (certificado_id,),
    ).fetchall()
