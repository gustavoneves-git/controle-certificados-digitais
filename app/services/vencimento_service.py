from datetime import date, datetime, timezone


VALIDO = "VALIDO"
VENCE_EM_15_DIAS = "VENCE_EM_15_DIAS"
VENCIDO = "VENCIDO"
SENHA_INVALIDA = "SENHA_INVALIDA"
SEM_TELEFONE = "SEM_TELEFONE"
VERIFICAR = "VERIFICAR"


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


def calcular_status(data_validade, telefone_valido=True, senha_invalida=False, essencial_ok=True, hoje=None):
    if senha_invalida:
        return SENHA_INVALIDA
    if not telefone_valido:
        return SEM_TELEFONE
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


def status_class(status):
    return {
        VENCIDO: "danger",
        VENCE_EM_15_DIAS: "warning",
        VALIDO: "success",
        SENHA_INVALIDA: "secondary",
        SEM_TELEFONE: "secondary",
        VERIFICAR: "secondary",
    }.get(status, "secondary")
