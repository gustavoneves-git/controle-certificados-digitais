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
        "email_certificado",
        "responsavel_certificado",
        "nome_contato",
        "sexo_contato",
        "telefone_limpo",
        "observacao",
        "status",
        "status_registro",
        "status_vencimento",
        "status_contato",
        "substituido_por_id",
        "substituido_em",
        "arquivo_arquivado_em",
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


def list_certificados(status_registro="ATIVO", status_vencimento=None, status_contato=None, busca=None):
    query = "SELECT * FROM certificados"
    params = []
    where = []
    if status_registro:
        where.append("status_registro = ?")
        params.append(status_registro)
    if status_vencimento:
        where.append("status_vencimento = ?")
        params.append(status_vencimento)
    if status_contato:
        where.append("status_contato = ?")
        params.append(status_contato)
    if busca:
        termo = f"%{busca.strip()}%"
        where.append(
            """
            (
                cnpj_cpf LIKE ?
                OR nome_extraido LIKE ?
                OR nome_contato LIKE ?
                OR telefone_limpo LIKE ?
            )
            """
        )
        params.extend([termo, termo, termo, termo])
    if where:
        query += " WHERE " + " AND ".join(where)
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


def marcar_substituido(certificado_id, substituido_por_id, caminho_arquivo_arquivado=None):
    db = get_db()
    db.execute(
        """
        UPDATE certificados
        SET status_registro = 'SUBSTITUIDO',
            substituido_por_id = ?,
            substituido_em = CURRENT_TIMESTAMP,
            caminho_arquivo = COALESCE(?, caminho_arquivo),
            arquivo_arquivado_em = CASE
                WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP
                ELSE arquivo_arquivado_em
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (substituido_por_id, caminho_arquivo_arquivado, caminho_arquivo_arquivado, certificado_id),
    )
    db.commit()


def registrar_arquivo_removido(certificado_id):
    db = get_db()
    db.execute(
        """
        UPDATE certificados
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (certificado_id,),
    )
    db.commit()


def update_dados_contato(certificado_id, data):
    db = get_db()
    db.execute(
        """
        UPDATE certificados
        SET nome_contato = ?,
            sexo_contato = ?,
            telefone_limpo = ?,
            observacao = ?,
            status_contato = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            data.get("nome_contato"),
            data.get("sexo_contato"),
            data.get("telefone_limpo"),
            data.get("observacao"),
            data.get("status_contato"),
            certificado_id,
        ),
    )
    db.commit()


def delete_certificado(certificado_id):
    db = get_db()
    db.execute("DELETE FROM mensagens WHERE certificado_id = ?", (certificado_id,))
    db.execute("DELETE FROM eventos_auditoria WHERE certificado_id = ?", (certificado_id,))
    db.execute("DELETE FROM certificados WHERE id = ?", (certificado_id,))
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


def count_by_registro(status_registro):
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM certificados WHERE status_registro = ?",
        (status_registro,),
    ).fetchone()
    return row["total"]


def count_by_contato(status_contato, status_registro="ATIVO"):
    row = get_db().execute(
        """
        SELECT COUNT(*) AS total FROM certificados
        WHERE status_contato = ? AND status_registro = ?
        """,
        (status_contato, status_registro),
    ).fetchone()
    return row["total"]
