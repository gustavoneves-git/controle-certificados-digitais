import io
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app import create_app
from app.services.crypto_service import gerar_chave
from scripts.gerar_certificados_teste import SENHA_TESTE, gerar_certificados, gerar_pfx_ficticio


def _pfx_bytes(password=b"123456"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Empresa Teste:12345678000195"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Empresa Teste"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"certificado-teste",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("CERT_PASSWORD_KEY", gerar_chave())
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "STORAGE_CERTIFICADOS": str(tmp_path / "certificados"),
            "STORAGE_CERTIFICADOS_ARQUIVADOS": str(tmp_path / "certificados_arquivados"),
        }
    )


def _db_rows(database_path, table):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    finally:
        conn.close()


def _post_pfx(client, arquivo_path, filename=None, senha=SENHA_TESTE, follow_redirects=False):
    return client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(arquivo_path.read_bytes()), filename or arquivo_path.name),
            "senha": senha,
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
        follow_redirects=follow_redirects,
    )


def _gerar_certificados_rota(tmp_path):
    base = tmp_path / "pfx"
    gerar_certificados(output_dir=base, agora=datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc))
    return base


def test_upload_invalido_nao_usa_nome_do_arquivo_como_validade(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(b"nao e pfx"), "cliente-validade-2099-12-31.pfx"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Nao foi possivel abrir o certificado" in response.data
    assert b"O arquivo enviado nao parece ser um certificado .pfx valido" in response.data
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    assert certificado["status"] == "SENHA_INVALIDA"
    assert certificado["data_validade"] is None
    assert "2099-12-31" in certificado["nome_arquivo_original"]


def test_extensao_invalida_mostra_mensagem_amigavel(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(b"texto"), "certificado.txt"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"O arquivo enviado nao parece ser um certificado .pfx valido" in response.data
    assert _db_rows(app.config["DATABASE_PATH"], "certificados") == []


def test_fluxo_sensivel_registra_auditoria_e_nao_cacheia_senha(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()

    client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(_pfx_bytes()), "cliente.pfx"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
    )
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    certificado_id = certificado["id"]

    detalhe_response = client.get(f"/certificados/{certificado_id}")
    assert detalhe_response.status_code == 200
    assert b"Diagnostico tecnico" in detalhe_response.data
    assert b"CERTIFICADO_PFX" in detalhe_response.data
    assert b"Documento extraido" in detalhe_response.data
    assert b"Status calculado" in detalhe_response.data

    senha_response = client.post(f"/certificados/{certificado_id}/senha")
    assert senha_response.status_code == 200
    assert senha_response.headers["Cache-Control"] == "no-store, max-age=0"
    assert senha_response.get_json()["senha"] == "123456"

    assert client.post(f"/certificados/{certificado_id}/senha/copiar").status_code == 200
    assert client.get(f"/certificados/{certificado_id}/download").status_code == 200
    assert client.post(f"/mensagens/certificado/{certificado_id}/gerar").status_code == 302
    mensagem = _db_rows(app.config["DATABASE_PATH"], "mensagens")[0]
    assert client.post(f"/mensagens/{mensagem['id']}/copiar").status_code == 200

    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert "CERTIFICADO_CADASTRADO" in eventos
    assert "SENHA_VISUALIZADA" in eventos
    assert "SENHA_COPIADA" in eventos
    assert "CERTIFICADO_BAIXADO" in eventos
    assert "MENSAGEM_GERADA" in eventos
    assert "MENSAGEM_COPIADA" in eventos


def test_download_funciona_com_caminho_relativo_de_storage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CERT_PASSWORD_KEY", gerar_chave())
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": "data/app.db",
            "STORAGE_CERTIFICADOS": "storage/certificados",
            "STORAGE_CERTIFICADOS_ARQUIVADOS": "storage/certificados_arquivados",
        }
    )
    client = app.test_client()

    client.post(
        "/certificados/novo",
        data={
            "arquivo": (io.BytesIO(_pfx_bytes()), "cliente.pfx"),
            "senha": "123456",
            "nome_contato": "Maria",
            "telefone_limpo": "916031398",
            "observacao": "",
        },
        content_type="multipart/form-data",
    )
    certificado = _db_rows("data/app.db", "certificados")[0]

    response = client.get(f"/certificados/{certificado['id']}/download")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith("attachment;")


