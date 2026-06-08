from app.services.mensagem_service import gerar_mensagem
from app.services.vencimento_service import VENCE_EM_15_DIAS, VENCIDO


def _cert(status):
    return {
        "nome_contato": "Maria",
        "sexo_contato": None,
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


def test_alterna_tres_modelos_para_certificado_vencido():
    mensagens = [gerar_mensagem(_cert(VENCIDO), indice_modelo=i)[1] for i in range(4)]

    assert len(set(mensagens[:3])) == 3
    assert mensagens[0] == mensagens[3]
    assert "vencido desde 10/06/2026" in mensagens[0]
    assert "consta como vencido desde 10/06/2026" in mensagens[1]
    assert "venceu em 10/06/2026" in mensagens[2]


def test_gera_mensagem_para_certificado_vencendo():
    tipo, texto = gerar_mensagem(_cert(VENCE_EM_15_DIAS))

    assert tipo == "CERTIFICADO_VENCENDO"
    assert "vence em 10/06/2026" in texto


def test_gera_mensagem_com_sr_para_homem():
    cert = _cert(VENCE_EM_15_DIAS)
    cert["nome_contato"] = "Jose Rubens"
    cert["sexo_contato"] = "HOMEM"

    _tipo, texto = gerar_mensagem(cert)

    assert "Ola, Sr. Jose Rubens" in texto


def test_gera_mensagem_com_sra_para_mulher():
    cert = _cert(VENCE_EM_15_DIAS)
    cert["nome_contato"] = "Gladys"
    cert["sexo_contato"] = "MULHER"

    _tipo, texto = gerar_mensagem(cert)

    assert "Ola, Sra. Gladys" in texto


def test_gera_mensagem_nao_duplica_tratamento():
    cert = _cert(VENCE_EM_15_DIAS)
    cert["nome_contato"] = "Sr. Jose Rubens"
    cert["sexo_contato"] = "HOMEM"

    _tipo, texto = gerar_mensagem(cert)

    assert "Ola, Sr. Jose Rubens" in texto
    assert "Sr. Sr." not in texto
