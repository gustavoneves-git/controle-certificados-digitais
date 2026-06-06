from pathlib import Path

from flask import current_app

from app.services.outlook_graph_service import buscar_codigo_onvio
from modulos.entra_onvio import EntrarOnvioConfig


def config_entrada_onvio(logger=None):
    codigo_provider = buscar_codigo_onvio if _graph_configurado() else None
    return EntrarOnvioConfig(
        url=current_app.config["ONVIO_URL"],
        email=current_app.config["ONVIO_EMAIL"],
        password=current_app.config["ONVIO_PASSWORD"],
        browser=current_app.config["ONVIO_BROWSER"],
        headless=current_app.config["ONVIO_HEADLESS"],
        user_data_dir=Path(current_app.config["ONVIO_USER_DATA_DIR"]),
        wait_seconds=current_app.config["ONVIO_WAIT_SECONDS"],
        windows_profile_app_name="Consiste Legal Certificados",
        codigo_provider=codigo_provider,
        logger=logger,
    )


def _graph_configurado():
    return all(
        current_app.config.get(chave)
        for chave in (
            "MICROSOFT_GRAPH_TENANT_ID",
            "MICROSOFT_GRAPH_CLIENT_ID",
            "MICROSOFT_GRAPH_CLIENT_SECRET",
            "MICROSOFT_GRAPH_USER_EMAIL",
        )
    )
