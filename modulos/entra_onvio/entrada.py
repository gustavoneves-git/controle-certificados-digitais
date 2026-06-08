import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
except ModuleNotFoundError:
    webdriver = None
    By = None
    WebDriverWait = None

    class WebDriverException(Exception):
        pass

    class TimeoutException(Exception):
        pass


CodigoProvider = Callable[[], str]
EventoLogger = Callable[[str, str, str], None]


class OnvioEntradaErro(Exception):
    """Erro de automacao ao abrir ou autenticar no Onvio."""


class OnvioEntradaConfiguracaoErro(OnvioEntradaErro):
    """Erro de configuracao obrigatoria para entrar no Onvio."""


@dataclass(frozen=True)
class EntrarOnvioConfig:
    url: str = "https://onvio.com.br/staff/#/documents/client"
    email: str = ""
    password: str = ""
    browser: str = "chrome"
    headless: bool = False
    user_data_dir: str | Path = "storage/onvio_browser"
    wait_seconds: int = 25
    windows_profile_app_name: str = "Consiste Legal"
    codigo_provider: Optional[CodigoProvider] = None
    logger: Optional[EventoLogger] = None

    def validar(self) -> None:
        faltando = []
        if not self.email:
            faltando.append("ONVIO_EMAIL")
        if not self.password:
            faltando.append("ONVIO_PASSWORD")
        if faltando:
            raise OnvioEntradaConfiguracaoErro(
                "Credenciais Onvio nao configuradas: " + ", ".join(faltando)
            )
        if self.browser.lower() not in ("edge", "chrome"):
            raise OnvioEntradaConfiguracaoErro("ONVIO_BROWSER deve ser edge ou chrome.")


@dataclass(frozen=True)
class EntrarOnvioResultado:
    autenticado: bool
    estado: str
    url_atual: str


def entrar_onvio(config: EntrarOnvioConfig):
    driver = criar_driver_onvio(config)
    wait = WebDriverWait(driver, config.wait_seconds)
    abrir_onvio(driver, wait, config)
    autenticar_onvio(driver, wait, config)
    return driver


def criar_driver_onvio(config: EntrarOnvioConfig):
    _validar_selenium_disponivel()
    config.validar()
    browser = config.browser.lower()
    user_data_dir = _resolver_user_data_dir(config, browser)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    if browser == "chrome":
        options = webdriver.ChromeOptions()
        _aplicar_opcoes_navegador(options, user_data_dir, config.headless)
        return webdriver.Chrome(options=options)

    options = webdriver.EdgeOptions()
    _aplicar_opcoes_navegador(options, user_data_dir, config.headless)
    return webdriver.Edge(options=options)


def abrir_onvio(driver, wait, config: EntrarOnvioConfig) -> None:
    _registrar(config, "abrir_onvio", "INFO", "Abrindo Onvio.")
    driver.get(config.url)
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")


def autenticar_onvio(driver, wait, config: EntrarOnvioConfig) -> EntrarOnvioResultado:
    config.validar()
    estado_login = estado_login_onvio(driver)
    if estado_login == "autenticado":
        _registrar(config, "sessao_ativa", "INFO", "Sessao Onvio ja estava autenticada.")
        return _resultado(driver, estado_login)
    if estado_login == "validacao_adicional":
        _resolver_validacao_adicional(driver, wait, config)
        return _resultado(driver, estado_login_onvio(driver))

    _registrar(
        config,
        "login",
        "INFO",
        f"Sessao Onvio nao autenticada. Executando login simples ({estado_login}).",
    )
    _abrir_formulario_login_se_necessario(driver, wait)

    estado_login = estado_login_onvio(driver)
    if estado_login == "autenticado":
        return _resultado(driver, estado_login)
    if estado_login == "validacao_adicional":
        _resolver_validacao_adicional(driver, wait, config)
        return _resultado(driver, estado_login_onvio(driver))

    email = _campo_email_login(driver)
    senha = _campo_senha_login(driver)
    if not email and not senha:
        raise OnvioEntradaErro(
            "Tela de login Onvio detectada, mas nenhum campo de e-mail ou senha foi encontrado."
        )

    if email:
        email.clear()
        email.send_keys(config.email)

    if not senha:
        _avancar_login(driver)
        senha = wait.until(lambda d: _campo_senha_login(d) or _esta_em_mfa(d))
        if _esta_em_mfa(driver):
            _resolver_validacao_adicional(driver, wait, config)
            return _resultado(driver, estado_login_onvio(driver))

    senha.clear()
    senha.send_keys(config.password)
    _avancar_login(driver)
    try:
        wait.until(lambda d: _esta_em_mfa(d) or not _esta_em_login(d))
    except TimeoutException as exc:
        raise OnvioEntradaErro(
            "Onvio demorou para concluir o login apos enviar a senha. "
            "Tente novamente; se o navegador mostrar codigo ou aviso de seguranca, conclua manualmente."
        ) from exc
    if _esta_em_mfa(driver):
        _resolver_validacao_adicional(driver, wait, config)
        return _resultado(driver, estado_login_onvio(driver))

    _registrar(config, "login", "SUCESSO", "Login Onvio concluido.")
    return _resultado(driver, estado_login_onvio(driver))


