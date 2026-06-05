# Recuperacao da Mark 1

Este documento descreve o plano simples de backup e restauracao do Controle de Certificados Digitais.

## Regras de seguranca

- Nunca envie backup aberto para e-mail, GitHub, ChatGPT ou Codex.
- O backup aberto contem banco, certificados `.pfx`, certificados arquivados e `.env`.
- Para nuvem, use apenas o arquivo criptografado `.tar.gz.enc`.
- Guarde a chave `BACKUP_ENCRYPTION_KEY` fora do OneDrive e fora do GitHub.
- Restaure primeiro em uma pasta vazia de teste; nao substitua o sistema real sem conferir.

## Gerar chave de backup

Execute uma vez e salve o valor no `.env` como `BACKUP_ENCRYPTION_KEY`.

```bash
.venv/bin/python scripts/backup_mark1.py --generate-key
```

## Backup local normal

Mantem apenas os 3 backups mais recentes.

```bash
.venv/bin/python scripts/backup_mark1.py --backup-dir /opt/consiste/backups/legal-certificados
```

## Backup criptografado para nuvem

Use este formato para gerar um arquivo seguro para OneDrive compartilhado.

```bash
.venv/bin/python scripts/backup_mark1.py \
  --backup-dir /opt/consiste/backups/legal-certificados-nuvem \
  --encrypt \
  --delete-plain
```

O arquivo gerado termina com:

```text
.tar.gz.enc
```

Esse e o arquivo que pode ser copiado para a pasta compartilhada da empresa.

## Restaurar em pasta de teste

Nunca restaure direto por cima do sistema real. Primeiro restaure em uma pasta vazia:

```bash
.venv/bin/python scripts/restaurar_backup_mark1.py \
  /caminho/backup/legal_mark1_YYYYMMDD_HHMMSS.tar.gz.enc \
  --restore-dir /tmp/restauracao_mark1
```

Depois confira:

```text
/tmp/restauracao_mark1/legal_mark1/data/app.db
/tmp/restauracao_mark1/legal_mark1/storage/certificados
/tmp/restauracao_mark1/legal_mark1/storage/certificados_arquivados
/tmp/restauracao_mark1/legal_mark1/storage/documentos_identificacao
/tmp/restauracao_mark1/legal_mark1/.env
```

## Em caso de problema real

1. Pare o servico.
2. Crie um ultimo backup do estado atual, se possivel.
3. Restaure o backup em pasta temporaria.
4. Confira se os arquivos esperados existem.
5. Substitua banco, storage e `.env` somente depois de validar.
6. Reinicie o servico.
7. Teste login, lista, detalhe e download de um certificado.
