from app.services.crypto_service import (
    criptografar_senha,
    descriptografar_senha,
    gerar_chave,
)


def test_criptografa_e_descriptografa_senha(monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", gerar_chave())
    token = criptografar_senha("senha-secreta")

    assert token != "senha-secreta"
    assert descriptografar_senha(token) == "senha-secreta"