def estado_login_onvio(driver) -> str:
    if _esta_em_mfa(driver):
        return "validacao_adicional"
    url = driver.current_url.lower()
    email = _campo_email_login(driver)
    senha = _campo_senha_login(driver)
    if "onvio.com.br/staff/" in url and not email and not senha:
        return "autenticado"
    if senha and not email:
        return "senha_salva"
    if email and senha:
        return "email_e_senha"
    if email:
        return "email_primeiro"
    if _esta_em_login(driver):
        return "login_indefinido"
    return "autenticado"


def _validar_selenium_disponivel():
    if webdriver is None:
        raise OnvioEntradaConfiguracaoErro(
            "Selenium nao instalado. Rode: pip install -r requirements.txt"
        )


def _resolver_user_data_dir(config: EntrarOnvioConfig, browser: str) -> Path:
    configurado = Path(config.user_data_dir)
    if sys.platform != "win32":
        return configurado

    texto = str(configurado)
    if texto.startswith("\\\\wsl.localhost\\") or texto.startswith("\\\\wsl$\\"):
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / config.windows_profile_app_name / f"onvio_{browser}_profile"
    return configurado


def _aplicar_opcoes_navegador(options, user_data_dir: Path, headless: bool) -> None:
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-dev-shm-usage")
    if sys.platform != "win32":
        options.add_argument("--no-sandbox")
    if headless:
        options.add_argument("--headless=new")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])


def _abrir_formulario_login_se_necessario(driver, wait) -> None:
    if _campo_email_login(driver) or _campo_senha_login(driver):
        return
    url = driver.current_url.lower()
    if "onvio.com.br/login" in url:
        _clicar_inicio_onvio(driver, wait)
        wait.until(
            lambda d: "auth.thomsonreuters.com" in d.current_url.lower()
            or "onvio.com.br/staff/" in d.current_url.lower()
            or bool(_campo_email_login(d))
            or bool(_campo_senha_login(d))
        )


def _clicar_inicio_onvio(driver, wait) -> None:
    seletores = (
        "#trauth-continue-signin-btn",
        "#trta1-auth0-continue-signin-btn",
        "button[type='submit']",
        "button",
    )
    ultimo_erro = None
    for _ in range(2):
        for seletor in seletores:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                for elemento in elementos:
                    if not elemento.is_displayed() or not elemento.is_enabled():
                        continue
                    texto = (elemento.text or "").strip().lower()
                    if seletor == "button" and "entrar" not in texto:
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                    try:
                        elemento.click()
                    except WebDriverException:
                        driver.execute_script("arguments[0].click();", elemento)
                    return
            except Exception as exc:
                ultimo_erro = exc
        try:
            _clicar_primeiro_texto(driver, ("Entrar", "Login", "Sign in", "Acessar"))
            return
        except Exception as exc:
            ultimo_erro = exc
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    raise OnvioEntradaErro("Botao inicial Entrar do Onvio nao foi encontrado.") from ultimo_erro


