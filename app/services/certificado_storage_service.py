import os
import secrets
from pathlib import Path
from werkzeug.utils import secure_filename


def extensao_valida(filename):
    return bool(filename) and filename.lower().endswith(".pfx")


def salvar_certificado(file_storage, storage_dir):
    original = file_storage.filename
    nome_seguro = secure_filename(original)
    prefixo = secrets.token_hex(8)
    destino = Path(storage_dir) / f"{prefixo}_{nome_seguro}"
    os.makedirs(storage_dir, exist_ok=True)
    file_storage.save(destino)
    return str(destino)
