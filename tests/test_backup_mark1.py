import os
import sqlite3
import tarfile

import pytest

from scripts import backup_mark1, restaurar_backup_mark1
from scripts.backup_mark1 import _cleanup_old_backups


def test_cleanup_old_backups_mantem_apenas_os_tres_mais_recentes(tmp_path):
    backups = []
    for index in range(4):
        backup = tmp_path / f"legal_mark1_20260604_12000{index}.tar.gz"
        backup.write_text("backup", encoding="utf-8")
        timestamp = 1_000 + index
        os.utime(backup, (timestamp, timestamp))
        backups.append((backup, timestamp))

    removidos = _cleanup_old_backups(tmp_path, keep=3)

    assert len(removidos) == 1
    assert not backups[0][0].exists()
    assert all(backup.exists() for backup, _timestamp in backups[1:])


def test_cleanup_old_backups_tambem_limpa_criptografados(tmp_path):
    backups = []
    for index in range(4):
        backup = tmp_path / f"legal_mark1_20260604_12000{index}.tar.gz.enc"
        backup.write_text("backup", encoding="utf-8")
        timestamp = 1_000 + index
        os.utime(backup, (timestamp, timestamp))
        backups.append((backup, timestamp))

    removidos = _cleanup_old_backups(tmp_path, keep=3)

    assert len(removidos) == 1
    assert not backups[0][0].exists()
    assert all(backup.exists() for backup, _timestamp in backups[1:])


def test_backup_criptografado_pode_ser_restaurado_em_pasta_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_mark1, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(restaurar_backup_mark1, "PROJECT_ROOT", tmp_path)
    backup_key = backup_mark1.gerar_chave_backup()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", backup_key)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "data" / "app.db"))
    monkeypatch.setenv("STORAGE_CERTIFICADOS", str(tmp_path / "storage" / "certificados"))
    monkeypatch.setenv("STORAGE_CERTIFICADOS_ARQUIVADOS", str(tmp_path / "storage" / "certificados_arquivados"))

    database_path = tmp_path / "data" / "app.db"
    database_path.parent.mkdir()
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE teste (nome TEXT)")
        conn.execute("INSERT INTO teste VALUES ('ok')")

    storage = tmp_path / "storage" / "certificados"
    storage.mkdir(parents=True)
    (storage / "certificado.pfx").write_bytes(b"certificado")
    arquivados = tmp_path / "storage" / "certificados_arquivados"
    arquivados.mkdir()
    (tmp_path / ".env").write_text("BACKUP_ENCRYPTION_KEY=\n", encoding="utf-8")

    backup_path, items, removidos = backup_mark1.criar_backup(
        backup_dir=tmp_path / "backups",
        keep=3,
        encrypt=True,
        delete_plain=True,
    )

    assert backup_path.suffix == ".enc"
    assert backup_path.exists()
    assert not backup_path.with_suffix("").exists()
    assert "data/app.db" in items
    assert removidos == []

    restore_dir = tmp_path / "restore"
    restaurar_backup_mark1.restaurar_backup(backup_path, restore_dir)

    restored_db = restore_dir / "legal_mark1" / "data" / "app.db"
    with sqlite3.connect(restored_db) as conn:
        assert conn.execute("SELECT nome FROM teste").fetchone()[0] == "ok"
    assert (restore_dir / "legal_mark1" / "storage" / "certificados" / "certificado.pfx").read_bytes() == b"certificado"
    assert (restore_dir / "legal_mark1" / ".env").exists()


def test_restauracao_bloqueia_caminho_inseguro(tmp_path, monkeypatch):
    monkeypatch.setattr(restaurar_backup_mark1, "PROJECT_ROOT", tmp_path)
    backup_path = tmp_path / "backup.tar.gz"
    arquivo = tmp_path / "malicioso.txt"
    arquivo.write_text("x", encoding="utf-8")
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(arquivo, arcname="../malicioso.txt")

    with pytest.raises(RuntimeError, match="caminho inseguro"):
        restaurar_backup_mark1.restaurar_backup(backup_path, tmp_path / "restore")