def _resolver_validacao_adicional(driver, wait, config: EntrarOnvioConfig) -> None:
    if not config.codigo_provider:
        raise OnvioEntradaErro(
            "Onvio solicitou validacao adicional. Informe o codigo manualmente no navegador aberto e rode o teste novamente, ou configure um provedor de codigo."
        )
    _registrar(config, "codigo_onvio", "INFO", "Onvio solicitou codigo de verificacao.")
    codigo = config.codigo_provider()
    if not codigo:
        raise OnvioEntradaErro("Provedor de codigo Onvio nao retornou nenhum codigo.")
    campo_codigo = _campo_codigo_mfa(driver)
    if not campo_codigo:
        raise OnvioEntradaErro("Onvio solicitou codigo, mas o campo de codigo nao foi encontrado.")
    campo_codigo.clear()
    campo_codigo.send_keys(codigo)
    _avancar_login(driver)
    wait.until(lambda d: not _esta_em_mfa(d) or estado_login_onvio(d) == "autenticado")
    if _esta_em_mfa(driver):
        raise OnvioEntradaErro("Codigo Onvio preenchido, mas a validacao adicional permaneceu ativa.")
    _registrar(config, "codigo_onvio", "SUCESSO", "Codigo Onvio preenchido automaticamente.")


def _campo_email_login(driver):
    return _primeiro_presente(
        driver,
        (
            "input[name='username']",
            "input#username",
            "input[type='email']",
            "input[name='uid']",
            "input[name*='email' i]",
            "input[id*='email' i]",
        ),
    )


def _campo_senha_login(driver):
    return _primeiro_presente(
        driver,
        (
            "input[type='password']",
            "input[name='password']",
            "input[name='pwd']",
            "input#password",
            "input#pwd",
            "input[name*='password' i]",
            "input[id*='password' i]",
            "input[name*='senha' i]",
            "input[id*='senha' i]",
        ),
    )


def _campo_codigo_mfa(driver):
    return _primeiro_presente(
        driver,
        (
            "input[name*='mfa' i]",
            "input[id*='mfa' i]",
            "input[name*='code' i]",
            "input[id*='code' i]",
            "input[autocomplete='one-time-code']",
            "input[placeholder*='codigo' i]",
            "input[placeholder*='código' i]",
            "input[type='tel']",
            "input[inputmode='numeric']",
        ),
    )


def _avancar_login(driver) -> None:
    _clicar_primeiro_texto(driver, ("Entrar", "Login", "Sign in", "Acessar", "Continuar", "Continue", "Next"))


def _esta_em_login(driver) -> bool:
    url = driver.current_url.lower()
    if "login" in url or "signin" in url or "auth" in url:
        return True
    return bool(_campo_senha_login(driver))


def _esta_em_mfa(driver) -> bool:
    url = driver.current_url.lower()
    if "mfa" in url or "multi-factor" in url or "multifactor" in url:
        return True
    return bool(_campo_codigo_mfa(driver))


def _primeiro_presente(driver, seletores):
    for seletor in seletores:
        elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
        for elemento in elementos:
            try:
                if elemento.is_displayed() and elemento.is_enabled():
                    return elemento
            except WebDriverException:
                continue
    return None


def _clicar_primeiro_texto(driver, textos) -> None:
    for texto in textos:
        xpath = (
            "//*[self::button or self::a or @role='button']"
            f"[contains(normalize-space(.), { _xpath_literal(texto) })]"
        )
        elementos = driver.find_elements(By.XPATH, xpath)
        for elemento in elementos:
            if elemento.is_displayed() and elemento.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                try:
                    elemento.click()
                except WebDriverException:
                    driver.execute_script("arguments[0].click();", elemento)
                return
    raise OnvioEntradaErro(f"Botao nao encontrado no Onvio: {', '.join(textos)}")


def _xpath_literal(texto: str) -> str:
    if "'" not in texto:
        return f"'{texto}'"
    if '"' not in texto:
        return f'"{texto}"'
    partes = texto.split("'")
    return "concat(" + ", \"'\", ".join(f"'{parte}'" for parte in partes) + ")"


def _resultado(driver, estado: str) -> EntrarOnvioResultado:
    return EntrarOnvioResultado(
        autenticado=estado == "autenticado",
        estado=estado,
        url_atual=_url_atual(driver),
    )


def _url_atual(driver) -> str:
    try:
        return driver.current_url
    except WebDriverException:
        return ""


def _registrar(config: EntrarOnvioConfig, etapa: str, status: str, mensagem: str) -> None:
    if config.logger:
        config.logger(etapa, status, mensagem)
