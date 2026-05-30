import re


TELEFONE_INSTRUCAO = (
    "Digite apenas o numero limpo usado na busca do Messenger. Exemplo: 916031398."
)


def is_telefone_limpo_valido(telefone):
    if not telefone:
        return False
    if not re.fullmatch(r"\d+", telefone):
        return False
    if telefone.startswith("55"):
        return False
    return 8 <= len(telefone) <= 9
