from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..utils.modulos_permissoes import _modulos_com_acesso


@login_required(login_url="entrar")
def index(request):
    return render(request, "index.html")


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
