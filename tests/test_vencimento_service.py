from datetime import date, datetime, timezone

from app.services.vencimento_service import (
    VALIDO,
    VENCE_EM_15_DIAS,
    VENCIDO,
    calcular_status,
    dias_para_vencer,
)


def test_dias_para_vencer():
    assert dias_para_vencer("2026-06-10", hoje=date(2026, 6, 1)) == 9


def test_calcular_status_por_vencimento():
    hoje = date(2026, 6, 1)
    assert calcular_status("2026-05-31", hoje=hoje) == VENCIDO
    assert calcular_status("2026-06-01", hoje=hoje) == VENCE_EM_15_DIAS
    assert calcular_status("2026-06-10", hoje=hoje) == VENCE_EM_15_DIAS
    assert calcular_status("2026-06-16", hoje=hoje) == VENCE_EM_15_DIAS
    assert calcular_status("2026-06-17", hoje=hoje) == VALIDO


def test_calcular_status_com_datetime_e_timezone():
    hoje = date(2026, 6, 1)
    data_com_timezone = datetime(2026, 6, 16, 23, 0, tzinfo=timezone.utc)

    assert calcular_status(data_com_timezone, hoje=hoje) == VENCE_EM_15_DIAS
    assert calcular_status("2026-06-17T00:00:00Z", hoje=hoje) == VALIDO
