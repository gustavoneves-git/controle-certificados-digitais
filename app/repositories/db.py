import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo_original TEXT NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            senha_criptografada TEXT NOT NULL,
            subject TEXT,
            issuer TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            thumbprint_sha1 TEXT,
            thumbprint_sha256 TEXT,
            serial_number TEXT,
            cnpj_cpf TEXT,
            tipo_documento TEXT,
            nome_extraido TEXT,
            email_certificado TEXT,
            responsavel_certificado TEXT,
            nome_contato TEXT,
            sexo_contato TEXT,
            email_contato TEXT,
            documento_identificacao TEXT,
            telefone_limpo TEXT,
            observacao TEXT,
            status TEXT NOT NULL,
            status_registro TEXT NOT NULL DEFAULT 'ATIVO',
            status_vencimento TEXT,
            status_contato TEXT NOT NULL DEFAULT 'COM_CONTATO',
            substituido_por_id INTEGER,
            substituido_em TEXT,
            arquivo_arquivado_em TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(substituido_por_id) REFERENCES certificados(id)
        );

        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER NOT NULL,
            telefone_limpo TEXT,
            tipo_mensagem TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            status_envio TEXT NOT NULL DEFAULT 'GERADA',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(certificado_id) REFERENCES certificados(id)
        );

        CREATE TABLE IF NOT EXISTS eventos_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER,
            tipo_evento TEXT NOT NULL,
            descricao TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(certificado_id) REFERENCES certificados(id)
        );
        """
    )
    _ensure_certificados_columns(db)
    db.commit()


def _ensure_certificados_columns(db):
    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(certificados)").fetchall()
    }
    migrations = {
        "status_registro": "ALTER TABLE certificados ADD COLUMN status_registro TEXT NOT NULL DEFAULT 'ATIVO'",
        "status_vencimento": "ALTER TABLE certificados ADD COLUMN status_vencimento TEXT",
        "status_contato": "ALTER TABLE certificados ADD COLUMN status_contato TEXT NOT NULL DEFAULT 'COM_CONTATO'",
        "substituido_por_id": "ALTER TABLE certificados ADD COLUMN substituido_por_id INTEGER",
        "substituido_em": "ALTER TABLE certificados ADD COLUMN substituido_em TEXT",
        "arquivo_arquivado_em": "ALTER TABLE certificados ADD COLUMN arquivo_arquivado_em TEXT",
        "sexo_contato": "ALTER TABLE certificados ADD COLUMN sexo_contato TEXT",
        "email_certificado": "ALTER TABLE certificados ADD COLUMN email_certificado TEXT",
        "responsavel_certificado": "ALTER TABLE certificados ADD COLUMN responsavel_certificado TEXT",
        "email_contato": "ALTER TABLE certificados ADD COLUMN email_contato TEXT",
        "documento_identificacao": "ALTER TABLE certificados ADD COLUMN documento_identificacao TEXT",
    }
    for column, sql in migrations.items():
        if column not in columns:
            db.execute(sql)

    db.execute(
        """
        UPDATE certificados
        SET status_vencimento = CASE
                WHEN status_vencimento = 'SEM_TELEFONE' THEN
                    CASE
                        WHEN data_validade IS NULL THEN 'VERIFICAR'
                        WHEN date(data_validade) < date('now') THEN 'VENCIDO'
                        WHEN date(data_validade) <= date('now', '+15 days') THEN 'VENCE_EM_15_DIAS'
                        ELSE 'VALIDO'
                    END
                ELSE COALESCE(status_vencimento, status)
            END,
            status_contato = CASE
                WHEN COALESCE(nome_contato, '') = ''
                    OR COALESCE(sexo_contato, '') = ''
                    OR COALESCE(telefone_limpo, '') = ''
                    THEN 'SEM_CONTATO'
                ELSE COALESCE(status_contato, 'COM_CONTATO')
            END,
            status_registro = CASE
                WHEN status IN ('SENHA_INVALIDA', 'VERIFICAR') THEN 'VERIFICAR'
                ELSE COALESCE(status_registro, 'ATIVO')
            END
        """
    )
    db.execute(
        """
        UPDATE certificados
        SET tipo_documento = CASE
                WHEN tipo_documento = 'CNPJ' THEN 'e-CNPJ'
                WHEN tipo_documento = 'CPF' THEN 'e-CPF'
                ELSE tipo_documento
            END
        """
    )
