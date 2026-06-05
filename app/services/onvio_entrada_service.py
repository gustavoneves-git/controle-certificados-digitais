from pathlib import Path

from flask import current_app

from modulos.entra_onvio import EntrarOnvioConfig


def config_entrada_onvio(logger=None):
    return EntrarOnvioConfig(
        url=current_app.config["ONVIO_URL"],
        email=current_app.config["ONVIO_EMAIL"],
        password=current_app.config["ONVIO_PASSWORD"],
        browser=current_app.config["ONVIO_BROWSER"],
        headless=current_app.config["ONVIO_HEADLESS"],
        user_data_dir=Path(current_app.config["ONVIO_USER_DATA_DIR"]),
        wait_seconds=current_app.config["ONVIO_WAIT_SECONDS"],
        windows_profile_app_name="Consiste Legal Certificados",
        logger=logger,
    )
