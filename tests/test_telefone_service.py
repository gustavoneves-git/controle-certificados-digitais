from app.services.telefone_service import is_telefone_limpo_valido


def test_telefone_limpo_valido():
    assert is_telefone_limpo_valido("916031398")


def test_telefone_limpo_rejeita_formatos_invalidos():
    assert not is_telefone_limpo_valido("+55916031398")
    assert not is_telefone_limpo_valido("47916031398")
    assert not is_telefone_limpo_valido("91603-1398")
    assert not is_telefone_limpo_valido("(47)916031398")
    assert not is_telefone_limpo_valido("abc916031398")
