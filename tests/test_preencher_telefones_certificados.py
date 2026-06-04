import io
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier
from werkzeug.security import generate_password_hash

from app import create_app
from app.services.crypto_service import gerar_chave
from scripts import preencher_telefones_certificados


TELEPHONE_NUMBER_OID = ObjectIdentifier("2.5.4.20")


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


def _pfx_bytes(telefone=None, password=b"123456"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    atributos = [
        x509.NameAttribute(NameOID.COMMON_NAME, "Empresa Telefone:12345678000195"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Empresa Telefone"),
    ]
    if telefone:
        atributos.append(x509.NameAttribute(TELEPHONE_NUMBER_OID, telefone))
    subject = issuer = x509.Name(atributos)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"certificado-telefone",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )


def _row(database_path):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM certificados ORDER BY id").fetchone()
    finally:
        conn.close()


def _cadastrar(client, pfx, telefone_formulario=""):
    return client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(pfx), "cliente.pfx"),
            "senha": "123456",
            "nome_contato": "",
            "sexo_contato": "",
            "telefone_limpo": telefone_formulario,
            "observacao": "",
        },
        content_type="multipart/form-data",
    )


def test_preencher_telefones_previa_nao_altera_banco(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    _cadastrar(client, _pfx_bytes())
    certificado = _row(app.config["DATABASE_PATH"])
    Path(certificado["caminho_arquivo"]).write_bytes(_pfx_bytes("+55 47 91603-1398"))

    monkeypatch.setattr("sys.argv", ["preencher_telefones_certificados.py"])
    output = io.StringIO()
    with redirect_stdout(output):
        assert preencher_telefones_certificados.main() == 0

    atualizado = _row(app.config["DATABASE_PATH"])
    assert atualizado["telefone_limpo"] in (None, "")
    assert atualizado["nome_contato"] in (None, "")
    assert "Modo: PREVIA" in output.getvalue()


def test_preencher_telefones_apply_preenche_vazio_e_marca_contato_a_confirmar(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    _cadastrar(client, _pfx_bytes())
    certificado = _row(app.config["DATABASE_PATH"])
    Path(certificado["caminho_arquivo"]).write_bytes(_pfx_bytes("+55 47 91603-1398"))

    monkeypatch.setattr("sys.argv", ["preencher_telefones_certificados.py", "--apply"])
    output = io.StringIO()
    with redirect_stdout(output):
        assert preencher_telefones_certificados.main() == 0

    atualizado = _row(app.config["DATABASE_PATH"])
    assert atualizado["telefone_limpo"] == "5547916031398"
    assert atualizado["nome_contato"] == "Contato a confirmar"
    assert atualizado["status_contato"] == "SEM_CONTATO"
    assert "preenchidos=1" in output.getvalue()


def test_preencher_telefones_nao_sobrescreve_telefone_existente(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    _cadastrar(client, _pfx_bytes("+55 47 91603-1398"), telefone_formulario="+55 11 99999-9999")

    monkeypatch.setattr("sys.argv", ["preencher_telefones_certificados.py", "--apply"])
    output = io.StringIO()
    with redirect_stdout(output):
        assert preencher_telefones_certificados.main() == 0

    atualizado = _row(app.config["DATABASE_PATH"])
    assert atualizado["telefone_limpo"] == "5511999999999"
    assert atualizado["nome_contato"] in (None, "")
    assert "ja_tinha_telefone=1" in output.getvalue()
