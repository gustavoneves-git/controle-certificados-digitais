import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from selenium.webdriver.support.ui import WebDriverWait
except ModuleNotFoundError:
    WebDriverWait = None

from app import create_app
from app.services.onvio_entrada_service import config_entrada_onvio
from app.services.telefone_service import normalizar_telefone
from modulos.entra_onvio import (
    OnvioEntradaConfiguracaoErro,
    OnvioEntradaErro,
    abrir_contatos_messenger,
    abrir_messenger_onvio,
    abrir_onvio,
    autenticar_onvio,
    buscar_contato_por_numero,
    criar_driver_onvio,
    estado_login_onvio,
)


def _logger(etapa, status, mensagem):
    print(f"[{status}] {etapa}: {mensagem}")


def main():
    parser = argparse.ArgumentParser(
        description="Teste assistido do caminho Onvio > Messenger > Contatos. Nao envia mensagem."
    )
    parser.add_argument("--telefone", default="", help="Telefone para buscar, com ou sem mascara.")
    parser.add_argument("--fechar", action="store_true", help="Fecha o navegador ao terminar o teste.")
    args = parser.parse_args()

    app = create_app()
    driver = None
    try:
        if WebDriverWait is None:
            print("Selenium nao instalado. Rode: pip install -r requirements.txt")
            return 1
        with app.app_context():
            config = config_entrada_onvio(logger=_logger)
            config.validar()
            driver = criar_driver_onvio(config)
            wait = WebDriverWait(driver, config.wait_seconds)
            abrir_onvio(driver, wait, config)
            autenticar_onvio(driver, wait, config)
            abrir_messenger_onvio(driver, wait, config)
            abrir_contatos_messenger(driver, wait, config)
            numero = normalizar_telefone(args.telefone)
            if numero:
                buscar_contato_por_numero(driver, wait, numero, config)
                print(f"Busca preenchida com numero limpo: {numero}")
            print("Caminho Onvio > Messenger > Contatos concluido.")
            print(f"Estado login: {estado_login_onvio(driver)}")
            print(f"URL atual: {driver.current_url}")
            if not args.fechar:
                input("Confira a tela. Pressione ENTER aqui no terminal para fechar o navegador...")
            return 0
    except (OnvioEntradaConfiguracaoErro, OnvioEntradaErro) as exc:
        print(f"Erro Onvio: {exc}")
        if driver:
            try:
                print(f"Estado observado: {estado_login_onvio(driver)}")
                print(f"URL atual: {driver.current_url}")
            except Exception:
                pass
        return 1
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
