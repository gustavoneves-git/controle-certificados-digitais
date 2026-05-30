from app.services.mensagem_service import gerar_mensagem
from app.services.vencimento_service import VENCE_EM_15_DIAS, VENCIDO


def _cert(status):
    return {
        "nome_contato": "Maria",
        "nome_extraido": "Empresa Teste",
        "cnpj_cpf": "12345678000195",
        "data_validade": "2026-06-10",
        "status": status,
    }


def test_gera_mensagem_para_certificado_vencido():
    tipo, texto = gerar_mensagem(_cert(VENCIDO))

    assert tipo == "CERTIFICADO_VENCIDO"
    assert "Maria" in texto
    assert "vencido desde 10/06/2026" in texto


def test_gera_mensagem_para_certificado_vencendo():
    tipo, texto = gerar_mensagem(_cert(VENCE_EM_15_DIAS))

    assert tipo == "CERTIFICADO_VENCENDO"
    assert "vence em 10/06/2026" in texto
