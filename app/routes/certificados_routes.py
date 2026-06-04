from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from pathlib import Path

from app.repositories import auditoria_repository as auditoria
from app.repositories import certificado_repository as certificados
from app.services.certificado_reader_service import SenhaCertificadoInvalida, ler_pfx
from app.services.certificado_storage_service import (
    arquivar_certificado,
    caminho_permitido,
    extensao_valida,
    remover_certificado,
    salvar_certificado,
)
from app.services.crypto_service import criptografar_senha, descriptografar_senha
from app.services.telefone_service import (
    TELEFONE_INSTRUCAO,
    is_telefone_limpo_valido,
    normalizar_telefone,
)
from app.services.vencimento_service import (
    SENHA_INVALIDA,
    SEM_CONTATO,
    VERIFICAR,
    calcular_status,
    calcular_status_contato,
    dias_para_vencer,
    parse_date,
    status_class,
)

certificados_bp = Blueprint("certificados", __name__, url_prefix="/certificados")


@certificados_bp.route("/")
def listar():
    filtro = request.args.get("filtro") or request.args.get("status_registro", "ATIVO")
    busca = request.args.get("busca", "").strip()
    tipo = request.args.get("tipo", "TODOS")
    tipos = {"TODOS", "e-CNPJ", "e-CPF"}
    if tipo not in tipos:
        tipo = "TODOS"
    filtros = {
        "ATIVO": ("ATIVO", None),
        "VENCIDO": ("ATIVO", "VENCIDO"),
        "VENCE_EM_15_DIAS": ("ATIVO", "VENCE_EM_15_DIAS"),
        "VALIDO": ("ATIVO", "VALIDO"),
        "VERIFICAR": ("VERIFICAR", None),
        "SEM_CONTATO": ("ATIVO", None),
        "SENHA_INVALIDA": ("VERIFICAR", "SENHA_INVALIDA"),
        "SUBSTITUIDO": ("SUBSTITUIDO", None),
        "TODOS": (None, None),
    }
    if filtro not in filtros:
        filtro = "ATIVO"
    status_registro, status_vencimento = filtros[filtro]
    status_contato = SEM_CONTATO if filtro == "SEM_CONTATO" else None
    registros = certificados.list_certificados(
        status_registro=status_registro,
        status_vencimento=status_vencimento,
        status_contato=status_contato,
        tipo_documento=None if tipo == "TODOS" else tipo,
        busca=busca,
    )
    return render_template(
        "certificados.html",
        certificados=registros,
        dias_para_vencer=dias_para_vencer,
        status_class=status_class,
        filtro=filtro,
        busca=busca,
        tipo=tipo,
    )


