from flask import (
    Blueprint,
    current_app,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.repositories import auditoria_repository as auditoria
from app.repositories import certificado_repository as certificados
from app.services.certificado_reader_service import SenhaCertificadoInvalida, ler_pfx
from app.services.certificado_storage_service import (
    caminho_permitido,
    extensao_valida,
    salvar_certificado,
)
from app.services.crypto_service import criptografar_senha, descriptografar_senha
from app.services.telefone_service import TELEFONE_INSTRUCAO, is_telefone_limpo_valido
from app.services.vencimento_service import (
    SENHA_INVALIDA,
    calcular_status,
    dias_para_vencer,
    status_class,
)

certificados_bp = Blueprint("certificados", __name__, url_prefix="/certificados")


@certificados_bp.route("/")
def listar():
    registros = certificados.list_certificados()
    return render_template(
        "certificados.html",
        certificados=registros,
        dias_para_vencer=dias_para_vencer,
        status_class=status_class,
    )


@certificados_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "GET":
        return render_template("novo_certificado.html", instrucao=TELEFONE_INSTRUCAO)

    arquivo = request.files.get("arquivo")
    senha = request.form.get("senha", "")
    nome_contato = request.form.get("nome_contato", "").strip()
    telefone_limpo = request.form.get("telefone_limpo", "").strip()
    observacao = request.form.get("observacao", "").strip()

    if not arquivo or not extensao_valida(arquivo.filename):
        flash("Envie um arquivo .pfx valido.", "danger")
        return redirect(url_for("certificados.novo"))

    telefone_valido = is_telefone_limpo_valido(telefone_limpo)
    conteudo = arquivo.read()
    arquivo.seek(0)
    caminho = salvar_certificado(arquivo, current_app.config["STORAGE_CERTIFICADOS"])
    senha_criptografada = criptografar_senha(senha)

    try:
        dados_certificado = ler_pfx(conteudo, senha)
        status = calcular_status(
            dados_certificado.get("data_validade"),
            telefone_valido=telefone_valido,
            essencial_ok=bool(dados_certificado.get("subject")),
        )
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
        }
        status = SENHA_INVALIDA

    certificado_id = certificados.create_certificado(
        {
            "nome_arquivo_original": arquivo.filename,
            "caminho_arquivo": caminho,
            "senha_criptografada": senha_criptografada,
            "nome_contato": nome_contato,
            "telefone_limpo": telefone_limpo,
            "observacao": observacao,
            "status": status,
            **dados_certificado,
        }
    )

    auditoria.registrar_evento(certificado_id, "CERTIFICADO_CADASTRADO", "Certificado cadastrado manualmente.")
    if status == SENHA_INVALIDA:
        auditoria.registrar_evento(certificado_id, "SENHA_INVALIDA", "Senha invalida ao abrir o arquivo .pfx.")

    flash("Certificado cadastrado.", "success")
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


@certificados_bp.route("/<int:certificado_id>/download")
def download(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))
    if not caminho_permitido(
        certificado["caminho_arquivo"], current_app.config["STORAGE_CERTIFICADOS"]
    ):
        abort(404)
    auditoria.registrar_evento(certificado_id, "CERTIFICADO_BAIXADO", "Arquivo .pfx baixado pelo usuario.")
    return send_file(
        certificado["caminho_arquivo"],
        as_attachment=True,
        download_name=certificado["nome_arquivo_original"],
    )


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
