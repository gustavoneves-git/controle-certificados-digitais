import argparse
import getpass
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.certificado_reader_service import SenhaCertificadoInvalida, ler_pfx


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostica localmente um arquivo .pfx ou .p12 sem cadastrar no sistema."
    )
    parser.add_argument("arquivo", help="Caminho do arquivo .pfx ou .p12")
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print("Arquivo nao encontrado.", file=sys.stderr)
        return 2

    senha = getpass.getpass("Senha do certificado: ")
    try:
        dados = ler_pfx(caminho.read_bytes(), senha)
    except SenhaCertificadoInvalida:
        print("Nao foi possivel abrir o certificado. Verifique se a senha esta correta.", file=sys.stderr)
        print("O arquivo enviado nao parece ser um certificado .pfx ou .p12 valido.", file=sys.stderr)
        return 1

    print(f"Nome extraido: {dados.get('nome_extraido') or '-'}")
    print(f"CNPJ/CPF: {dados.get('cnpj_cpf') or '-'}")
    print(f"Tipo documento: {dados.get('tipo_documento') or '-'}")
    print(f"Data de emissao: {dados.get('data_emissao') or '-'}")
    print(f"Data de validade: {dados.get('data_validade') or '-'}")
    print(f"Emissor: {dados.get('issuer') or '-'}")
    print(f"Thumbprint SHA1: {dados.get('thumbprint_sha1') or '-'}")
    print(f"Thumbprint SHA256: {dados.get('thumbprint_sha256') or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
