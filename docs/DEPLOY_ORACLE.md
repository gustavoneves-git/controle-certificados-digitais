# Deploy Oracle - legal.consistecontabilidade.com

Este roteiro coloca a Mark 1 em uma VM Oracle usando Gunicorn + Nginx.

Dominio esperado:

```text
legal.consistecontabilidade.com
```

IP publico da VM Oracle:

```text
163.176.226.185
```

## 1. DNS

No painel onde o dominio `consistecontabilidade.com` e administrado, crie um registro:

```text
Tipo: A
Nome: legal
Valor: 163.176.226.185
TTL: automatico ou 300
```

Depois de salvar, o dominio deve apontar para:

```text
legal.consistecontabilidade.com -> 163.176.226.185
```

## 2. Portas na Oracle

Na Oracle Cloud, libere no Security List ou Network Security Group da VM:

```text
80/tcp
443/tcp
```

O Flask/Gunicorn deve ficar interno na VM, por exemplo em `127.0.0.1:5060`.

## 3. Instalar dependencias no servidor

Na VM:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx
```

Clone ou atualize o projeto em um diretorio seguro, por exemplo:

```bash
mkdir -p /opt/consiste
cd /opt/consiste
git clone https://github.com/gustavoneves-git/controle-certificados-digitais.git legal-certificados
cd legal-certificados
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configurar .env de producao

Crie o `.env` diretamente na VM. Nunca envie esse arquivo ao GitHub, Codex ou ChatGPT.

```bash
cp .env.example .env
```

Preencha pelo menos:

```text
FLASK_ENV=production
SECRET_KEY=
CERT_PASSWORD_KEY=
DATABASE_PATH=data/app.db
STORAGE_CERTIFICADOS=storage/certificados
STORAGE_CERTIFICADOS_ARQUIVADOS=storage/certificados_arquivados
APP_LOGIN_USER=
APP_LOGIN_PASSWORD_HASH=
```

Gere as chaves na propria VM:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
.venv/bin/python -c "from app.services.crypto_service import gerar_chave; print(gerar_chave())"
.venv/bin/python scripts/gerar_hash_senha.py
```

## 5. Testar Gunicorn manualmente

```bash
.venv/bin/gunicorn -w 2 -b 127.0.0.1:5060 wsgi:app
```

Em outro terminal da VM:

```bash
curl -I http://127.0.0.1:5060/login
```

Se responder, pare o Gunicorn manual com `Ctrl+C`.

## 6. Criar servico systemd

Crie:

```bash
sudo nano /etc/systemd/system/legal-certificados.service
```

Conteudo:

```ini
[Unit]
Description=Controle Certificados Digitais - Mark 1
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/opt/consiste/legal-certificados
EnvironmentFile=/opt/consiste/legal-certificados/.env
ExecStart=/opt/consiste/legal-certificados/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5060 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable legal-certificados
sudo systemctl start legal-certificados
sudo systemctl status legal-certificados
```

## 7. Configurar Nginx

Crie:

```bash
sudo nano /etc/nginx/sites-available/legal-certificados
```

Conteudo:

```nginx
server {
    listen 80;
    server_name legal.consistecontabilidade.com;

    client_max_body_size 32M;

    location / {
        proxy_pass http://127.0.0.1:5060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative:

```bash
sudo ln -s /etc/nginx/sites-available/legal-certificados /etc/nginx/sites-enabled/legal-certificados
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS

Quando o DNS ja estiver apontando para a VM:

```bash
sudo certbot --nginx -d legal.consistecontabilidade.com
```

Teste renovacao automatica:

```bash
sudo certbot renew --dry-run
```

## 9. Validacao

Acesse:

```text
https://legal.consistecontabilidade.com/login
```

Confira:

- login abre;
- dashboard exige autenticacao;
- upload de `.pfx` funciona;
- download de `.pfx` funciona;
- `storage/certificados/`, `storage/certificados_arquivados/`, `data/*.db` e `.env` nao estao no Git.

## 10. Backup

Antes de uso real, defina backup seguro para:

```text
data/app.db
storage/certificados/
storage/certificados_arquivados/
.env
```

Sem o `.env`, as senhas criptografadas dos certificados nao podem ser recuperadas.
