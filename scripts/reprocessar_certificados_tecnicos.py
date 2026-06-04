import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.repositories import auditoria_repository as auditoria
from app.repositories import certificado_repository as certificados
from app.repositories.db import get_db
from app.services.certificado_reader_service import SenhaCertificadoInvalida, ler_pfx
from app.services.crypto_service import descriptografar_senha
from app.services.vencimento_service import calcular_status


TECHNICAL_FIELDS = [
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
    "email_certificado",
    "responsavel_certificado",
]


def main():
    parser = argparse.ArgumentParser(
        description="Reprocessa dados tecnicos de certificados ja cadastrados sem alterar contato, senha ou arquivo."
    )
    parser.add_argument("--apply", action="store_true", help="Grava as alteracoes no banco. Sem isso, roda em modo previa.")
    parser.add_argument("--certificado-id", type=int, help="Reprocessa apenas um certificado especifico.")
    parser.add_argument("--limit", type=int, help="Limita a quantidade de certificados avaliados.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        registros = _listar_certificados(args.certificado_id, args.limit)
        resumo = {"avaliados": 0, "alterados": 0, "sem_mudanca": 0, "erros": 0}

        print("Modo:", "APLICAR" if args.apply else "PREVIA")
        for certificado in registros:
            resumo["avaliados"] += 1
            resultado = _processar_certificado(certificado, apply=args.apply)
            resumo[resultado] += 1

        print(
            "Resumo: "
            f"avaliados={resumo['avaliados']} "
            f"alterados={resumo['alterados']} "
            f"sem_mudanca={resumo['sem_mudanca']} "
            f"erros={resumo['erros']}"
        )
    return 0 if resumo["erros"] == 0 else 1


def _listar_certificados(certificado_id=None, limit=None):
    query = "SELECT * FROM certificados"
    params = []
    if certificado_id:
        query += " WHERE id = ?"
        params.append(certificado_id)
    query += " ORDER BY id"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    return get_db().execute(query, params).fetchall()


def _processar_certificado(certificado, apply=False):
    certificado_id = certificado["id"]
    caminho = Path(certificado["caminho_arquivo"] or "")
    if not caminho.is_file():
        print(f"#{certificado_id}: erro - arquivo nao encontrado")
        return "erros"

    try:
        senha = descriptografar_senha(certificado["senha_criptografada"])
        dados = ler_pfx(caminho.read_bytes(), senha)
    except SenhaCertificadoInvalida:
        print(f"#{certificado_id}: erro - senha invalida ou arquivo ilegivel")
        return "erros"
    except Exception as exc:
        print(f"#{certificado_id}: erro - {type(exc).__name__}")
        return "erros"

    status_vencimento = calcular_status(
        dados.get("data_validade"),
        essencial_ok=bool(dados.get("subject")),
    )
    novos_dados = {
        **{field: dados.get(field) for field in TECHNICAL_FIELDS},
        "status": status_vencimento,
        "status_vencimento": status_vencimento,
    }
    mudancas = _mudancas(certificado, novos_dados)
    if not mudancas:
        print(f"#{certificado_id}: sem mudanca")
        return "sem_mudanca"

    print(f"#{certificado_id}: {certificado['nome_arquivo_original']}")
    for campo, antigo, novo in mudancas:
        print(f"  {campo}: {_valor(antigo)} -> {_valor(novo)}")

    if apply:
        certificados.update_dados_tecnicos(certificado_id, novos_dados)
        auditoria.registrar_evento(
            certificado_id,
            "DADOS_TECNICOS_REPROCESSADOS",
            "Dados tecnicos do certificado reprocessados a partir do arquivo salvo.",
        )
    return "alterados"


def _mudancas(certificado, novos_dados):
    mudancas = []
    for campo, novo in novos_dados.items():
        antigo = certificado[campo] if campo in certificado.keys() else None
        if _normalizar(antigo) != _normalizar(novo):
            mudancas.append((campo, antigo, novo))
    return mudancas


def _normalizar(value):
    if value is None:
        return ""
    return str(value)


def _valor(value):
    return "-" if value in (None, "") else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
