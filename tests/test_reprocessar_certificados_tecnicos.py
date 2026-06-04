import io
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime, timezone

from app import create_app
from app.services.crypto_service import gerar_chave
from scripts import reprocessar_certificados_tecnicos
from scripts.gerar_certificados_teste import SENHA_TESTE, gerar_pfx_ficticio
from werkzeug.security import generate_password_hash


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", gerar_chave())
    monkeypatch.setenv("SECRET_KEY", "teste")
    monkeypatch.setenv("APP_LOGIN_USER", "legal")
    monkeypatch.setenv("APP_LOGIN_PASSWORD_HASH", generate_password_hash("consiste"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("STORAGE_CERTIFICADOS", str(tmp_path / "certificados"))
    monkeypatch.setenv("STORAGE_CERTIFICADOS_ARQUIVADOS", str(tmp_path / "certificados_arquivados"))
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
            "STORAGE_CERTIFICADOS_ARQUIVADOS": str(tmp_path / "certificados_arquivados"),
        }
    )


def _row(database_path, table):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchone()
    finally:
        conn.close()


def _cadastrar_certificado(client, caminho):
    return client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(caminho.read_bytes()), caminho.name),
            "senha": SENHA_TESTE,
            "nome_contato": "Maria",
            "sexo_contato": "MULHER",
            "telefone_limpo": "+55 47 91603-1398",
            "observacao": "",
        },
        content_type="multipart/form-data",
    )


def test_reprocessar_previa_nao_altera_banco(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    arquivo = tmp_path / "empresa.pfx"
    arquivo.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA TESTE LTDA",
            "11222333000181",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
    )
    _cadastrar_certificado(client, arquivo)
    certificado = _row(app.config["DATABASE_PATH"], "certificados")

    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        conn.execute("UPDATE certificados SET email_certificado = NULL WHERE id = ?", (certificado["id"],))
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr("sys.argv", ["reprocessar_certificados_tecnicos.py", "--certificado-id", str(certificado["id"])])
    output = io.StringIO()
    with redirect_stdout(output):
        assert reprocessar_certificados_tecnicos.main() == 0

    atualizado = _row(app.config["DATABASE_PATH"], "certificados")
    assert atualizado["email_certificado"] is None
    assert "Modo: PREVIA" in output.getvalue()


def test_reprocessar_apply_atualiza_dados_tecnicos(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    arquivo = tmp_path / "empresa.pfx"
    arquivo.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA TESTE LTDA",
            "11222333000181",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
    )
    _cadastrar_certificado(client, arquivo)
    certificado = _row(app.config["DATABASE_PATH"], "certificados")
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        conn.execute(
            """
            UPDATE certificados
            SET cnpj_cpf = ?, tipo_documento = ?, nome_extraido = ?
            WHERE id = ?
            """,
            ("00000000000000", "e-CNPJ", "NOME ANTIGO", certificado["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        "sys.argv",
        [
            "reprocessar_certificados_tecnicos.py",
            "--apply",
            "--certificado-id",
            str(certificado["id"]),
        ],
    )
    output = io.StringIO()
    with redirect_stdout(output):
        assert reprocessar_certificados_tecnicos.main() == 0

    atualizado = _row(app.config["DATABASE_PATH"], "certificados")
    assert atualizado["cnpj_cpf"] == "11222333000181"
    assert atualizado["nome_extraido"] == "EMPRESA TESTE LTDA"
    assert "Modo: APLICAR" in output.getvalue()
