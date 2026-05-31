from datetime import date

from app.services.vencimento_service import VENCIDO


def gerar_mensagem(certificado):
    nome_contato = _nome_contato_com_tratamento(certificado)
    nome_empresa = certificado["nome_extraido"] or "empresa"
    documento = certificado["cnpj_cpf"] or "nao identificado"
    data_vencimento = _data_br(certificado["data_validade"])

    status = certificado["status_vencimento"] if "status_vencimento" in certificado.keys() else certificado["status"]

    if status == VENCIDO:
        tipo = "CERTIFICADO_VENCIDO"
        texto = (
            f"Ola, {nome_contato}, tudo bem?\n\n"
            f"Estamos entrando em contato sobre o certificado digital da empresa {nome_empresa}, "
            f"CNPJ/CPF {documento}.\n\n"
            f"Identificamos que o certificado esta vencido desde {data_vencimento}. "
            "Para mantermos os acessos e rotinas fiscais em dia, precisamos providenciar a regularizacao.\n\n"
            "Ficamos no aguardo."
        )
    else:
        tipo = "CERTIFICADO_VENCENDO"
        texto = (
            f"Ola, {nome_contato}, tudo bem?\n\n"
            f"Estamos entrando em contato sobre o certificado digital da empresa {nome_empresa}, "
            f"CNPJ/CPF {documento}.\n\n"
            f"Identificamos que o certificado vence em {data_vencimento}. "
            "Recomendamos iniciar a renovacao com antecedencia para evitar bloqueios de acesso.\n\n"
            "Ficamos a disposicao."
        )
    return tipo, texto


def _nome_contato_com_tratamento(certificado):
    nome = certificado["nome_contato"] or "cliente"
    sexo = _get_optional(certificado, "sexo_contato")
    if not sexo:
        return nome
    nome_sem_tratamento = _remover_tratamento(nome)
    if sexo == "HOMEM":
        return f"Sr. {nome_sem_tratamento}"
    if sexo == "MULHER":
        return f"Sra. {nome_sem_tratamento}"
    return nome


def _remover_tratamento(nome):
    tratamentos = ("sr. ", "sra. ", "sr ", "sra ")
    nome_limpo = nome.strip()
    nome_normalizado = nome_limpo.lower()
    for tratamento in tratamentos:
        if nome_normalizado.startswith(tratamento):
            return nome_limpo[len(tratamento):].strip()
    return nome_limpo


def _get_optional(certificado, key):
    if hasattr(certificado, "keys"):
        return certificado[key] if key in certificado.keys() else None
    return certificado.get(key)


def _data_br(value):
    validade = date.fromisoformat(value)
    return validade.strftime("%d/%m/%Y")
