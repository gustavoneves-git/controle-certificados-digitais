from datetime import date, datetime, timezone


VALIDO = "VALIDO"
VENCE_EM_15_DIAS = "VENCE_EM_15_DIAS"
VENCIDO = "VENCIDO"
SENHA_INVALIDA = "SENHA_INVALIDA"
VERIFICAR = "VERIFICAR"
SEM_CONTATO = "SEM_CONTATO"
COM_CONTATO = "COM_CONTATO"


def parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.date()
    if isinstance(value, date):
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.date()


def dias_para_vencer(data_validade, hoje=None):
    validade = parse_date(data_validade)
    if validade is None:
        return None
    hoje = hoje or date.today()
    return (validade - hoje).days


def calcular_status(data_validade, senha_invalida=False, essencial_ok=True, hoje=None):
    if senha_invalida:
        return SENHA_INVALIDA
    if not essencial_ok:
        return VERIFICAR

    dias = dias_para_vencer(data_validade, hoje=hoje)
    if dias is None:
        return VERIFICAR
    if dias < 0:
        return VENCIDO
    if dias <= 15:
        return VENCE_EM_15_DIAS
    return VALIDO


def calcular_status_contato(nome_contato=None, sexo_contato=None, telefone_limpo=None):
    if nome_contato and sexo_contato and telefone_limpo:
        return COM_CONTATO
    return SEM_CONTATO


def status_class(status):
    return {
        VENCIDO: "danger",
        VENCE_EM_15_DIAS: "warning",
        VALIDO: "success",
        SENHA_INVALIDA: "secondary",
        VERIFICAR: "secondary",
        SEM_CONTATO: "secondary",
        COM_CONTATO: "success",
    }.get(status, "secondary")
