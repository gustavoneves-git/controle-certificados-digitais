import argparse
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

from scripts.backup_mark1 import PROJECT_ROOT, _backup_fernet


def _safe_extract(tar, destino):
    destino_resolvido = destino.resolve()
    for member in tar.getmembers():
        member_path = (destino / member.name).resolve()
        try:
            member_path.relative_to(destino_resolvido)
        except ValueError:
            raise RuntimeError(f"Backup contem caminho inseguro: {member.name}")
    tar.extractall(destino, filter="data")


def restaurar_backup(backup_path, restore_dir):
    load_dotenv(PROJECT_ROOT / ".env")
    backup_path = Path(backup_path)
    restore_dir = Path(restore_dir)
    restore_dir.mkdir(parents=True, exist_ok=True)

    if any(restore_dir.iterdir()):
        raise RuntimeError("A pasta de restauracao precisa estar vazia.")

    tar_path = backup_path
    with tempfile.TemporaryDirectory(prefix="legal_mark1_restore_") as tmp_name:
        tmp_dir = Path(tmp_name)
        if backup_path.suffix == ".enc":
            tar_path = tmp_dir / backup_path.name.removesuffix(".enc")
            tar_path.write_bytes(_backup_fernet().decrypt(backup_path.read_bytes()))

        with tarfile.open(tar_path, "r:gz") as tar:
            _safe_extract(tar, restore_dir)

    return restore_dir


def main():
    parser = argparse.ArgumentParser(
        description="Restaura um backup da Mark 1 em uma pasta vazia para teste ou recuperacao assistida."
    )
    parser.add_argument("backup", help="Arquivo .tar.gz ou .tar.gz.enc.")
    parser.add_argument("--restore-dir", required=True, help="Pasta vazia onde o backup sera extraido.")
    args = parser.parse_args()

    destino = restaurar_backup(args.backup, args.restore_dir)
    print(f"Backup restaurado em: {destino}")
    print("Revise os arquivos restaurados antes de substituir qualquer ambiente real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
