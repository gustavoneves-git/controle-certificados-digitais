from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from scripts import diagnosticar_certificado


def _pfx_bytes(password=b"segredo"):
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


def test_diagnostico_local_imprime_dados_sem_senha(tmp_path, monkeypatch, capsys):
    arquivo = tmp_path / "certificado.pfx"
    arquivo.write_bytes(_pfx_bytes())
    monkeypatch.setattr("sys.argv", ["diagnosticar_certificado.py", str(arquivo)])
    monkeypatch.setattr(diagnosticar_certificado.getpass, "getpass", lambda prompt: "segredo")

    assert diagnosticar_certificado.main() == 0

    saida = capsys.readouterr()
    assert "Nome extraido: Empresa Teste" in saida.out
    assert "CNPJ/CPF: 12345678000195" in saida.out
    assert "Thumbprint SHA1:" in saida.out
    assert "segredo" not in saida.out
    assert "segredo" not in saida.err


def test_diagnostico_local_trata_senha_invalida_sem_imprimir_senha(tmp_path, monkeypatch, capsys):
    arquivo = tmp_path / "certificado.pfx"
    arquivo.write_bytes(_pfx_bytes())
    monkeypatch.setattr("sys.argv", ["diagnosticar_certificado.py", str(arquivo)])
    monkeypatch.setattr(diagnosticar_certificado.getpass, "getpass", lambda prompt: "errada")

    assert diagnosticar_certificado.main() == 1

    saida = capsys.readouterr()
    assert "Nao foi possivel abrir o certificado" in saida.err
    assert "errada" not in saida.out
    assert "errada" not in saida.err
