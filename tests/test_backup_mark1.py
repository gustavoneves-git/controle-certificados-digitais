import os

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