@certificados_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "GET":
        return render_template("novo_certificado.html", instrucao=TELEFONE_INSTRUCAO)

    arquivo = request.files.get("arquivo")
    senha = request.form.get("senha", "")
    nome_contato = request.form.get("nome_contato", "").strip()
    sexo_contato = request.form.get("sexo_contato", "").strip().upper()
    email_contato = request.form.get("email_contato", "").strip()
    documento_identificacao = request.form.get("documento_identificacao", "").strip()
    telefone_limpo = normalizar_telefone(request.form.get("telefone_limpo", "").strip())
    observacao = request.form.get("observacao", "").strip()

    if sexo_contato not in {"", "HOMEM", "MULHER"}:
        sexo_contato = ""

    if not arquivo or not extensao_valida(arquivo.filename):
        flash("O arquivo enviado nao parece ser um certificado .pfx ou .p12 valido.", "danger")
        return redirect(url_for("certificados.novo"))

    telefone_valido = not telefone_limpo or is_telefone_limpo_valido(telefone_limpo)

    if not telefone_valido:
        flash("Telefone invalido. Use o formato +55 11 99999-9999 ou deixe em branco para preencher depois.", "danger")
        return redirect(url_for("certificados.novo"))
    conteudo = arquivo.read()
    arquivo.seek(0)
    senha_criptografada = criptografar_senha(senha)
    status_registro = "ATIVO"
    substituido_por_id = None
    substituido_em = None
    certificado_ativo_existente = None

    try:
        dados_certificado = ler_pfx(conteudo, senha)
        if not telefone_limpo:
            telefone_certificado = normalizar_telefone(dados_certificado.get("telefone_certificado"))
            if telefone_certificado and is_telefone_limpo_valido(telefone_certificado):
                telefone_limpo = telefone_certificado
        status_vencimento = calcular_status(
            dados_certificado.get("data_validade"),
            essencial_ok=bool(dados_certificado.get("subject")),
        )
        if not dados_certificado.get("cnpj_cpf"):
            status_registro = "VERIFICAR"
            status_vencimento = VERIFICAR
        certificado_ativo_existente = certificados.get_ativo_by_documento(dados_certificado.get("cnpj_cpf"))
        if certificado_ativo_existente:
            validade_nova = parse_date(dados_certificado.get("data_validade"))
            validade_atual = parse_date(certificado_ativo_existente["data_validade"])
            if validade_nova is None or validade_atual is None or validade_nova <= validade_atual:
                auditoria.registrar_evento(
                    certificado_ativo_existente["id"],
                    "TENTATIVA_SUBSTITUICAO_BLOQUEADA",
                    "Cadastro bloqueado porque ja existe certificado ativo com validade igual ou superior.",
                )
                flash(
                    "Ja existe um certificado ativo para este CNPJ/CPF com validade igual ou superior.",
                    "warning",
                )
                return redirect(url_for("certificados.detalhe", certificado_id=certificado_ativo_existente["id"]))
    except SenhaCertificadoInvalida:
        dados_certificado = {
            "subject": None,
            "issuer": None,
            "data_emissao": None,
            "data_validade": None,
            "thumbprint_sha1": None,
            "thumbprint_sha256": None,
            "serial_number": None,
            "cnpj_cpf": None,
            "tipo_documento": "DESCONHECIDO",
            "nome_extraido": None,
            "email_certificado": None,
            "telefone_certificado": None,
            "responsavel_certificado": None,
        }
        status_registro = "VERIFICAR"
        status_vencimento = SENHA_INVALIDA
        flash("Nao foi possivel abrir o certificado. Verifique se a senha esta correta.", "danger")
        flash("O arquivo enviado nao parece ser um certificado .pfx ou .p12 valido.", "warning")

    status_contato = calcular_status_contato(nome_contato, sexo_contato, telefone_limpo)
    caminho = salvar_certificado(arquivo, current_app.config["STORAGE_CERTIFICADOS"])
    certificado_id = certificados.create_certificado(
        {
            "nome_arquivo_original": arquivo.filename,
            "caminho_arquivo": caminho,
            "senha_criptografada": senha_criptografada,
            "nome_contato": nome_contato,
            "sexo_contato": sexo_contato,
            "email_contato": email_contato,
            "documento_identificacao": documento_identificacao,
            "telefone_limpo": telefone_limpo,
            "observacao": observacao,
            "status": status_vencimento,
            "status_registro": status_registro,
            "status_vencimento": status_vencimento,
            "status_contato": status_contato,
            "substituido_por_id": substituido_por_id,
            "substituido_em": substituido_em,
            "arquivo_arquivado_em": None,
            **dados_certificado,
        }
    )

    auditoria.registrar_evento(certificado_id, "CERTIFICADO_CADASTRADO", "Certificado cadastrado manualmente.")
    if status_vencimento == SENHA_INVALIDA:
        auditoria.registrar_evento(certificado_id, "SENHA_INVALIDA", "Senha invalida ao abrir o arquivo .pfx.")
    if status_registro == "VERIFICAR" and not dados_certificado.get("cnpj_cpf") and status_vencimento != SENHA_INVALIDA:
        auditoria.registrar_evento(
            certificado_id,
            "DOCUMENTO_NAO_IDENTIFICADO",
            "Nao foi possivel extrair CNPJ/CPF do certificado.",
        )

    if certificado_ativo_existente and certificado_ativo_existente["id"] != certificado_id:
        caminho_arquivado = arquivar_certificado(
            certificado_ativo_existente["caminho_arquivo"],
            current_app.config["STORAGE_CERTIFICADOS"],
            current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"],
        )
        certificados.marcar_substituido(
            certificado_ativo_existente["id"],
            certificado_id,
            caminho_arquivado,
        )
        arquivo_antigo_arquivado = caminho_arquivado is not None
        auditoria.registrar_evento(
            certificado_ativo_existente["id"],
            "CERTIFICADO_SUBSTITUIDO",
            f"Certificado substituido pelo cadastro #{certificado_id}.",
        )
        auditoria.registrar_evento(
            certificado_ativo_existente["id"],
            "CERTIFICADO_ARQUIVO_ARQUIVADO" if arquivo_antigo_arquivado else "ARQUIVO_CERTIFICADO_NAO_ENCONTRADO",
            "Arquivo .pfx antigo movido para storage de arquivados."
            if arquivo_antigo_arquivado
            else "Arquivo .pfx antigo nao foi encontrado para arquivamento.",
        )
        auditoria.registrar_evento(
            certificado_id,
            "CERTIFICADO_SUBSTITUIDO",
            f"Este certificado substituiu o cadastro #{certificado_ativo_existente['id']}.",
        )

    if status_vencimento != SENHA_INVALIDA:
        flash("Certificado cadastrado.", "success")
    pendencias_contato = []
    if not nome_contato:
        pendencias_contato.append("nome do contato")
    if not sexo_contato:
        pendencias_contato.append("sexo do contato")
    if not telefone_limpo:
        pendencias_contato.append("telefone")
    if pendencias_contato:
        flash(
            "Atencao: certificado salvo com pendencia de contato: "
            + ", ".join(pendencias_contato)
            + ". Complete depois pelo filtro Sem contato ou pela conferencia operacional.",
            "warning",
        )
    return redirect(url_for("certificados.detalhe", certificado_id=certificado_id))


