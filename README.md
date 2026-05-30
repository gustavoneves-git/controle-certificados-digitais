# controle-certificados-digitais

Sistema interno Mark 1 para controle manual de certificados digitais de clientes de um escritorio contabil.

## O que a Mark 1 faz

O usuario cadastra um arquivo `.pfx`, informa a senha, o nome do contato e o telefone limpo usado para busca futura no Messenger/WhatsApp. O sistema le os dados reais do certificado, controla vencimentos, guarda o arquivo para download futuro, protege a senha e gera mensagens manuais para o cliente.

Funcionalidades entregues:

- Dashboard com totais por status.
- Cadastro manual de certificado `.pfx`.
- Leitura real do `.pfx` com `cryptography`.
- Extracao de subject, issuer, emissao, validade, serial, SHA1, SHA256, CNPJ/CPF quando possivel e nome extraido.
- Armazenamento do `.pfx` para download futuro.
- Criptografia da senha do certificado com chave do `.env`.
- Auditoria de cadastro, senha invalida, senha visualizada, senha copiada, download e mensagem gerada.
- Lista e detalhe dos certificados.
- Geracao manual de mensagem para cliente.
- Controle de substituicao: no maximo um certificado `ATIVO` por CNPJ/CPF.

## O que a Mark 1 ainda nao faz

- Nao entra no Onvio.
- Nao usa Selenium.
- Nao envia WhatsApp automaticamente.
- Nao envia Messenger automaticamente.
- Nao usa Graph API.
- Nao busca arquivos no Outlook ou OneDrive.
- Nao usa OCR.
- Nao depende do MMC.

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

Nunca versione o `.env`. Ele contem a chave que permite descriptografar as senhas salvas.

## Banco de dados

```bash
python scripts/init_db.py
```

O banco SQLite padrao fica em `data/app.db`.

Nesta fase de desenvolvimento, se um banco local antigo ficar incompatível com o schema atual, recrie o banco removendo `data/app.db` e executando `python scripts/init_db.py` novamente. Nao faca isso com uma base real sem backup.

## Rodar o sistema

```bash
python run.py
```

Acesse `http://127.0.0.1:5000`.

Login padrao da Mark 1:

- Usuario: `legal`
- Senha: `consiste`

Esses valores podem ser alterados no `.env` com `LOGIN_USUARIO` e `LOGIN_SENHA`.

## Cadastro de certificado

Na tela "Novo certificado", envie um `.pfx`, informe a senha, o nome do contato, o telefone limpo e uma observacao opcional. A senha e testada contra o arquivo; se estiver incorreta, o cadastro fica com status `SENHA_INVALIDA` e um evento de auditoria e registrado.

## Certificados ficticios para desenvolvimento

Nunca envie certificados reais ao GitHub, Codex ou ChatGPT. Certificados reais tambem nao devem ser usados em testes versionados.

Para desenvolvimento, gere certificados `.pfx` ficticios e autossinados:

```bash
.venv/bin/python scripts/gerar_certificados_teste.py
```

Os arquivos sao criados em `tmp/certificados_teste/`, pasta ignorada pelo Git. A senha ficticia padrao e `teste123`.

Arquivos gerados:

- `empresa_teste_valido.pfx`
- `empresa_teste_vencido.pfx`
- `empresa_teste_vence_15_dias.pfx`
- `empresa_substituicao_antigo.pfx`
- `empresa_substituicao_novo.pfx`

Todos usam nomes e CNPJs ficticios, apenas para validar leitura, status, extracao de documento e cenarios de substituicao futura.

## Como testar com certificado real

1. Inicie o servidor local.
2. Acesse `http://127.0.0.1:5000/certificados/novo`.
3. Envie um arquivo real `.pfx`.
4. Informe a senha correta do certificado.
5. Preencha o nome do contato e o telefone limpo, por exemplo `916031398`.
6. Salve e confira a tela de detalhe.

Na tela de detalhe, valide:

- `Subject` e `Issuer`.
- Data de emissao e data de validade.
- Serial number.
- Thumbprint SHA1 e SHA256.
- CNPJ/CPF extraido, quando o certificado trouxer essa informacao.
- Status calculado pela data real do certificado.

Se a senha estiver errada ou o arquivo nao for um `.pfx` valido, o sistema nao deve quebrar. O registro fica como `SENHA_INVALIDA` e a validade permanece vazia, mesmo que o nome do arquivo contenha alguma data.

## Telefone limpo