def test_primeiro_certificado_de_documento_fica_ativo(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    response = _post_pfx(client, base / "empresa_substituicao_antigo.pfx")

    assert response.status_code == 302
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    assert certificado["cnpj_cpf"] == "44555666000111"
    assert certificado["status_registro"] == "ATIVO"
    assert certificado["status_vencimento"] == "VALIDO"


def test_certificado_mais_novo_substitui_ativo_do_mesmo_documento(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_substituicao_antigo.pfx")
    certificado_antigo = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    caminho_antigo = certificado_antigo["caminho_arquivo"]
    assert Path(caminho_antigo).exists()
    _post_pfx(client, base / "empresa_substituicao_novo.pfx")

    certificados = _db_rows(app.config["DATABASE_PATH"], "certificados")
    antigo, novo = certificados
    assert antigo["status_registro"] == "SUBSTITUIDO"
    assert antigo["substituido_por_id"] == novo["id"]
    assert novo["status_registro"] == "ATIVO"
    assert not Path(caminho_antigo).exists()
    assert Path(antigo["caminho_arquivo"]).exists()
    assert Path(antigo["caminho_arquivo"]).parent == Path(app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"])
    assert Path(novo["caminho_arquivo"]).exists()

    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert eventos.count("CERTIFICADO_SUBSTITUIDO") == 2
    assert "CERTIFICADO_ARQUIVO_ARQUIVADO" in eventos


def test_exclusao_manual_remove_apenas_arquivo_arquivado_de_substituido(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_substituicao_antigo.pfx")
    _post_pfx(client, base / "empresa_substituicao_novo.pfx")
    antigo = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    caminho_arquivado = Path(antigo["caminho_arquivo"])
    assert caminho_arquivado.exists()

    response = client.post(
        f"/certificados/{antigo['id']}/arquivo-arquivado/excluir",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert not caminho_arquivado.exists()
    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert "CERTIFICADO_ARQUIVO_REMOVIDO" in eventos


def test_excluir_certificado_remove_registro_e_arquivo(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_teste_valido.pfx")
    certificado = _db_rows(app.config["DATABASE_PATH"], "certificados")[0]
    caminho = Path(certificado["caminho_arquivo"])
    assert caminho.exists()

    response = client.post(f"/certificados/{certificado['id']}/excluir", follow_redirects=True)

    assert response.status_code == 200
    assert b"Certificado excluido com sucesso" in response.data
    assert not caminho.exists()
    assert _db_rows(app.config["DATABASE_PATH"], "certificados") == []


def test_bloqueia_substituicao_com_validade_menor_ou_igual(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_substituicao_novo.pfx")
    response = _post_pfx(
        client,
        base / "empresa_substituicao_antigo.pfx",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Ja existe um certificado ativo para este CNPJ/CPF com validade igual ou superior" in response.data
    certificados = _db_rows(app.config["DATABASE_PATH"], "certificados")
    assert len(certificados) == 1
    assert certificados[0]["status_registro"] == "ATIVO"

    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert "TENTATIVA_SUBSTITUICAO_BLOQUEADA" in eventos


def test_dashboard_e_lista_padrao_consideram_apenas_ativos(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_teste_vencido.pfx")
    _post_pfx(client, base / "empresa_substituicao_antigo.pfx")
    _post_pfx(client, base / "empresa_substituicao_novo.pfx")

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"Vencidos</span>\n            <strong>1</strong>" in dashboard.data
    assert b"Ativos</span>\n            <strong>2</strong>" in dashboard.data

    lista = client.get("/certificados/")
    assert lista.status_code == 200
    certificados = _db_rows(app.config["DATABASE_PATH"], "certificados")
    substituido = [row for row in certificados if row["status_registro"] == "SUBSTITUIDO"][0]
    ativo_substituto = [
        row
        for row in certificados
        if row["cnpj_cpf"] == "44555666000111" and row["status_registro"] == "ATIVO"
    ][0]
    assert f'/certificados/{substituido["id"]}'.encode() not in lista.data
    assert f'/certificados/{ativo_substituto["id"]}'.encode() in lista.data

    substituidos = client.get("/certificados/?status_registro=SUBSTITUIDO")
    assert f'/certificados/{substituido["id"]}'.encode() in substituidos.data


def test_filtros_rapidos_e_busca_da_lista(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_teste_valido.pfx")
    _post_pfx(client, base / "empresa_teste_vencido.pfx")
    _post_pfx(client, base / "empresa_teste_vence_15_dias.pfx")

    vencidos = client.get("/certificados/?filtro=VENCIDO")
    assert b"EMPRESA TESTE VENCIDA LTDA" in vencidos.data
    assert b"EMPRESA TESTE LTDA" not in vencidos.data

    busca_cnpj = client.get("/certificados/?filtro=TODOS&busca=33444555000101")
    assert b"EMPRESA TESTE ATENCAO LTDA" in busca_cnpj.data
    assert b"EMPRESA TESTE VENCIDA LTDA" not in busca_cnpj.data

    busca_contato = client.get("/certificados/?filtro=TODOS&busca=916031398")
    assert busca_contato.data.count(b"916031398") >= 3


def test_dashboard_tem_cards_operacionais_clicaveis(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    base = _gerar_certificados_rota(tmp_path)

    _post_pfx(client, base / "empresa_teste_valido.pfx")
    _post_pfx(client, base / "empresa_teste_vencido.pfx")
    _post_pfx(client, base / "empresa_substituicao_antigo.pfx")
    _post_pfx(client, base / "empresa_substituicao_novo.pfx")

    response = client.get("/")

    assert response.status_code == 200
    assert b"Ativos" in response.data
    assert b"Verificar" in response.data
    assert b"Senha invalida" in response.data
    assert b"Sem telefone" in response.data
    assert b"Substituidos" in response.data
    assert b"/certificados/?filtro=VENCIDO" in response.data
    assert b"/certificados/?filtro=SUBSTITUIDO" in response.data


def test_certificado_substituido_vencido_nao_conta_como_pendencia_principal(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    antigo = tmp_path / "antigo_vencido.pfx"
    novo = tmp_path / "novo_valido.pfx"
    antigo.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA VENCIDA SUBSTITUIDA LTDA",
            "55666777000121",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 2, 1, tzinfo=timezone.utc),
        )
    )
    novo.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA VENCIDA SUBSTITUIDA LTDA",
            "55666777000121",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
    )

    _post_pfx(client, antigo)
    _post_pfx(client, novo)

    dashboard = client.get("/")
    assert b"Vencidos</span>\n            <strong>0</strong>" in dashboard.data
    certificados = _db_rows(app.config["DATABASE_PATH"], "certificados")
    assert certificados[0]["status_registro"] == "SUBSTITUIDO"
    assert certificados[0]["status_vencimento"] == "VENCIDO"


def test_certificado_sem_documento_nao_aplica_substituicao_automatica(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    client = app.test_client()
    primeiro = tmp_path / "sem_doc_1.pfx"
    segundo = tmp_path / "sem_doc_2.pfx"
    primeiro.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA SEM DOCUMENTO LTDA",
            "",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
    )
    segundo.write_bytes(
        gerar_pfx_ficticio(
            "EMPRESA SEM DOCUMENTO LTDA",
            "",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2027, 12, 31, tzinfo=timezone.utc),
        )
    )

    _post_pfx(client, primeiro)
    _post_pfx(client, segundo)

    certificados = _db_rows(app.config["DATABASE_PATH"], "certificados")
    assert len(certificados) == 2
    assert {row["status_registro"] for row in certificados} == {"VERIFICAR"}
    eventos = [
        row["tipo_evento"]
        for row in _db_rows(app.config["DATABASE_PATH"], "eventos_auditoria")
    ]
    assert eventos.count("DOCUMENTO_NAO_IDENTIFICADO") == 2
