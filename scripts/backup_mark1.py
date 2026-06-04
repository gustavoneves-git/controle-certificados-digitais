import argparse
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(value, default):
    path = Path(value or default)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _copy_sqlite_database(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def _copy_tree_if_exists(source, destination):
    if not source.exists():
        return False
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return True


def _cleanup_old_backups(backup_dir, keep):
    if keep <= 0:
        return []
    backups = sorted(backup_dir.glob("legal_mark1_*.tar.gz"), key=lambda item: item.stat().st_mtime)
    removidos = []
    while len(backups) > keep:
        antigo = backups.pop(0)
        antigo.unlink()
        removidos.append(str(antigo))
    return removidos


def criar_backup(backup_dir=None, keep=3):
    load_dotenv(PROJECT_ROOT / ".env")

    database_path = _resolve_path(os.getenv("DATABASE_PATH"), "data/app.db")
    storage_certificados = _resolve_path(os.getenv("STORAGE_CERTIFICADOS"), "storage/certificados")
    storage_arquivados = _resolve_path(
        os.getenv("STORAGE_CERTIFICADOS_ARQUIVADOS"),
        "storage/certificados_arquivados",
    )
    env_path = PROJECT_ROOT / ".env"
    backup_dir = _resolve_path(backup_dir or os.getenv("BACKUP_DIR"), "backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.chmod(0o700)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"legal_mark1_{timestamp}.tar.gz"
    manifest_items = []

    with tempfile.TemporaryDirectory(prefix="legal_mark1_backup_") as tmp_name:
        tmp_dir = Path(tmp_name)
        staged = tmp_dir / "legal_mark1"
        staged.mkdir()

        if database_path.exists():
            _copy_sqlite_database(database_path, staged / "data" / database_path.name)
            manifest_items.append(f"data/{database_path.name}")

        _copy_tree_if_exists(storage_certificados, staged / "storage" / "certificados")
        if (staged / "storage" / "certificados").exists():
            manifest_items.append("storage/certificados")

        _copy_tree_if_exists(storage_arquivados, staged / "storage" / "certificados_arquivados")
        if (staged / "storage" / "certificados_arquivados").exists():
            manifest_items.append("storage/certificados_arquivados")

        if env_path.exists():
            shutil.copy2(env_path, staged / ".env")
            manifest_items.append(".env")

        manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "database_path": str(database_path),
            "storage_certificados": str(storage_certificados),
            "storage_certificados_arquivados": str(storage_arquivados),
            "items": manifest_items,
        }
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(staged, arcname="legal_mark1")

    backup_path.chmod(0o600)
    removidos = _cleanup_old_backups(backup_dir, keep)
    return backup_path, manifest_items, removidos


def main():
    parser = argparse.ArgumentParser(description="Cria backup seguro da Mark 1.")
    parser.add_argument("--backup-dir", help="Diretorio onde o backup .tar.gz sera salvo.")
    parser.add_argument("--keep", type=int, default=3, help="Quantidade de backups locais a manter.")
    args = parser.parse_args()

    backup_path, items, removidos = criar_backup(args.backup_dir, args.keep)
    print(f"Backup criado: {backup_path}")
    print("Itens incluidos: " + ", ".join(items))
    if removidos:
        print(f"Backups antigos removidos: {len(removidos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