Use apenas o numero sem DDD, sem `+55`, sem espacos, sem tracos, sem parenteses e sem letras. Exemplo aceito: `916031398`.

Exemplos rejeitados:

- `+55916031398`
- `47916031398`
- `91603-1398`
- `(47)916031398`
- `91603 1398`
- `abc916031398`

## Validade do certificado

A validade usada pelo sistema vem exclusivamente da leitura interna do arquivo `.pfx`. O nome do arquivo nunca e usado para definir data de emissao, data de validade ou status.

## Status

Status de registro:

- `ATIVO`: certificado principal daquele CNPJ/CPF.
- `SUBSTITUIDO`: certificado antigo mantido apenas como historico.
- `VERIFICAR`: certificado que precisa de revisao manual, por exemplo sem documento identificado ou senha invalida.

Status de vencimento:

- `VENCIDO`: validade menor que hoje.
- `VENCE_EM_15_DIAS`: validade entre hoje e 15 dias, incluindo certificados que vencem hoje.
- `VALIDO`: validade acima de 15 dias.
- `SENHA_INVALIDA`: senha nao abre o `.pfx`.
- `SEM_TELEFONE`: telefone vazio ou invalido.
- `VERIFICAR`: informacao essencial ausente.

## Substituicao por CNPJ/CPF

Ao cadastrar um novo `.pfx`, o sistema sempre le o certificado antes de decidir. Se o CNPJ/CPF for identificado e ja existir um certificado `ATIVO` para o mesmo documento:

- validade nova maior: o certificado antigo vira `SUBSTITUIDO` e o novo fica `ATIVO`;
- validade nova menor ou igual: o cadastro e bloqueado e nada novo fica ativo;
- documento nao identificado: o certificado fica `VERIFICAR` e nao participa da substituicao automatica.

Quando um certificado e substituido, o arquivo `.pfx` antigo e removido automaticamente do storage para evitar uso operacional do certificado vencido/antigo. O registro antigo permanece no banco como historico, com auditoria.

Dashboard e lista principal consideram apenas certificados `ATIVO` por padrao. Certificados `SUBSTITUIDO` ficam disponiveis pelo filtro da lista e nao entram como pendencia principal.

## Uso operacional da lista

A tela de certificados abre em `Ativos` por padrao. Use os filtros rapidos para revisar:

- `Ativos`: certificados principais em uso.
- `Vencidos`: ativos com validade expirada.
- `Vencem em 15 dias`: ativos que precisam de renovacao imediata.
- `Validos`: ativos com mais de 15 dias de validade.
- `Verificar`: registros que precisam de revisao manual.
- `Sem telefone`: ativos sem telefone limpo valido.
- `Senha invalida`: registros cujo `.pfx` nao abriu com a senha informada.
- `Substituidos`: historico de certificados trocados por versoes mais novas.
- `Todos`: visao completa para conferencia.

A busca aceita CNPJ/CPF, nome extraido, nome do contato e telefone limpo.

## Fluxo recomendado de renovacao

1. Filtre por `Vencem em 15 dias` ou `Vencidos`.
2. Abra o detalhe e gere a mensagem para contato manual.
3. Quando receber o novo `.pfx`, cadastre normalmente.
4. Se o novo certificado tiver o mesmo CNPJ/CPF e validade maior, ele fica `ATIVO` e o antigo vira `SUBSTITUIDO`.
5. Se a validade for menor ou igual ao certificado ativo, o sistema bloqueia a substituicao automatica.
6. Use o filtro `Substituidos` apenas para historico e conferencia.

## Seguranca

- A senha do certificado nunca e salva em texto puro.
- `CERT_PASSWORD_KEY` deve ser uma chave Fernet valida e deve ficar somente no `.env`.
- A pasta `storage/certificados` e ignorada pelo Git.
- O banco `data/*.db` e ignorado pelo Git.
- A pasta `tmp/` e ignorada pelo Git.
- Arquivos `.pfx` nao devem ser enviados ao repositorio.
- Visualizar/copiar senha e baixar certificado registra auditoria.
- A resposta que mostra senha usa `Cache-Control: no-store`.
- O download so e permitido para arquivos dentro da pasta configurada em `STORAGE_CERTIFICADOS`.
- Evite usar certificados reais em ambiente compartilhado sem controle de acesso ao computador.

## Testes

```bash
pytest
```

Se estiver usando a `.venv` criada no projeto:

```bash
.venv/bin/python -m pytest
```
