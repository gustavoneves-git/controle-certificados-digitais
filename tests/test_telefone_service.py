from app.services.telefone_service import (
    formatar_telefone,
    is_telefone_limpo_valido,
    normalizar_telefone,
)


def test_telefone_limpo_valido():
    assert is_telefone_limpo_valido("+55 47 91603-1398")
    assert is_telefone_limpo_valido("5547916031398")
    assert normalizar_telefone("+55 47 91603-1398") == "5547916031398"
    assert formatar_telefone("5547916031398") == "+55 47 91603-1398"


def test_telefone_limpo_rejeita_formatos_invalidos():
    assert not is_telefone_limpo_valido("+55 91603-1398")
    assert not is_telefone_limpo_valido("47916031398")
    assert not is_telefone_limpo_valido("91603-1398")
    assert not is_telefone_limpo_valido("(47)916031398")
    assert not is_telefone_limpo_valido("abc916031398")
