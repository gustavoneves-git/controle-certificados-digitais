from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


SENHA_TESTE = "teste123"
OUTPUT_DIR = Path("tmp/certificados_teste")


def cenarios_certificados(agora=None):
    agora = agora or datetime.now(timezone.utc)
    return [
        {
            "arquivo": "empresa_teste_valido.pfx",
            "nome": "EMPRESA TESTE LTDA",
            "cnpj": "11222333000181",
            "inicio": agora - timedelta(days=1),
            "validade": agora + timedelta(days=365),
        },
        {
            "arquivo": "empresa_teste_vencido.pfx",
            "nome": "EMPRESA TESTE VENCIDA LTDA",
            "cnpj": "22333444000191",
            "inicio": agora - timedelta(days=400),
            "validade": agora - timedelta(days=1),
        },
        {
            "arquivo": "empresa_teste_vence_15_dias.pfx",
            "nome": "EMPRESA TESTE ATENCAO LTDA",
            "cnpj": "33444555000101",
            "inicio": agora - timedelta(days=30),
            "validade": agora + timedelta(days=10),
        },
        {
            "arquivo": "empresa_substituicao_antigo.pfx",
            "nome": "EMPRESA SUBSTITUICAO LTDA",
            "cnpj": "44555666000111",
            "inicio": agora - timedelta(days=30),
            "validade": agora + timedelta(days=90),
        },
        {
            "arquivo": "empresa_substituicao_novo.pfx",
            "nome": "EMPRESA SUBSTITUICAO LTDA",
            "cnpj": "44555666000111",
            "inicio": agora - timedelta(days=1),
            "validade": agora + timedelta(days=365),
        },
    ]


def gerar_pfx_ficticio(nome, cnpj, inicio, validade, senha=SENHA_TESTE):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, f"{nome}:{cnpj}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, nome),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, cnpj),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        ]
    )
    certificado = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(inicio)
        .not_valid_after(validade)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=nome.encode("utf-8"),
        key=key,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
    )


def gerar_certificados(output_dir=OUTPUT_DIR, agora=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    arquivos = []
    for cenario in cenarios_certificados(agora):
        destino = output_dir / cenario["arquivo"]
        destino.write_bytes(
            gerar_pfx_ficticio(
                cenario["nome"],
                cenario["cnpj"],
                cenario["inicio"],
                cenario["validade"],
            )
        )
        arquivos.append(destino)
    return arquivos


def main():
    arquivos = gerar_certificados()
    print("Certificados ficticios gerados em tmp/certificados_teste/")
    for arquivo in arquivos:
        print(f"- {arquivo}")
    print("Senha ficticia padrao: teste123")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
