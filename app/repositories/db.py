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
            nome_contato TEXT,
            telefone_limpo TEXT,
            observacao TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    db.commit()
