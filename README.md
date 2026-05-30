# controle-certificados-digitais

Sistema interno Mark 1 para controle manual de certificados digitais de clientes de um escritorio contabil.

## Visao da Mark 1

O usuario cadastra um arquivo `.pfx`, informa a senha, o nome do contato e o telefone limpo usado para busca futura no Messenger/WhatsApp. O sistema le os dados reais do certificado, controla vencimentos, guarda o arquivo para download futuro, protege a senha e gera mensagens manuais para o cliente.

## Regras centrais

- A validade oficial vem da leitura interna do `.pfx`.
- A validade nunca vem do nome do arquivo.
- A Mark 1 nao usa OCR, MMC, Outlook, OneDrive, Graph API, Onvio, Messenger, WhatsApp API ou Selenium.
- CNPJ/CPF extraido do certificado identifica a empresa/certificado.
- Telefone limpo identifica o canal de atendimento.
- Nome do contato personaliza a mensagem.

## Instalacao

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuracao

Crie o `.env` a partir do exemplo:

```bash
cp .env.example .env
python -c "from app.services.crypto_service import gerar_chave; print(gerar_chave())"
```

Preencha `SECRET_KEY` e `CERT_PASSWORD_KEY` no `.env`.

## Banco de dados

```bash
python scripts/init_db.py
```

O banco SQLite padrao fica em `data/app.db`.

## Rodar o sistema

```bash
python run.py
```

Acesse `http://127.0.0.1:5000`.

## Cadastro de certificado

Na tela "Novo certificado", envie um `.pfx`, informe a senha, o nome do contato, o telefone limpo e uma observacao opcional. A senha e testada contra o arquivo; se estiver incorreta, o cadastro fica com status `SENHA_INVALIDA` e um evento de auditoria e registrado.

## Telefone limpo

Use apenas o numero sem DDD, sem `+55`, sem espacos, sem tracos, sem parenteses e sem letras. Exemplo aceito: `916031398`.

## Status

- `VENCIDO`: validade menor que hoje.
- `VENCE_EM_15_DIAS`: validade entre hoje e 15 dias.
- `VALIDO`: validade acima de 15 dias.
- `SENHA_INVALIDA`: senha nao abre o `.pfx`.
- `SEM_TELEFONE`: telefone vazio ou invalido.
- `VERIFICAR`: informacao essencial ausente.

## Seguranca

- A senha do certificado nunca e salva em texto puro.
- `CERT_PASSWORD_KEY` deve ser uma chave Fernet valida e deve ficar somente no `.env`.
- A pasta `storage/certificados` e ignorada pelo Git.
- Visualizar/copiar senha e baixar certificado registra auditoria.

## Testes

```bash
pytest
```
