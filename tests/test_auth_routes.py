import pytest
from werkzeug.security import generate_password_hash

from app import create_app


def _auth_config(tmp_path):
    return {
        "TESTING": True,
        "AUTH_ENABLED": True,
        "DATABASE_PATH": str(tmp_path / "app.db"),
        "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
        "STORAGE_CERTIFICADOS_ARQUIVADOS": str(tmp_path / "arquivados"),
        "SECRET_KEY": "teste",
        "APP_LOGIN_USER": "legal",
        "APP_LOGIN_PASSWORD_HASH": generate_password_hash("consiste"),
    }


def test_login_exige_autenticacao(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")
    app = create_app(_auth_config(tmp_path))
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_e_logout_com_credenciais_padrao(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")
    app = create_app(_auth_config(tmp_path))
    client = app.test_client()

    login = client.post(
        "/login",
        data={"usuario": "legal", "senha": "consiste"},
        follow_redirects=True,
    )
    assert login.status_code == 200
    assert b"Dashboard" in login.data

    logout = client.get("/logout", follow_redirects=True)
    assert logout.status_code == 200
    assert b"Sessao encerrada com sucesso" in logout.data


def test_login_rejeita_senha_incorreta_com_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")
    app = create_app(_auth_config(tmp_path))
    client = app.test_client()

    response = client.post(
        "/login",
        data={"usuario": "legal", "senha": "errada"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Usuario ou senha invalidos" in response.data


def test_secret_key_obrigatoria_em_modo_real(tmp_path, monkeypatch):
    monkeypatch.chdir("/")
    monkeypatch.setenv("SECRET_KEY", "")
    monkeypatch.setenv("APP_LOGIN_USER", "legal")
    monkeypatch.setenv("APP_LOGIN_PASSWORD_HASH", generate_password_hash("consiste"))
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")

    with pytest.raises(RuntimeError, match="SECRET_KEY obrigatoria"):
        create_app(
            {
                "TESTING": False,
                "DATABASE_PATH": str(tmp_path / "app.db"),
                "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
                "STORAGE_CERTIFICADOS_ARQUIVADOS": str(tmp_path / "arquivados"),
            }
        )
