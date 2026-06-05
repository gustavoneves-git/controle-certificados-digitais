# controle-certificados-digitais

Sistema interno Mark 1 para controle manual de certificados digitais de clientes de um escritorio contabil.

## O que a Mark 1 faz

O usuario cadastra um arquivo `.pfx` ou `.p12`, informa a senha e, quando souber, os dados do contato. O sistema le os dados reais do certificado, controla vencimentos, guarda o arquivo para download futuro, protege a senha e gera mensagens manuais para o cliente.

Funcionalidades entregues:

- Dashboard com totais por status.
- Cadastro manual de certificado `.pfx` ou `.p12`.
- Leitura real do arquivo PKCS#12 com `cryptography`.
- Extracao de subject, issuer, emissao, validade, serial, SHA1, SHA256, CNPJ/CPF quando possivel e nome extraido.
- Armazenamento do `.pfx` para download futuro.
- Criptografia da senha do certificado com chave do `.env`.
- Auditoria de cadastro, senha invalida, senha visualizada, senha copiada, download e mensagem gerada.
- Lista e detalhe dos certificados.
- Edicao de contato, e-mail, RG/CNH, senha salva e substituicao manual do arquivo do certificado.
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

## Entrada Onvio assistida

A etapa inicial de Mark 2 para entrada/login no Onvio fica documentada em `docs/ENTRADA_ONVIO_ASSISTIDA.md`.

Esta etapa apenas abre o navegador e valida autenticação assistida. Ela nao busca contato, nao abre conversa e nao envia mensagem.

## Regras centrais

- A validade oficial vem da leitura interna do `.pfx`.
- A validade nunca vem do nome do arquivo.
- Campos opcionais, como e-mail ou titular/responsavel, so aparecem quando existem dentro do certificado.
- A Mark 1 nao usa OCR, MMC, Outlook, OneDrive, Graph API, Onvio, Messenger, WhatsApp API ou Selenium.
- CNPJ/CPF extraido do certificado identifica a empresa/certificado.
- Tipo de certificado separado entre `e-CNPJ` e `e-CPF`, conforme o documento extraido de dentro do arquivo.
- Telefone identifica o canal de atendimento. Visualmente use `+55 11 99999-9999`; internamente o sistema salva somente numeros, por exemplo `5511999999999`, para busca futura.
- Nome do contato personaliza a mensagem.
- E-mail e RG/CNH do contato podem ser guardados para apoiar emissao ou renovacao.
- Sexo do contato e opcional e usado somente para tratamento na mensagem: `Sr.` para homem e `Sra.` para mulher.

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

## Deploy em Oracle

Para publicar em producao com o dominio:

```text
https://legal.consistecontabilidade.com
```

use o roteiro em `docs/DEPLOY_ORACLE.md`.

Resumo do apontamento DNS:

```text
legal.consistecontabilidade.com -> 163.176.226.185
```

A entrada WSGI de producao e:

```text
wsgi:app
```

Em producao, mantenha `.env`, banco, certificados `.pfx` e backups somente no servidor, fora do Git.

## Backup em producao

Antes de qualquer atualizacao em producao, faca backup de:

```text
data/app.db
storage/certificados/
storage/certificados_arquivados/
storage/documentos_identificacao/
.env
```

Comando recomendado na Oracle:

```bash
cd /opt/consiste/legal-certificados
.venv/bin/python scripts/backup_mark1.py --backup-dir /opt/consiste/backups/legal-certificados
```

Por padrao, o script mantem apenas os 3 backups locais mais recentes.

Para backup criptografado em nuvem compartilhada, configure `BACKUP_ENCRYPTION_KEY` no `.env` e gere um arquivo `.tar.gz.enc`:

```bash
.venv/bin/python scripts/backup_mark1.py \
  --backup-dir /opt/consiste/backups/legal-certificados-nuvem \
  --encrypt \
  --delete-plain
```

O roteiro completo de backup, nuvem criptografada e restauracao esta em `docs/RECUPERACAO_MARK_1.md`.

## Reprocessar dados tecnicos

Quando a regra de leitura do certificado evoluir, use o script abaixo para reler arquivos ja cadastrados sem alterar contato, telefone, observacao, senha ou arquivo:

```bash
.venv/bin/python scripts/reprocessar_certificados_tecnicos.py
```

Por padrao ele roda em modo previa e nao grava nada. Para aplicar depois de revisar a previa e fazer backup:

```bash
.venv/bin/python scripts/reprocessar_certificados_tecnicos.py --apply
```

Para testar apenas um cadastro:

```bash
.venv/bin/python scripts/reprocessar_certificados_tecnicos.py --certificado-id 80
```

Login padrao da Mark 1:

- configure `APP_LOGIN_USER` no `.env`;
- configure `APP_LOGIN_PASSWORD_HASH` no `.env`.

Para gerar o hash da senha local:

```bash
.venv/bin/python scripts/gerar_hash_senha.py
```

Copie o hash impresso para `APP_LOGIN_PASSWORD_HASH`. A Mark 1 usa login simples nesta fase, sem cadastro de usuarios.

## Cadastro de certificado

Na tela "Novo certificado", envie um `.pfx` ou `.p12` e informe a senha. Nome do contato, sexo do contato, e-mail, RG/CNH, telefone e observacao sao opcionais. A senha e testada contra o arquivo; se estiver incorreta, o cadastro fica com status `SENHA_INVALIDA` e um evento de auditoria e registrado.

O campo `Sexo do contato` e opcional. Quando preenchido como homem ou mulher, a mensagem gerada usa `Sr.` ou `Sra.` antes do nome. Se ficar como nao informado, a mensagem usa o nome exatamente como foi cadastrado.

