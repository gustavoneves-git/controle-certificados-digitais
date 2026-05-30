from flask import Blueprint, render_template

from app.repositories import certificado_repository as certificados
from app.services.vencimento_service import (
    SENHA_INVALIDA,
    SEM_TELEFONE,
    VALIDO,
    VENCE_EM_15_DIAS,
    VENCIDO,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    stats = {
        "total": certificados.count_all(),
        "vencidos": certificados.count_by_status(VENCIDO),
        "vence_15": certificados.count_by_status(VENCE_EM_15_DIAS),
        "validos": certificados.count_by_status(VALIDO),
        "senha_invalida": certificados.count_by_status(SENHA_INVALIDA),
        "sem_telefone": certificados.count_by_status(SEM_TELEFONE),
    }
    return render_template("dashboard.html", stats=stats)
