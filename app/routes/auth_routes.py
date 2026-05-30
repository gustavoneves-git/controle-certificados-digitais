from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if (
            usuario == current_app.config["LOGIN_USUARIO"]
            and senha == current_app.config["LOGIN_SENHA"]
        ):
            session["autenticado"] = True
            session["usuario"] = usuario
            flash("Sessao iniciada com sucesso.", "success")
            return redirect(url_for("dashboard.index"))
        flash("Usuario ou senha invalidos.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sessao encerrada com sucesso.", "success")
    return redirect(url_for("auth.login"))