@certificados_bp.route("/<int:certificado_id>")
def detalhe(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))
    eventos = auditoria.listar_eventos(certificado_id)
    return render_template(
        "detalhe_certificado.html",
        certificado=certificado,
        eventos=eventos,
        dias_para_vencer=dias_para_vencer,
        status_class=status_class,
    )


@certificados_bp.route("/<int:certificado_id>/editar", methods=["GET", "POST"])
def editar(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))

    if request.method == "GET":
        return render_template("editar_certificado.html", certificado=certificado)

    nome_contato = request.form.get("nome_contato", "").strip()
    sexo_contato = request.form.get("sexo_contato", "").strip().upper()
    email_contato = request.form.get("email_contato", "").strip()
    documento_identificacao = request.form.get("documento_identificacao", "").strip()
    telefone_limpo = normalizar_telefone(request.form.get("telefone_limpo", "").strip())
    observacao = request.form.get("observacao", "").strip()
    senha = request.form.get("senha", "")
    arquivo = request.files.get("arquivo")

    if sexo_contato not in {"", "HOMEM", "MULHER"}:
        sexo_contato = ""
    if telefone_limpo and not is_telefone_limpo_valido(telefone_limpo):
        flash("Telefone invalido. Use o formato +55 11 99999-9999 ou deixe em branco.", "danger")
        return redirect(url_for("certificados.editar", certificado_id=certificado_id))

    status_contato = calcular_status_contato(nome_contato, sexo_contato, telefone_limpo)

    troca_certificado = arquivo is not None and arquivo.filename
    if troca_certificado:
        if not extensao_valida(arquivo.filename):
            flash("O arquivo enviado nao parece ser um certificado .pfx ou .p12 valido.", "danger")
            return redirect(url_for("certificados.editar", certificado_id=certificado_id))
        if not senha:
            flash("Informe a senha do novo certificado para validar a substituicao.", "danger")
            return redirect(url_for("certificados.editar", certificado_id=certificado_id))
        conteudo = arquivo.read()
        arquivo.seek(0)
        try:
            dados_certificado = ler_pfx(conteudo, senha)
        except SenhaCertificadoInvalida:
            auditoria.registrar_evento(
                certificado_id,
                "SENHA_INVALIDA",
                "Senha invalida ao tentar substituir o certificado pela tela de edicao.",
            )
            flash("Nao foi possivel abrir o certificado. Verifique se a senha esta correta.", "danger")
            return redirect(url_for("certificados.editar", certificado_id=certificado_id))

        documento_atual = certificado["cnpj_cpf"]
        documento_novo = dados_certificado.get("cnpj_cpf")
        if documento_atual and documento_novo and documento_atual != documento_novo:
            auditoria.registrar_evento(
                certificado_id,
                "TENTATIVA_SUBSTITUICAO_BLOQUEADA",
                "Substituicao bloqueada porque o CNPJ/CPF do novo certificado e diferente.",
            )
            flash("O CNPJ/CPF do novo certificado e diferente deste cadastro. Revise antes de substituir.", "danger")
            return redirect(url_for("certificados.editar", certificado_id=certificado_id))

        validade_nova = parse_date(dados_certificado.get("data_validade"))
        validade_atual = parse_date(certificado["data_validade"])
        if validade_atual and validade_nova and validade_nova <= validade_atual:
            auditoria.registrar_evento(
                certificado_id,
                "TENTATIVA_SUBSTITUICAO_BLOQUEADA",
                "Substituicao bloqueada porque a validade do novo certificado e menor ou igual a atual.",
            )
            flash("O novo certificado nao tem validade maior que o atual. Revise antes de substituir.", "warning")
            return redirect(url_for("certificados.editar", certificado_id=certificado_id))

        status_vencimento = calcular_status(
            dados_certificado.get("data_validade"),
            essencial_ok=bool(dados_certificado.get("subject")),
        )
        status_registro = certificado["status_registro"]
        if status_registro != "SUBSTITUIDO":
            status_registro = "ATIVO" if dados_certificado.get("cnpj_cpf") else "VERIFICAR"
        if not dados_certificado.get("cnpj_cpf"):
            status_vencimento = VERIFICAR

        caminho = salvar_certificado(arquivo, current_app.config["STORAGE_CERTIFICADOS"])
        caminho_arquivado = arquivar_certificado(
            certificado["caminho_arquivo"],
            current_app.config["STORAGE_CERTIFICADOS"],
            current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"],
        )

        certificados.update_certificado(
            certificado_id,
            {
                "nome_arquivo_original": arquivo.filename,
                "caminho_arquivo": caminho,
                "senha_criptografada": criptografar_senha(senha),
                "nome_contato": nome_contato,
                "sexo_contato": sexo_contato,
                "email_contato": email_contato,
                "documento_identificacao": documento_identificacao,
                "telefone_limpo": telefone_limpo,
                "observacao": observacao,
                "status": status_vencimento,
                "status_registro": status_registro,
                "status_vencimento": status_vencimento,
                "status_contato": status_contato,
                **dados_certificado,
            },
        )
        auditoria.registrar_evento(
            certificado_id,
            "CERTIFICADO_ATUALIZADO",
            "Certificado substituido manualmente pela tela de edicao.",
        )
        auditoria.registrar_evento(
            certificado_id,
            "CERTIFICADO_ARQUIVO_ARQUIVADO" if caminho_arquivado else "ARQUIVO_CERTIFICADO_NAO_ENCONTRADO",
            "Arquivo .pfx anterior arquivado antes da substituicao."
            if caminho_arquivado
            else "Arquivo .pfx anterior nao foi encontrado para arquivamento.",
        )
        flash("Certificado atualizado com sucesso.", "success")
    else:
        data = {
            "nome_contato": nome_contato,
            "sexo_contato": sexo_contato,
            "email_contato": email_contato,
            "documento_identificacao": documento_identificacao,
            "telefone_limpo": telefone_limpo,
            "observacao": observacao,
            "status_contato": status_contato,
        }
        if senha:
            data["senha_criptografada"] = criptografar_senha(senha)
            certificados.update_senha(certificado_id, data["senha_criptografada"])
            auditoria.registrar_evento(
                certificado_id,
                "SENHA_CERTIFICADO_ATUALIZADA",
                "Senha do certificado atualizada manualmente pela tela de edicao.",
            )
        certificados.update_dados_contato(certificado_id, data)
        flash("Dados atualizados.", "success")

    auditoria.registrar_evento(
        certificado_id,
        "DADOS_CONTATO_ATUALIZADOS",
        "Dados de contato e emissao do certificado atualizados manualmente.",
    )
    if status_contato == SEM_CONTATO:
        flash("Atencao: ainda existem pendencias de contato neste certificado.", "warning")
    return redirect(url_for("certificados.detalhe", certificado_id=certificado_id))


