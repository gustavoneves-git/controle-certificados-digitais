import re


TELEFONE_INSTRUCAO = (
    "Digite o telefone com DDI e DDD. Exemplo: +55 11 99999-9999."
)


def normalizar_telefone(telefone):
    if not telefone:
        return ""
    return re.sub(r"\D", "", telefone)


def is_telefone_limpo_valido(telefone):
    telefone_normalizado = normalizar_telefone(telefone)
    if not telefone_normalizado:
        return False
    return re.fullmatch(r"\d{12,13}", telefone_normalizado) is not None


def formatar_telefone(telefone):
    telefone_normalizado = normalizar_telefone(telefone)
    if len(telefone_normalizado) == 13:
        return (
            f"+{telefone_normalizado[:2]} {telefone_normalizado[2:4]} "
            f"{telefone_normalizado[4:9]}-{telefone_normalizado[9:]}"
        )
    if len(telefone_normalizado) == 12:
        return (
            f"+{telefone_normalizado[:2]} {telefone_normalizado[2:4]} "
            f"{telefone_normalizado[4:8]}-{telefone_normalizado[8:]}"
        )
    return telefone or ""
