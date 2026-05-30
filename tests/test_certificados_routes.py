import io
import sqlite3
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app import create_app
from app.services.crypto_service import gerar_chave


def _pfx_bytes(password=b"123456"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Empresa Teste:12345678000195"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Empresa Teste"),
        ]
    )
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
        name=b"certificado-teste",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", gerar_chave())
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
        }
    )


def _db_rows(database_path, table):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    finally:
        conn.close()


def test_upload_invalido_nao_usa_nome_do_arquivo_como_validade(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(b"nao e pfx"), "cliente-validade-2099-12-31.pfx"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    assert certificado["status"] == "SENHA_INVALIDA"
    assert certificado["data_validade"] is None
    assert "2099-12-31" in certificado["nome_arquivo_original"]


def test_fluxo_sensivel_registra_auditoria_e_nao_cacheia_senha(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()

    client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(_pfx_bytes()), "cliente.pfx"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
    )
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    certificado_id = certificado["id"]

    senha_response = client.post(f"/certificados/{certificado_id}/senha")
    assert senha_response.status_code == 200
    assert senha_response.headers["Cache-Control"] == "no-store, max-age=0"
    assert senha_response.get_json()["senha"] == "123456"

    assert client.post(f"/certificados/{certificado_id}/senha/copiar").status_code == 200
    assert client.get(f"/certificados/{certificado_id}/download").status_code == 200
    assert client.post(f"/mensagens/certificado/{certificado_id}/gerar").status_code == 302

    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert "CERTIFICADO_CADASTRADO" in eventos
    assert "SENHA_VISUALIZADA" in eventos
    assert "SENHA_COPIADA" in eventos
    assert "CERTIFICADO_BAIXADO" in eventos
    assert "MENSAGEM_GERADA" in eventos