@certificados_bp.route("/<int:certificado_id>/download")
def download(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))
    if not caminho_permitido(
        certificado["caminho_arquivo"], current_app.config["STORAGE_CERTIFICADOS"]
    ) and not caminho_permitido(
        certificado["caminho_arquivo"], current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"]
    ):
        flash("Arquivo .pfx nao encontrado no storage. Verifique se o certificado ainda existe na pasta configurada.", "warning")
        return redirect(url_for("certificados.detalhe", certificado_id=certificado_id))
    auditoria.registrar_evento(certificado_id, "CERTIFICADO_BAIXADO", "Arquivo .pfx baixado pelo usuario.")
    return send_file(
        Path(certificado["caminho_arquivo"]).resolve(),
        as_attachment=True,
        download_name=certificado["nome_arquivo_original"],
    )


@certificados_bp.route("/<int:certificado_id>/arquivo-arquivado/excluir", methods=["POST"])
def excluir_arquivo_arquivado(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))
    if certificado["status_registro"] != "SUBSTITUIDO":
        flash("Somente certificados substituidos podem ter arquivo arquivado excluido.", "warning")
        return redirect(url_for("certificados.detalhe", certificado_id=certificado_id))
    removido = remover_certificado(
        certificado["caminho_arquivo"],
        current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"],
    )
    if removido:
        certificados.registrar_arquivo_removido(certificado_id)
        auditoria.registrar_evento(
            certificado_id,
            "CERTIFICADO_ARQUIVO_REMOVIDO",
            "Arquivo .pfx arquivado removido manualmente.",
        )
        flash("Arquivo arquivado removido.", "success")
    else:
        flash("Arquivo arquivado nao encontrado.", "warning")
    return redirect(url_for("certificados.detalhe", certificado_id=certificado_id))


