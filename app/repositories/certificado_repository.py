from app.repositories.db import get_db


def create_certificado(data):
    fields = [
        "nome_arquivo_original",
        "caminho_arquivo",
        "senha_criptografada",
        "subject",
        "issuer",
        "data_emissao",
        "data_validade",
        "thumbprint_sha1",
        "thumbprint_sha256",
        "serial_number",
        "cnpj_cpf",
        "tipo_documento",
        "nome_extraido",
        "nome_contato",
        "telefone_limpo",
        "observacao",
        "status",
        "status_registro",
        "status_vencimento",
        "substituido_por_id",
        "substituido_em",
    ]
    values = [data.get(field) for field in fields]
    placeholders = ", ".join(["?"] * len(fields))
    db = get_db()
    cursor = db.execute(
        f"INSERT INTO certificados ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    return cursor.lastrowid


def list_certificados(status_registro="ATIVO"):
    query = "SELECT * FROM certificados"
    params = []
    if status_registro:
        query += " WHERE status_registro = ?"
        params.append(status_registro)
    query += " ORDER BY data_validade IS NULL, data_validade ASC, id DESC"
    return get_db().execute(query, params).fetchall()


def get_certificado(certificado_id):
    return get_db().execute(
        "SELECT * FROM certificados WHERE id = ?", (certificado_id,)
    ).fetchone()


def get_ativo_by_documento(cnpj_cpf):
    if not cnpj_cpf:
        return None
    return get_db().execute(
        """
        SELECT * FROM certificados
        WHERE cnpj_cpf = ? AND status_registro = 'ATIVO'
        ORDER BY data_validade DESC, id DESC
        LIMIT 1
        """,
        (cnpj_cpf,),
    ).fetchone()


def marcar_substituido(certificado_id, substituido_por_id):
    db = get_db()
    db.execute(
        """
        UPDATE certificados
        SET status_registro = 'SUBSTITUIDO',
            substituido_por_id = ?,
            substituido_em = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (substituido_por_id, certificado_id),
    )
    db.commit()


def count_by_status(status, status_registro="ATIVO"):
    row = get_db().execute(
        """
        SELECT COUNT(*) AS total FROM certificados
        WHERE status_vencimento = ? AND status_registro = ?
        """,
        (status, status_registro),
    ).fetchone()
    return row["total"]


def count_all(status_registro="ATIVO"):
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM certificados WHERE status_registro = ?",
        (status_registro,),
    ).fetchone()
    return row["total"]
