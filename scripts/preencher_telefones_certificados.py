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
from app.services.telefone_service import is_telefone_limpo_valido, normalizar_telefone
from app.services.vencimento_service import calcular_status_contato


CONTATO_A_CONFIRMAR = "Contato a confirmar"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Preenche telefones ausentes usando o campo tecnico de telefone do "
            "certificado salvo. Nao sobrescreve telefones existentes."
        )
    )
    parser.add_argument("--apply", action="store_true", help="Grava as alteracoes no banco. Sem isso, roda em modo previa.")
    parser.add_argument("--certificado-id", type=int, help="Avalia apenas um certificado especifico.")
    parser.add_argument("--limit", type=int, help="Limita a quantidade de certificados avaliados.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        registros = _listar_certificados(args.certificado_id, args.limit)
        resumo = {
            "avaliados": 0,
            "preenchidos": 0,
            "ja_tinha_telefone": 0,
            "sem_telefone_certificado": 0,
            "erros": 0,
        }

        print("Modo:", "APLICAR" if args.apply else "PREVIA")
        for certificado in registros:
            resumo["avaliados"] += 1
            resultado = _processar_certificado(certificado, apply=args.apply)
            resumo[resultado] += 1

        print(
            "Resumo: "
            f"avaliados={resumo['avaliados']} "
            f"preenchidos={resumo['preenchidos']} "
            f"ja_tinha_telefone={resumo['ja_tinha_telefone']} "
            f"sem_telefone_certificado={resumo['sem_telefone_certificado']} "
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
    if normalizar_telefone(certificado["telefone_limpo"]):
        print(f"#{certificado_id}: ja tinha telefone")
        return "ja_tinha_telefone"

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

    telefone = normalizar_telefone(dados.get("telefone_certificado"))
    if not telefone or not is_telefone_limpo_valido(telefone):
        print(f"#{certificado_id}: sem telefone no certificado")
        return "sem_telefone_certificado"

    print(f"#{certificado_id}: telefone encontrado no certificado")
    if apply:
        nome_contato = certificado["nome_contato"] or CONTATO_A_CONFIRMAR
        status_contato = calcular_status_contato(
            None if nome_contato == CONTATO_A_CONFIRMAR else nome_contato,
            certificado["sexo_contato"],
            telefone,
        )
        certificados.update_dados_contato(
            certificado_id,
            {
                "nome_contato": nome_contato,
                "sexo_contato": certificado["sexo_contato"],
                "email_contato": certificado["email_contato"],
                "documento_identificacao": certificado["documento_identificacao"],
                "documento_identificacao_arquivo": certificado["documento_identificacao_arquivo"]
                if "documento_identificacao_arquivo" in certificado.keys()
                else None,
                "telefone_limpo": telefone,
                "observacao": certificado["observacao"],
                "status_contato": status_contato,
            },
        )
        auditoria.registrar_evento(
            certificado_id,
            "TELEFONE_CERTIFICADO_PREENCHIDO",
            "Telefone ausente preenchido a partir do campo tecnico do certificado.",
        )
    return "preenchidos"


if __name__ == "__main__":
    raise SystemExit(main())
