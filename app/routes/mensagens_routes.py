from flask import Blueprint, flash, jsonify, redirect, render_template, url_for

from app.repositories import auditoria_repository as auditoria
from app.repositories import certificado_repository as certificados
from app.repositories import mensagem_repository as mensagens
from app.services.mensagem_service import gerar_mensagem

mensagens_bp = Blueprint("mensagens", __name__, url_prefix="/mensagens")


@mensagens_bp.route("/certificado/<int:certificado_id>/gerar", methods=["POST"])
def gerar(certificado_id):
    certificado = certificados.get_certificado(certificado_id)
    if certificado is None:
        flash("Certificado nao encontrado.", "warning")
        return redirect(url_for("certificados.listar"))

    tipo, texto = gerar_mensagem(certificado)
    mensagem_id = mensagens.create_mensagem(
        certificado_id,
        certificado["telefone_limpo"],
        tipo,
        texto,
    )
    auditoria.registrar_evento(certificado_id, "MENSAGEM_GERADA", "Mensagem gerada para contato manual.")
    return redirect(url_for("mensagens.detalhe", mensagem_id=mensagem_id))


@mensagens_bp.route("/<int:mensagem_id>")
def detalhe(mensagem_id):
    mensagem = mensagens.get_mensagem(mensagem_id)
    if mensagem is None:
        flash("Mensagem nao encontrada.", "warning")
        return redirect(url_for("certificados.listar"))
    certificado = certificados.get_certificado(mensagem["certificado_id"])
    return render_template("mensagem.html", mensagem=mensagem, certificado=certificado)


@mensagens_bp.route("/<int:mensagem_id>/copiar", methods=["POST"])
def registrar_copia(mensagem_id):
    mensagem = mensagens.get_mensagem(mensagem_id)
    if mensagem is None:
        return jsonify({"error": "Mensagem nao encontrada"}), 404
    auditoria.registrar_evento(
        mensagem["certificado_id"],
        "MENSAGEM_COPIADA",
        "Mensagem copiada para envio manual.",
    )
    return jsonify({"ok": True})
