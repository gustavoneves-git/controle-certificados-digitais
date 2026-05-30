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


def list_certificados():
    return get_db().execute(
        "SELECT * FROM certificados ORDER BY data_validade IS NULL, data_validade ASC, id DESC"
    ).fetchall()


def get_certificado(certificado_id):
    return get_db().execute(
        "SELECT * FROM certificados WHERE id = ?", (certificado_id,)
    ).fetchone()


def count_by_status(status):
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM certificados WHERE status = ?", (status,)
    ).fetchone()
    return row["total"]


def count_all():
    row = get_db().execute("SELECT COUNT(*) AS total FROM certificados").fetchone()
    return row["total"]
