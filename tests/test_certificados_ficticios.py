from datetime import datetime, timezone

import pytest

from app.services.certificado_reader_service import SenhaCertificadoInvalida, ler_pfx
from app.services.vencimento_service import (
    VALIDO,
    VENCE_EM_15_DIAS,
    VENCIDO,
    calcular_status,
)
from scripts.gerar_certificados_teste import SENHA_TESTE, gerar_certificados


def _gerar_base(tmp_path):
    agora = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    output_dir = tmp_path / "certificados_teste"
    gerar_certificados(output_dir=output_dir, agora=agora)
    return output_dir, agora.date()


def _ler(output_dir, nome_arquivo, senha=SENHA_TESTE):
    return ler_pfx((output_dir / nome_arquivo).read_bytes(), senha)


def test_certificado_ficticio_valido_extrai_nome_cnpj_e_validade_futura(tmp_path):
    output_dir, hoje = _gerar_base(tmp_path)

    dados = _ler(output_dir, "empresa_teste_valido.pfx")

    assert dados["nome_extraido"] == "EMPRESA TESTE LTDA"
    assert dados["cnpj_cpf"] == "11222333000181"
    assert dados["tipo_documento"] == "e-CNPJ"
    assert calcular_status(dados["data_validade"], hoje=hoje) == VALIDO


def test_certificado_ficticio_vencido(tmp_path):
    output_dir, hoje = _gerar_base(tmp_path)

    dados = _ler(output_dir, "empresa_teste_vencido.pfx")

    assert dados["nome_extraido"] == "EMPRESA TESTE VENCIDA LTDA"
    assert dados["cnpj_cpf"] == "22333444000191"
    assert calcular_status(dados["data_validade"], hoje=hoje) == VENCIDO


def test_certificado_ficticio_vence_em_15_dias(tmp_path):
    output_dir, hoje = _gerar_base(tmp_path)

    dados = _ler(output_dir, "empresa_teste_vence_15_dias.pfx")

    assert dados["nome_extraido"] == "EMPRESA TESTE ATENCAO LTDA"
    assert dados["cnpj_cpf"] == "33444555000101"
    assert calcular_status(dados["data_validade"], hoje=hoje) == VENCE_EM_15_DIAS


def test_certificado_ficticio_rejeita_senha_incorreta(tmp_path):
    output_dir, _hoje = _gerar_base(tmp_path)

    with pytest.raises(SenhaCertificadoInvalida):
        _ler(output_dir, "empresa_teste_valido.pfx", senha="senha-errada")


def test_certificado_ficticio_trata_arquivo_invalido(tmp_path):
    arquivo = tmp_path / "invalido.pfx"
    arquivo.write_bytes(b"conteudo invalido")

    with pytest.raises(SenhaCertificadoInvalida):
        ler_pfx(arquivo.read_bytes(), SENHA_TESTE)


def test_certificados_substituicao_mesmo_cnpj_com_validades_diferentes(tmp_path):
    output_dir, _hoje = _gerar_base(tmp_path)

    antigo = _ler(output_dir, "empresa_substituicao_antigo.pfx")
    novo = _ler(output_dir, "empresa_substituicao_novo.pfx")

    assert antigo["nome_extraido"] == "EMPRESA SUBSTITUICAO LTDA"
    assert novo["nome_extraido"] == "EMPRESA SUBSTITUICAO LTDA"
    assert antigo["cnpj_cpf"] == "44555666000111"
    assert novo["cnpj_cpf"] == "44555666000111"
    assert antigo["data_validade"] < novo["data_validade"]
