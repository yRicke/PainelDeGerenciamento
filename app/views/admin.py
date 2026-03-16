from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render

from ..models import Empresa, Usuario
from ..services.admin import (
    atualizar_empresa_por_nome,
    atualizar_usuario_por_post,
    criar_empresa_por_nome,
    criar_usuario_por_post,
    excluir_empresa_por_id,
    excluir_usuario_por_id,
    usuarios_com_permissoes_ids,
)
from ..utils.modulos_permissoes import _obter_permissoes_do_form, _obter_permissoes_por_modulo

def _valor_checkbox_possui_sistema(post_data):
    return str(post_data.get("possui_sistema", "")).strip().lower() in {"1", "true", "on", "sim", "yes"}


def _usuario_admin_pode_acessar_empresa(usuario, empresa):
    if not usuario:
        return False
    if usuario.is_superuser:
        return True
    if not empresa:
        return False
    if not usuario.is_staff:
        return False
    return bool(getattr(usuario, "empresa_id", None) and usuario.empresa_id == empresa.id)


def _empresas_painel_admin_para_usuario(usuario):
    if usuario.is_superuser:
        return Empresa.objects.all()
    if not usuario.is_staff or not getattr(usuario, "empresa_id", None):
        return Empresa.objects.none()
    return Empresa.objects.filter(id=usuario.empresa_id)


def _obter_empresa_admin_autorizada(request, empresa_id):
    empresa = Empresa.objects.filter(id=empresa_id).first()
    if not empresa:
        messages.error(request, "Empresa nao encontrada.")
        return None
    if not _usuario_admin_pode_acessar_empresa(request.user, empresa):
        messages.error(request, "Voce nao tem permissao para acessar esta empresa.")
        return None
    return empresa


def _obter_usuario_admin_autorizado(request, usuario_id):
    usuario = Usuario.objects.select_related("empresa").filter(id=usuario_id).first()
    if not usuario:
        messages.error(request, "Usuario nao encontrado.")
        return None
    if not _usuario_admin_pode_acessar_empresa(request.user, usuario.empresa):
        messages.error(request, "Voce nao tem permissao para acessar este usuario.")
        return None
    return usuario


@staff_member_required(login_url="entrar")
def painel_admin(request):
    empresas = _empresas_painel_admin_para_usuario(request.user).order_by("nome")
    contexto = {
        "empresas": empresas,
        "pode_cadastrar_empresa": request.user.is_superuser,
        "pode_editar_possui_sistema": request.user.is_superuser,
    }
    return render(request, "admin/painel_admin.html", contexto)


@staff_member_required(login_url="entrar")
def criar_empresa(request):
    if not request.user.is_superuser:
        messages.error(request, "Somente superusuario pode cadastrar empresa.")
        return redirect("painel_admin")
    if request.method == "POST":
        erro = criar_empresa_por_nome(
            request.POST.get("nome"),
            possui_sistema=_valor_checkbox_possui_sistema(request.POST),
        )
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa criada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def editar_empresa(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    if request.method == "POST":
        possui_sistema = empresa.possui_sistema
        if request.user.is_superuser:
            possui_sistema = _valor_checkbox_possui_sistema(request.POST)
        erro = atualizar_empresa_por_nome(
            empresa,
            request.POST.get("nome"),
            possui_sistema=possui_sistema,
        )
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa atualizada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def excluir_empresa(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    ok, mensagem = excluir_empresa_por_id(empresa_id)
    if ok:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def usuarios_permissoes(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    usuarios_qs = Usuario.objects.filter(empresa=empresa).prefetch_related("permissoes")
    usuarios = usuarios_com_permissoes_ids(usuarios_qs)

    contexto = {
        "empresa": empresa,
        "usuarios": usuarios,
        "permissoes_por_modulo": _obter_permissoes_por_modulo(),
    }
    return render(request, "admin/usuarios_permissoes.html", contexto)


@staff_member_required(login_url="entrar")
def cadastrar_usuario(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    if request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        erro = criar_usuario_por_post(empresa, request.POST, permissoes)
        if erro:
            messages.error(request, erro)
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        messages.success(request, "Usuario criado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def editar_usuario(request, usuario_id):
    usuario = _obter_usuario_admin_autorizado(request, usuario_id)
    if not usuario:
        return redirect("painel_admin")
    empresa_id = usuario.empresa_id
    if not empresa_id:
        messages.error(request, "Usuario sem empresa vinculada.")
        return redirect("painel_admin")
    if request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        erro = atualizar_usuario_por_post(
            usuario,
            request.POST,
            permissoes,
            usuario_logado=request.user,
        )
        if erro:
            messages.error(request, erro)
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        messages.success(request, "Usuario atualizado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def excluir_usuario(request, usuario_id):
    usuario = _obter_usuario_admin_autorizado(request, usuario_id)
    if not usuario:
        return redirect("painel_admin")

    ok, empresa_id, mensagem = excluir_usuario_por_id(usuario_id)
    if ok:
        messages.success(request, mensagem)
        if empresa_id:
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        return redirect("painel_admin")
    messages.error(request, mensagem)
    return redirect("painel_admin")