@certificados_bp.route("/<int:certificado_id>/excluir", methods=["POST"])
def excluir(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))

    removido = False
    if caminho_permitido(certificado["caminho_arquivo"], current_app.config["STORAGE_CERTIFICADOS"]):
        removido = remover_certificado(
            certificado["caminho_arquivo"],
            current_app.config["STORAGE_CERTIFICADOS"],
        )
    elif caminho_permitido(certificado["caminho_arquivo"], current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"]):
        removido = remover_certificado(
            certificado["caminho_arquivo"],
            current_app.config["STORAGE_CERTIFICADOS_ARQUIVADOS"],
        )

    auditoria.registrar_evento(
        certificado_id,
        "CERTIFICADO_EXCLUIDO",
        "Certificado excluido manualmente. Arquivo .pfx removido."
        if removido
        else "Certificado excluido manualmente. Arquivo .pfx nao localizado.",
    )
    certificados.delete_certificado(certificado_id)
    flash("Certificado excluido com sucesso.", "success")
    return redirect(url_for("certificados.listar", filtro="TODOS"))


@certificados_bp.route("/<int:certificado_id>/senha", methods=["POST"])
def mostrar_senha(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        return jsonify({"error": "Certificado nao encontrado"}), 404
    senha = descriptografar_senha(certificado["senha_criptografada"])
    auditoria.registrar_evento(certificado_id, "SENHA_VISUALIZADA", "Senha visualizada pelo usuario.")
    response = jsonify({"senha": senha})
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@certificados_bp.route("/<int:certificado_id>/senha/copiar", methods=["POST"])
def registrar_copia_senha(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        return jsonify({"error": "Certificado nao encontrado"}), 404
    auditoria.registrar_evento(certificado_id, "SENHA_COPIADA", "Senha copiada pelo usuario.")
    return jsonify({"ok": True})
