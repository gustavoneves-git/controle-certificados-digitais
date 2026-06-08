# Entrada Onvio assistida

Esta etapa serve apenas para validar a entrada/login no Onvio com Selenium.

Ela ainda nao:

- busca contato;
- abre conversa do Messenger;
- cola mensagem;
- envia mensagem;
- verifica resposta de cliente;
- roda em fila automatica.

## Configuracao

Configure no `.env`:

```text
ONVIO_URL=https://onvio.com.br/staff/#/documents/client
ONVIO_EMAIL=
ONVIO_PASSWORD=
ONVIO_BROWSER=chrome
ONVIO_HEADLESS=0
ONVIO_USER_DATA_DIR=storage/onvio_browser
ONVIO_WAIT_SECONDS=60
MICROSOFT_GRAPH_TENANT_ID=
MICROSOFT_GRAPH_CLIENT_ID=
MICROSOFT_GRAPH_CLIENT_SECRET=
MICROSOFT_GRAPH_USER_EMAIL=
MICROSOFT_GRAPH_LOOKBACK_MINUTES=10
MICROSOFT_GRAPH_POLL_SECONDS=45
```

Use `ONVIO_HEADLESS=0` para teste assistido, porque o navegador aparece na tela.

As variaveis `MICROSOFT_GRAPH_*` permitem buscar automaticamente no e-mail o codigo de verificacao enviado pelo Onvio. Se elas nao estiverem configuradas, o teste continua em modo manual: o navegador fica aberto para o usuario digitar o codigo.

## Rodar teste assistido

```bash
.venv/bin/python scripts/testar_entrada_onvio.py
```

O script abre o navegador, tenta autenticar no Onvio e mostra o estado final.

Se o Onvio pedir codigo de verificacao e ainda nao houver provedor de codigo configurado, digite o codigo manualmente no navegador aberto. Depois podemos automatizar essa parte com a mesma ideia usada no sistema SN, mas nao nesta primeira etapa.

## Cuidados

- Nao envie senha Onvio ao GitHub, Codex ou ChatGPT.
- Nao rode em producao como processo continuo nesta etapa.
- Use um navegador por vez.
- Se o teste falhar, observe a tela e anote em qual etapa parou.
