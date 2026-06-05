import pytest

from app import create_app
from app.services.onvio_entrada_service import config_entrada_onvio
from modulos.entra_onvio import EntrarOnvioConfig, OnvioEntradaConfiguracaoErro


def test_config_entrada_onvio_monta_variaveis_do_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", "x" * 44)
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "ONVIO_URL": "https://onvio.com.br/staff/#/documents/client",
            "ONVIO_EMAIL": "usuario@example.com",
            "ONVIO_PASSWORD": "senha",
            "ONVIO_BROWSER": "edge",
            "ONVIO_HEADLESS": False,
            "ONVIO_USER_DATA_DIR": str(tmp_path / "onvio_browser"),
            "ONVIO_WAIT_SECONDS": 30,
        }
    )

    with app.app_context():
        config = config_entrada_onvio()

    assert config.url == "https://onvio.com.br/staff/#/documents/client"
    assert config.email == "usuario@example.com"
    assert config.password == "senha"
    assert config.browser == "edge"
    assert config.user_data_dir == tmp_path / "onvio_browser"
    assert config.wait_seconds == 30


def test_config_entrada_onvio_exige_credenciais():
    config = EntrarOnvioConfig(email="", password="", browser="chrome")

    with pytest.raises(OnvioEntradaConfiguracaoErro, match="ONVIO_EMAIL"):
        config.validar()


def test_config_entrada_onvio_exige_browser_suportado():
    config = EntrarOnvioConfig(email="usuario@example.com", password="senha", browser="firefox")

    with pytest.raises(OnvioEntradaConfiguracaoErro, match="edge ou chrome"):
        config.validar()
