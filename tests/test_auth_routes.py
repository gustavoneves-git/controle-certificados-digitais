from app import create_app


def test_login_exige_autenticacao(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")
    app = create_app(
        {
            "TESTING": True,
            "AUTH_ENABLED": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
            "SECRET_KEY": "teste",
        }
    )
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_e_logout_com_credenciais_padrao(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "unused")
    app = create_app(
        {
            "TESTING": True,
            "AUTH_ENABLED": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
            "SECRET_KEY": "teste",
        }
    )
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
