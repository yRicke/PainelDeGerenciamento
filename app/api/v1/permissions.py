from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission

from ...models import Empresa
from ...utils.modulos_permissoes import _usuario_tem_acesso_empresa, _usuario_tem_permissao_modulo


def _obter_empresa_da_view(view):
    empresa_id = view.kwargs.get("empresa_id")
    try:
        return Empresa.objects.get(id=empresa_id)
    except (TypeError, ValueError, Empresa.DoesNotExist):
        return None


def _token_bearer_do_request(request):
    cabecalho = str(request.headers.get("Authorization") or "").strip()
    if not cabecalho:
        return ""
    partes = cabecalho.split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return ""
    return partes[1].strip()


class HasTofuAtividadeAccess(BasePermission):
    message = "Acesso negado."

    def has_permission(self, request, view):
        empresa = _obter_empresa_da_view(view)
        if not empresa:
            self.message = "Empresa nao encontrada."
            return False

        usuario = request.user
        if not getattr(usuario, "is_authenticated", False):
            return False
        mesma_empresa = _usuario_tem_acesso_empresa(usuario, empresa)
        tem_permissao = _usuario_tem_permissao_modulo(usuario, "TOFU Lista de Atividades")
        if usuario.is_superuser:
            autorizado = True
        elif usuario.is_staff:
            autorizado = mesma_empresa
        else:
            autorizado = mesma_empresa and tem_permissao

        if autorizado:
            view.empresa = empresa
        return autorizado


class HasFixedApiToken(BasePermission):
    message = "Acesso negado."

    def has_permission(self, request, view):
        token_configurado = str(getattr(settings, "API_FIXED_TOKEN", "") or "").strip()
        if not token_configurado:
            return False
        token_recebido = _token_bearer_do_request(request)
        if not token_recebido:
            return False
        return constant_time_compare(token_recebido, token_configurado)


class HasTofuAccessOrFixedToken(BasePermission):
    message = "Acesso negado."

    def has_permission(self, request, view):
        empresa = _obter_empresa_da_view(view)
        if not empresa:
            self.message = "Empresa nao encontrada."
            return False

        token_ok = HasFixedApiToken().has_permission(request, view)
        if token_ok:
            view.empresa = empresa
            return True

        tofu_ok = HasTofuAtividadeAccess().has_permission(request, view)
        if tofu_ok:
            view.empresa = empresa
            return True
        return False
