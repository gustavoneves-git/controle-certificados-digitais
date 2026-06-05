import re


TELEFONE_INSTRUCAO = (
    "Digite o telefone com DDI. Exemplos: +55 11 99999-9999 ou +1 236-513-9861."
)


def normalizar_telefone(telefone):
    if not telefone:
        return ""
    return re.sub(r"\D", "", telefone)


def is_telefone_limpo_valido(telefone):
    if re.search(r"[A-Za-z]", telefone or ""):
        return False
    telefone_normalizado = normalizar_telefone(telefone)
    if not telefone_normalizado:
        return False
    if telefone_normalizado.startswith("55"):
        return re.fullmatch(r"\d{12,13}", telefone_normalizado) is not None
    if telefone_normalizado.startswith("1"):
        return re.fullmatch(r"\d{11}", telefone_normalizado) is not None
    return False


def formatar_telefone(telefone):
    telefone_normalizado = normalizar_telefone(telefone)
    if len(telefone_normalizado) == 11 and telefone_normalizado.startswith("1"):
        return (
            f"+{telefone_normalizado[:1]} {telefone_normalizado[1:4]}-"
            f"{telefone_normalizado[4:7]}-{telefone_normalizado[7:]}"
        )
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
