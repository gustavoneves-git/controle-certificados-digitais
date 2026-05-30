# Teste real assistido da Mark 1

Use este roteiro para validar a Mark 1 com certificados `.pfx` reais em ambiente controlado.

## Antes de comecar

- [ ] Confirme que `.env`, `data/*.db` e `storage/certificados/*` estao ignorados pelo Git.
- [ ] Use somente certificados autorizados para teste.
- [ ] Nao envie certificados reais, banco real ou `.env` para o repositorio.
- [ ] Rode o sistema localmente com `python run.py`.
- [ ] Acesse `http://127.0.0.1:5000`.

## Teste com certificado real e senha correta

- [ ] Abra a tela `Certificados > Novo certificado`.
- [ ] Suba um arquivo `.pfx` real.
- [ ] Informe a senha correta.
- [ ] Informe o nome do contato.
- [ ] Informe telefone limpo, por exemplo `916031398`.
- [ ] Salve o cadastro.
- [ ] Confirme que o sistema abriu a tela de detalhe sem erro.
- [ ] Confira o nome/razao social extraido.
- [ ] Confira o CNPJ/CPF extraido.
- [ ] Confira a data de emissao.
- [ ] Confira a data de validade.
- [ ] Confira o emissor.
- [ ] Confira o status calculado.
- [ ] Na secao `Diagnostico tecnico`, confirme `Origem da validade: CERTIFICADO_PFX`.
- [ ] Na secao `Diagnostico tecnico`, confira documento extraido, tipo do documento, dias ate vencer, SHA1, SHA256 e serial number.
- [ ] Teste o botao `Mostrar` senha.
- [ ] Teste o botao `Copiar` senha.
- [ ] Teste o download do certificado.
- [ ] Teste o botao `Gerar mensagem`.
- [ ] Confirme que a mensagem usa contato, empresa, CNPJ/CPF e data correta.
- [ ] Volte ao dashboard e valide os totais.
- [ ] Valide as cores de status: vermelho para vencido, amarelo para vence em 15 dias, verde para valido e cinza para verificar, senha invalida ou sem telefone.

## Teste com senha errada

- [ ] Cadastre um `.pfx` real informando senha incorreta.
- [ ] Confirme que o sistema nao quebra.
- [ ] Confirme que a tela mostra: `Nao foi possivel abrir o certificado. Verifique se a senha esta correta.`
- [ ] Confirme que o status fica `SENHA_INVALIDA`.
- [ ] Confirme que o certificado nao entra como `VALIDO`.
- [ ] Confirme que a auditoria registra `SENHA_INVALIDA`.
- [ ] Confirme que a senha nao aparece no terminal, em logs ou em mensagens de erro.

## Teste com arquivo invalido

- [ ] Tente cadastrar um arquivo que nao seja `.pfx`.
- [ ] Confirme que a tela mostra: `O arquivo enviado nao parece ser um certificado .pfx valido.`
- [ ] Tente cadastrar um arquivo com extensao `.pfx`, mas conteudo invalido.
- [ ] Confirme que o sistema nao quebra.
- [ ] Confirme que o status fica `SENHA_INVALIDA`.
- [ ] Confirme que a validade fica vazia e nao e extraida do nome do arquivo.

## Teste de telefone limpo

- [ ] Teste telefone com `+55`, exemplo `+55916031398`.
- [ ] Teste telefone com DDD, exemplo `47916031398`.
- [ ] Teste telefone com espaco, exemplo `91603 1398`.
- [ ] Teste telefone com traco, exemplo `91603-1398`.
- [ ] Teste telefone com parenteses, exemplo `(47)916031398`.
- [ ] Teste telefone com letras, exemplo `abc916031398`.
- [ ] Confirme que todos os formatos acima deixam o campo invalido e bloqueiam o botao salvar.
- [ ] Teste telefone limpo correto: `916031398`.
- [ ] Confirme que o campo fica valido e libera o botao salvar.

## Diagnostico local sem cadastro

Use o comando abaixo quando quiser inspecionar um `.pfx` sem salvar no banco e sem copiar o arquivo:

```bash
python scripts/diagnosticar_certificado.py caminho/arquivo.pfx
```

- [ ] Confirme que o terminal pede a senha de forma oculta.
- [ ] Confirme que a senha nao e impressa.
- [ ] Confira nome extraido, CNPJ/CPF, tipo documento, emissao, validade, emissor, SHA1 e SHA256.
- [ ] Confirme que nada foi salvo no banco.
- [ ] Confirme que o arquivo nao foi copiado para `storage/certificados`.

## Resultado esperado

Ao final, a Mark 1 deve permitir controle manual confiavel de certificados reais, sem nenhuma integracao externa, sem envio automatico e sem versionar dados sensiveis.
