import pytest

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


def test_falha_clara_sem_chave(monkeypatch):
    monkeypatch.delenv("CERT_PASSWORD_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CERT_PASSWORD_KEY nao configurada"):
        criptografar_senha("senha")


def test_falha_clara_com_chave_invalida(monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "chave-invalida")

    with pytest.raises(RuntimeError, match="CERT_PASSWORD_KEY invalida"):
        criptografar_senha("senha")
