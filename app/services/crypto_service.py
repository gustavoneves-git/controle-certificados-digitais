import os

from cryptography.fernet import Fernet


def gerar_chave():
    return Fernet.generate_key().decode("utf-8")


def _fernet():
    key = os.getenv("CERT_PASSWORD_KEY")
    if not key:
        raise RuntimeError("CERT_PASSWORD_KEY nao configurada no .env")
    return Fernet(key.encode("utf-8"))


def criptografar_senha(senha):
    return _fernet().encrypt((senha or "").encode("utf-8")).decode("utf-8")


def descriptografar_senha(senha_criptografada):
    return _fernet().decrypt(senha_criptografada.encode("utf-8")).decode("utf-8")
