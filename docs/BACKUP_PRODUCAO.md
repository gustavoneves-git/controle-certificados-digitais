# Backup de producao da Mark 1

O sistema guarda dados sensiveis em:

```text
data/app.db
storage/certificados/
storage/certificados_arquivados/
.env
```

Esses arquivos nunca devem ser versionados no Git. Em producao, eles precisam de backup antes de qualquer atualizacao e tambem de backup automatico recorrente.

## Backup manual antes de atualizar

Na Oracle:

```bash
cd /opt/consiste/legal-certificados
.venv/bin/python scripts/backup_mark1.py --backup-dir /opt/consiste/backups/legal-certificados --keep 60
```

Depois do backup, atualize o codigo:

```bash
git pull origin main
. .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart legal-certificados
```

## Backup automatico diario

Crie o diretorio:

```bash
sudo mkdir -p /opt/consiste/backups/legal-certificados
sudo chown -R ubuntu:ubuntu /opt/consiste/backups
chmod 700 /opt/consiste/backups/legal-certificados
```

Crie o servico:

```bash
sudo nano /etc/systemd/system/legal-certificados-backup.service
```

Conteudo:

```ini
[Unit]
Description=Backup diario do Controle Certificados Digitais

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/consiste/legal-certificados
ExecStart=/opt/consiste/legal-certificados/.venv/bin/python scripts/backup_mark1.py --backup-dir /opt/consiste/backups/legal-certificados --keep 60
```

Crie o timer:

```bash
sudo nano /etc/systemd/system/legal-certificados-backup.timer
```

Conteudo:

```ini
[Unit]
Description=Executa backup diario do Controle Certificados Digitais

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now legal-certificados-backup.timer
sudo systemctl start legal-certificados-backup.service
systemctl list-timers legal-certificados-backup.timer
```

## Restauracao

Para restaurar, pare o sistema antes:

```bash
sudo systemctl stop legal-certificados
```

Extraia o backup escolhido em uma pasta temporaria e copie de volta:

```bash
mkdir -p /tmp/restore-legal
tar -xzf /opt/consiste/backups/legal-certificados/NOME_DO_BACKUP.tar.gz -C /tmp/restore-legal
cp /tmp/restore-legal/legal_mark1/data/app.db /opt/consiste/legal-certificados/data/app.db
cp -a /tmp/restore-legal/legal_mark1/storage/certificados/. /opt/consiste/legal-certificados/storage/certificados/
cp -a /tmp/restore-legal/legal_mark1/storage/certificados_arquivados/. /opt/consiste/legal-certificados/storage/certificados_arquivados/
cp /tmp/restore-legal/legal_mark1/.env /opt/consiste/legal-certificados/.env
sudo chown -R ubuntu:www-data /opt/consiste/legal-certificados/data /opt/consiste/legal-certificados/storage
chmod 600 /opt/consiste/legal-certificados/.env
sudo systemctl start legal-certificados
```

## Importante

Backup no mesmo servidor protege contra erro de atualizacao e alteracao acidental, mas nao protege contra perda total da VM. Para uso definitivo, copie periodicamente os arquivos de `/opt/consiste/backups/legal-certificados/` para outro local seguro, como outro servidor, disco externo criptografado ou Object Storage privado.
