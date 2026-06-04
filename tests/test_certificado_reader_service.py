from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.services.certificado_reader_service import (
    SenhaCertificadoInvalida,
    extrair_documento,
    ler_pfx,
)


def _pfx_bytes(password=b"123456"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Empresa Teste:12345678000195"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Empresa Teste"),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, "teste@example.com"),
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
        .add_extension(
            x509.SubjectAlternativeName([x509.RFC822Name("teste@example.com")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"certificado-teste",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )


def test_ler_pfx_extrai_dados_e_documento():
    dados = ler_pfx(_pfx_bytes(), "123456")

    assert dados["tipo_documento"] == "e-CNPJ"
    assert dados["cnpj_cpf"] == "12345678000195"
    assert dados["nome_extraido"] == "Empresa Teste"
    assert dados["email_certificado"] == "teste@example.com"
    assert dados["responsavel_certificado"] is None
    assert dados["thumbprint_sha1"]
    assert dados["thumbprint_sha256"]


def test_ler_pfx_mostra_responsavel_quando_certificado_for_cpf():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Pessoa Teste:12345678901"),
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
    pfx = pkcs12.serialize_key_and_certificates(
        name=b"certificado-cpf",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"123456"),
    )

    dados = ler_pfx(pfx, "123456")

    assert dados["tipo_documento"] == "e-CPF"
    assert dados["responsavel_certificado"] == "Pessoa Teste"


def test_ler_pfx_prioriza_documento_do_cn_quando_ou_tem_outro_cnpj():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                "DIEGO HUMBERTO LOPES REPRESENTACOES LTDA:60342097000142",
            ),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "31057526000131"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ICP-Brasil"),
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
    pfx = pkcs12.serialize_key_and_certificates(
        name=b"certificado-ou",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"123456"),
    )

    dados = ler_pfx(pfx, "123456")

    assert dados["cnpj_cpf"] == "60342097000142"
    assert dados["tipo_documento"] == "e-CNPJ"


def test_ler_pfx_trata_senha_invalida():
    with pytest.raises(SenhaCertificadoInvalida):
        ler_pfx(_pfx_bytes(), "errada")


def test_ler_pfx_trata_arquivo_invalido():
    with pytest.raises(SenhaCertificadoInvalida):
        ler_pfx(b"isto nao e um pfx", "123456")


def test_extrair_documento_reconhece_cpf_cnpj_e_desconhecido():
    assert extrair_documento("CPF 123.456.789-01") == ("12345678901", "e-CPF")
    assert extrair_documento("CNPJ 12.345.678/0001-95") == ("12345678000195", "e-CNPJ")
    assert extrair_documento("sem documento") == (None, "DESCONHECIDO")
