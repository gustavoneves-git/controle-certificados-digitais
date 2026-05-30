from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.repositories import auditoria_repository as auditoria

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if (
            usuario == current_app.config["APP_LOGIN_USER"]
            and check_password_hash(current_app.config["APP_LOGIN_PASSWORD_HASH"], senha)
        ):
            session["autenticado"] = True
            session["usuario"] = usuario
            auditoria.registrar_evento(None, "LOGIN_REALIZADO", f"Login realizado pelo usuario {usuario}.")
            flash("Sessao iniciada com sucesso.", "success")
            return redirect(url_for("dashboard.index"))
        flash("Usuario ou senha invalidos.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    usuario = session.get("usuario", "-")
    auditoria.registrar_evento(None, "LOGOUT_REALIZADO", f"Logout realizado pelo usuario {usuario}.")
    session.clear()
    flash("Sessao encerrada com sucesso.", "success")
    return redirect(url_for("auth.login"))
