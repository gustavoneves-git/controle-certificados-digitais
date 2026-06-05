import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from selenium.webdriver.support.ui import WebDriverWait
except ModuleNotFoundError:
    WebDriverWait = None

from app import create_app
from app.services.onvio_entrada_service import config_entrada_onvio
from modulos.entra_onvio import (
    OnvioEntradaConfiguracaoErro,
    OnvioEntradaErro,
    abrir_onvio,
    autenticar_onvio,
    criar_driver_onvio,
    estado_login_onvio,
)


def _logger(etapa, status, mensagem):
    print(f"[{status}] {etapa}: {mensagem}")


def main():
    parser = argparse.ArgumentParser(
        description="Teste assistido de entrada/login no Onvio. Nao busca contato e nao envia mensagem."
    )
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
            print("Abrindo navegador assistido do Onvio...")
            driver = criar_driver_onvio(config)
            wait = WebDriverWait(driver, config.wait_seconds)
            abrir_onvio(driver, wait, config)
            try:
                resultado = autenticar_onvio(driver, wait, config)
            except OnvioEntradaErro as exc:
                if "validacao adicional" not in str(exc).lower():
                    raise
                print(f"Atencao: {exc}")
                print("Complete a validacao no navegador aberto.")
                input("Depois que o Onvio abrir, pressione ENTER aqui para conferir o estado...")
                estado = estado_login_onvio(driver)
                resultado = SimpleNamespace(
                    autenticado=estado == "autenticado",
                    estado=estado,
                    url_atual=driver.current_url,
                )
            print(f"Estado final: {resultado.estado}")
            print(f"Autenticado: {'sim' if resultado.autenticado else 'nao'}")
            print(f"URL atual: {resultado.url_atual}")
            if not args.fechar:
                print("Navegador mantido aberto para conferencia assistida.")
                input("Pressione ENTER aqui no terminal para fechar o navegador...")
            return 0 if resultado.autenticado else 2
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
        if driver and args.fechar:
            driver.quit()
        elif driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
