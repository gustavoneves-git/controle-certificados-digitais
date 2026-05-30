from pathlib import Path

from app.services.certificado_storage_service import (
    arquivar_certificado,
    caminho_permitido,
    remover_certificado,
    salvar_certificado,
)


class FakeUpload:
    def __init__(self, filename, content=b"conteudo"):
        self.filename = filename
        self.content = content

    def save(self, destino):
        Path(destino).write_bytes(self.content)


def test_salvar_certificado_usa_nome_seguro_e_nao_sobrescreve(tmp_path):
    primeiro = salvar_certificado(FakeUpload("../../cliente teste.pfx"), tmp_path)
    segundo = salvar_certificado(FakeUpload("../../cliente teste.pfx"), tmp_path)

    assert primeiro != segundo
    assert Path(primeiro).name.endswith("cliente_teste.pfx")
    assert ".." not in Path(primeiro).name
    assert Path(primeiro).read_bytes() == b"conteudo"


def test_caminho_permitido_limita_download_ao_storage(tmp_path):
    permitido = tmp_path / "certificado.pfx"
    permitido.write_bytes(b"pfx")
    fora = tmp_path.parent / "fora.pfx"
    fora.write_bytes(b"pfx")

    assert caminho_permitido(permitido, tmp_path)
    assert not caminho_permitido(fora, tmp_path)
    assert not caminho_permitido(tmp_path / "ausente.pfx", tmp_path)


def test_remover_certificado_apaga_apenas_arquivo_permitido(tmp_path):
    permitido = tmp_path / "certificado.pfx"
    permitido.write_bytes(b"pfx")
    fora = tmp_path.parent / "fora-remocao.pfx"
    fora.write_bytes(b"pfx")

    assert remover_certificado(permitido, tmp_path)
    assert not permitido.exists()
    assert not remover_certificado(fora, tmp_path)
    assert fora.exists()


def test_arquivar_certificado_move_para_pasta_de_arquivados(tmp_path):
    storage = tmp_path / "certificados"
    arquivados = tmp_path / "arquivados"
    storage.mkdir()
    arquivo = storage / "certificado.pfx"
    arquivo.write_bytes(b"pfx")

    destino = arquivar_certificado(arquivo, storage, arquivados)

    assert destino is not None
    assert not arquivo.exists()
    assert Path(destino).exists()
    assert Path(destino).parent == arquivados
    assert Path(destino).read_bytes() == b"pfx"