Na tela "Editar certificado", e possivel atualizar dados do contato, e-mail, RG/CNH, telefone, observacao e senha salva. Tambem e possivel enviar um novo `.pfx` ou `.p12` para substituir o certificado daquele cadastro. Nesse caso o sistema:

- exige a senha do novo certificado;
- abre o arquivo antes de salvar;
- bloqueia a troca se o CNPJ/CPF do novo certificado for diferente do cadastro atual;
- arquiva o arquivo anterior em `storage/certificados_arquivados/`;
- registra auditoria da atualizacao e do arquivamento.

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
3. Envie um arquivo real `.pfx` ou `.p12`.
4. Informe a senha correta do certificado.
5. Preencha o nome do contato e o telefone limpo, por exemplo `916031398`.
6. Salve e confira a tela de detalhe.

Na tela de detalhe, valide:

- `Subject` e `Issuer`.
- Data de emissao e data de validade.
- Serial number.
- Thumbprint SHA1 e SHA256.
- CNPJ/CPF extraido, quando o certificado trouxer essa informacao.
- Tipo do certificado: `e-CNPJ`, `e-CPF` ou `DESCONHECIDO`.
- E-mail ou titular/responsavel, somente quando o certificado trouxer esses dados de forma confiavel.
- Status calculado pela data real do certificado.

Se a senha estiver errada ou o arquivo nao for um `.pfx` valido, o sistema nao deve quebrar. O registro fica como `SENHA_INVALIDA` e a validade permanece vazia, mesmo que o nome do arquivo contenha alguma data.

## Telefone

Use o telefone em formato familiar, com DDI e DDD. Exemplo aceito: `+55 11 99999-9999`.

Ao salvar, o sistema guarda internamente apenas os numeros, por exemplo `5511999999999`. Esse formato interno sera usado em uma futura busca automatizada, mas a tela continua mostrando o telefone formatado.

Nome, sexo do contato e telefone podem ficar em branco quando o responsavel ainda nao foi identificado. Nesse caso, o certificado fica cadastrado e aparece no filtro `Sem contato` para completar depois.

Exemplos rejeitados:

- `+55 91603-1398`
- `47 91603-1398`
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
- `VERIFICAR`: informacao essencial ausente.

Status de contato:

- `COM_CONTATO`: nome, sexo do contato e telefone limpo preenchidos.
- `SEM_CONTATO`: falta nome do contato, sexo do contato ou telefone limpo.

## Substituicao por CNPJ/CPF

Ao cadastrar um novo `.pfx`, o sistema sempre le o certificado antes de decidir. Se o CNPJ/CPF for identificado e ja existir um certificado `ATIVO` para o mesmo documento:

- validade nova maior: o certificado antigo vira `SUBSTITUIDO` e o novo fica `ATIVO`;
- validade nova menor ou igual: o cadastro e bloqueado e nada novo fica ativo;
- documento nao identificado: o certificado fica `VERIFICAR` e nao participa da substituicao automatica.

Quando um certificado e substituido, o arquivo `.pfx` antigo e movido automaticamente para `storage/certificados_arquivados/`. O registro antigo permanece no banco como historico, com auditoria. No detalhe de um certificado `SUBSTITUIDO`, existe uma acao manual para excluir definitivamente o arquivo arquivado, com confirmacao.

Dashboard e lista principal consideram apenas certificados `ATIVO` por padrao. Certificados `SUBSTITUIDO` ficam disponiveis pelo filtro da lista e nao entram como pendencia principal.

## Uso operacional da lista

A tela de certificados abre em `Ativos` por padrao. Use os filtros rapidos para revisar:

- `Ativos`: certificados principais em uso.
- `Vencidos`: ativos com validade expirada.
- `Vencem em 15 dias`: ativos que precisam de renovacao imediata.
- `Validos`: ativos com mais de 15 dias de validade.
- `Verificar`: registros que precisam de revisao manual.
- `Sem contato`: ativos com nome do contato, sexo do contato ou telefone limpo pendente.
- `Senha invalida`: registros cujo `.pfx` nao abriu com a senha informada.
- `Substituidos`: historico de certificados trocados por versoes mais novas.
- `Todos`: visao completa para conferencia.

A busca aceita CNPJ/CPF, nome extraido, nome do contato e telefone limpo.

Use o seletor `Todos / e-CNPJ / e-CPF` na lista para alternar rapidamente entre certificados de empresa e certificados de pessoa fisica sem perder o filtro principal.

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
- A pasta `storage/certificados_arquivados` e ignorada pelo Git.
- O banco `data/*.db` e ignorado pelo Git.
- A pasta `tmp/` e ignorada pelo Git.
- Arquivos `.pfx` nao devem ser enviados ao repositorio.
- Visualizar/copiar senha e baixar certificado registra auditoria.
- A resposta que mostra senha usa `Cache-Control: no-store`.
- A sessao expira automaticamente e o cookie de sessao usa `HttpOnly`, `SameSite=Lax` e `Secure` em producao.
- As paginas internas enviam headers de seguranca como `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` e HSTS em HTTPS.
- O download so e permitido para arquivos dentro da pasta configurada em `STORAGE_CERTIFICADOS`.
- Evite usar certificados reais em ambiente compartilhado sem controle de acesso ao computador.
- Proximas melhorias recomendadas: protecao CSRF em formularios, limite de tentativas de login e, se o uso crescer, autenticacao em duas etapas ou acesso por VPN/rede restrita.

## Testes

```bash
pytest
```

Se estiver usando a `.venv` criada no projeto:

```bash
.venv/bin/python -m pytest
```
