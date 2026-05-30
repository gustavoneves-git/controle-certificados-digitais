import os
import secrets
import shutil
from pathlib import Path
from werkzeug.utils import secure_filename


def extensao_valida(filename):
    return bool(filename) and filename.lower().endswith(".pfx")


def salvar_certificado(file_storage, storage_dir):
    original = file_storage.filename
    nome_seguro = secure_filename(original) or "certificado.pfx"
    prefixo = secrets.token_hex(8)
    destino = Path(storage_dir) / f"{prefixo}_{nome_seguro}"
    os.makedirs(storage_dir, exist_ok=True)
    file_storage.save(destino)
    return str(destino)


def caminho_permitido(caminho_arquivo, storage_dir):
    storage = Path(storage_dir).resolve()
    caminho = Path(caminho_arquivo).resolve()
    try:
        caminho.relative_to(storage)
    except ValueError:
        return False
    return caminho.is_file()


def remover_certificado(caminho_arquivo, storage_dir):
    if not caminho_permitido(caminho_arquivo, storage_dir):
        return False
    Path(caminho_arquivo).resolve().unlink()
    return True


def arquivar_certificado(caminho_arquivo, storage_dir, archive_dir):
    if not caminho_permitido(caminho_arquivo, storage_dir):
        return None
    origem = Path(caminho_arquivo).resolve()
    destino_dir = Path(archive_dir)
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origem.name
    if destino.exists():
        destino = destino_dir / f"{secrets.token_hex(4)}_{origem.name}"
    shutil.move(str(origem), str(destino))
    return str(destino)
