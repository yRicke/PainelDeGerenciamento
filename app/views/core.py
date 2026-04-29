from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import redirect, render

from ..utils.dashboard_geral import (
    NOME_PERMISSAO_DASHBOARD_GERAL,
    montar_dashboard_geral,
    montar_payload_pdf_dashboard_geral,
    resolver_mes_dashboard_geral,
    texto_mes_referencia,
)
from ..utils.modulos_permissoes import (
    _modulos_com_acesso,
    _obter_empresa_e_validar_permissao_modulo,
    _usuario_tem_permissao_modulo,
)


@login_required(login_url="entrar")
def index(request):
    contexto = {
        "dashboard_geral_permitido": bool(
            getattr(request.user, "empresa_id", None)
            and (
                request.user.is_staff
                or request.user.is_superuser
                or _usuario_tem_permissao_modulo(request.user, NOME_PERMISSAO_DASHBOARD_GERAL)
            )
        ),
        "kpi_controladoria_permitido": bool(
            getattr(request.user, "empresa_id", None)
            and (
                request.user.is_staff
                or request.user.is_superuser
                or _usuario_tem_permissao_modulo(request.user, "KPI - Controladoria")
            )
        ),
    }
    return render(request, "index.html", contexto)


@login_required(login_url="entrar")
@ensure_csrf_cookie
def dashboard_geral(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        NOME_PERMISSAO_DASHBOARD_GERAL,
    )
    if not permitido:
        return redirect("index")

    data_inicio, data_fim = resolver_mes_dashboard_geral(request.GET.get("mes"))
    dashboard = montar_dashboard_geral(empresa, data_inicio, data_fim)
    contexto = {
        "empresa": empresa,
        "mes_referencia": texto_mes_referencia(data_inicio),
        "periodo_inicio": data_inicio.strftime("%d/%m/%Y"),
        "periodo_fim": data_fim.strftime("%d/%m/%Y"),
        "dashboard": dashboard,
        "dashboard_pdf_payload": montar_payload_pdf_dashboard_geral(dashboard, data_inicio, data_fim),
    }
    return render(request, "dashboard_geral.html", contexto)


@login_required(login_url="entrar")
def financeiro(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Financeiro"),
    }
    return render(request, "financeiro/financeiro.html", contexto)


financeiro_home = financeiro


@login_required(login_url="entrar")
def comercial(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Comercial"),
    }
    return render(request, "comercial/comercial.html", contexto)


comercial_home = comercial


def entrar(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login bem-sucedido!")
            return redirect("index")
        messages.error(request, "Credenciais invalidas. Tente novamente.")
    return render(request, "autentificacao/entrar.html")


@login_required(login_url="entrar")
def sair(request):
    logout(request)
    messages.success(request, "Logout bem-sucedido!")
    return redirect("entrar")
