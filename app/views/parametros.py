from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ..models import (
    Cidade,
    ContaBancaria,
    DescricaoPerfil,
    EmpresaTitular,
    Motorista,
    Parceiro,
    ParametroMargemAdministracao,
    ParametroMargemFinanceiro,
    ParametroMargemLogistica,
    ParametroMargemVendas,
    ParametroMeta,
    ParametroNegocios,
    Produto,
    Rota,
    Transportadora,
    UnidadeFederativa,
)
from ..services.parametros import (
    atualizar_empresa_titular_por_dados,
    atualizar_motorista_por_dados,
    atualizar_descricao_perfil_por_dados,
    atualizar_conta_bancaria_por_dados,
    atualizar_parametro_margem_financeiro,
    atualizar_parametro_meta_por_dados,
    atualizar_parametro_margem_logistica,
    atualizar_parametro_margem_vendas,
    atualizar_parametro_negocios,
    atualizar_parceiro_por_dados,
    atualizar_produto_por_dados,
    atualizar_rota_por_dados,
    atualizar_transportadora_por_dados,
    atualizar_unidade_federativa_por_dados,
    criar_motorista_por_dados,
    criar_descricao_perfil_por_dados,
    criar_empresa_titular_por_dados,
    criar_conta_bancaria_por_dados,
    criar_parametro_margem_financeiro,
    criar_parametro_meta_por_dados,
    criar_parametro_margem_logistica,
    criar_parametro_margem_vendas,
    criar_parametro_negocios,
    criar_parceiro_por_dados,
    criar_produto_por_dados,
    criar_rota_por_dados,
    criar_transportadora_por_dados,
    criar_unidade_federativa_por_dados,
    excluir_parametro_margem_logistica,
    excluir_parametro_margem_financeiro,
    excluir_parametro_margem_vendas,
    excluir_parametro_negocios,
    excluir_conta_bancaria_por_dados,
    excluir_empresa_titular_por_dados,
    salvar_parametro_margem_administracao,
)
from ..tabulator import (
    build_contas_bancarias_tabulator,
    build_empresas_titulares_tabulator,
    build_motoristas_tabulator,
    build_descricoes_perfil_tabulator,
    build_parametros_margem_financeiro_tabulator,
    build_parametros_metas_tabulator,
    build_parametros_margem_logistica_tabulator,
    build_parametros_margem_vendas_tabulator,
    build_parametros_negocios_tabulator,
    build_parceiros_tabulator,
    build_produtos_tabulator,
    build_rotas_tabulator,
    build_transportadoras_tabulator,
    build_unidades_federativas_tabulator,
)
from ..utils.modulos_permissoes import _modulos_com_acesso, _obter_empresa_e_validar_permissao_modulo


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required(login_url="entrar")
def parametros(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Parametros"),
    }
    return render(request, "parametros/parametros.html", contexto)


@login_required(login_url="entrar")
def parceiros(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    parceiros_qs = Parceiro.objects.filter(empresa=empresa).select_related("cidade").order_by("nome")
    cidades_qs = Cidade.objects.filter(empresa=empresa).order_by("nome")
    parceiros_tabulator = build_parceiros_tabulator(parceiros_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "parceiros": parceiros_qs,
        "cidades": cidades_qs,
        "cidades_js": list(cidades_qs.values("id", "nome", "codigo")),
        "parceiros_tabulator": parceiros_tabulator,
    }
    return render(request, "parametros/parceiros.html", contexto)


@login_required(login_url="entrar")
def criar_parceiro_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    erro = criar_parceiro_por_dados(
        empresa,
        request.POST.get("nome"),
        request.POST.get("codigo"),
        request.POST.get("cidade_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("parceiros", empresa_id=empresa.id)
    messages.success(request, "Parceiro criado com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_parceiro_modulo(request, empresa_id, parceiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro = Parceiro.objects.filter(id=parceiro_id, empresa=empresa).first()
    if not parceiro:
        messages.error(request, "Parceiro nÃ£o encontrado.")
        return redirect("parceiros", empresa_id=empresa.id)

    erro = atualizar_parceiro_por_dados(
        parceiro,
        request.POST.get("nome"),
        request.POST.get("codigo"),
        empresa,
        request.POST.get("cidade_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("parceiros", empresa_id=empresa.id)
    messages.success(request, "Parceiro atualizado com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_parceiro_modulo(request, empresa_id, parceiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro = Parceiro.objects.filter(id=parceiro_id, empresa=empresa).first()
    if not parceiro:
        messages.error(request, "Parceiro nÃ£o encontrado.")
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro.excluir_parceiro()
    messages.success(request, "Parceiro excluÃ­do com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def empresas_titulares(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Empresas Titulares")
    if not autorizado:
        return redirect("index")

    empresas_titulares_qs = EmpresaTitular.objects.filter(empresa=empresa).order_by("codigo", "id")
    contexto = {
        "empresa": empresa,
        "empresas_titulares_tabulator": build_empresas_titulares_tabulator(empresas_titulares_qs, empresa.id),
    }
    return render(request, "parametros/empresas_titulares.html", contexto)


@login_required(login_url="entrar")
def criar_empresa_titular_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Empresas Titulares")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("empresas_titulares", empresa_id=empresa.id)

    erro = criar_empresa_titular_por_dados(
        empresa,
        request.POST.get("codigo"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("empresas_titulares", empresa_id=empresa.id)
    messages.success(request, "Empresa titular criada com sucesso.")
    return redirect("empresas_titulares", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_empresa_titular_modulo(request, empresa_id, empresa_titular_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Empresas Titulares")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("empresas_titulares", empresa_id=empresa.id)

    empresa_titular = EmpresaTitular.objects.filter(id=empresa_titular_id, empresa=empresa).first()
    if not empresa_titular:
        messages.error(request, "Empresa titular nao encontrada.")
        return redirect("empresas_titulares", empresa_id=empresa.id)

    erro = atualizar_empresa_titular_por_dados(
        empresa_titular,
        empresa,
        request.POST.get("codigo"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("empresas_titulares", empresa_id=empresa.id)
    messages.success(request, "Empresa titular atualizada com sucesso.")
    return redirect("empresas_titulares", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_empresa_titular_modulo(request, empresa_id, empresa_titular_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Empresas Titulares")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("empresas_titulares", empresa_id=empresa.id)

    empresa_titular = EmpresaTitular.objects.filter(id=empresa_titular_id, empresa=empresa).first()
    if not empresa_titular:
        messages.error(request, "Empresa titular nao encontrada.")
        return redirect("empresas_titulares", empresa_id=empresa.id)

    try:
        erro = excluir_empresa_titular_por_dados(empresa_titular, empresa)
    except ProtectedError:
        messages.error(
            request,
            "Nao e possivel excluir a empresa titular porque existem registros vinculados.",
        )
        return redirect("empresas_titulares", empresa_id=empresa.id)

    if erro:
        messages.error(request, erro)
        return redirect("empresas_titulares", empresa_id=empresa.id)
    messages.success(request, "Empresa titular excluida com sucesso.")
    return redirect("empresas_titulares", empresa_id=empresa.id)


@login_required(login_url="entrar")
def contas_bancarias(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas Bancarias")
    if not autorizado:
        return redirect("index")

    contas_qs = ContaBancaria.objects.filter(empresa=empresa).select_related("empresa_titular").order_by("id")
    empresas_titulares_qs = EmpresaTitular.objects.filter(empresa=empresa).order_by("codigo", "id")
    contexto = {
        "empresa": empresa,
        "contas_bancarias_tabulator": build_contas_bancarias_tabulator(contas_qs, empresa.id),
        "empresas_titulares_opcoes": [
            {"id": item.id, "codigo": item.codigo, "nome": item.nome}
            for item in empresas_titulares_qs
        ],
    }
    return render(request, "parametros/contas_bancarias.html", contexto)


@login_required(login_url="entrar")
def criar_conta_bancaria_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas Bancarias")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contas_bancarias", empresa_id=empresa.id)

    erro = criar_conta_bancaria_por_dados(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("contas_bancarias", empresa_id=empresa.id)

    conta = ContaBancaria.objects.filter(empresa=empresa).order_by("-id").first()
    registro = build_contas_bancarias_tabulator([conta], empresa.id)[0] if conta else None
    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "registro": registro, "message": "Conta bancaria criada com sucesso."})
    messages.success(request, "Conta bancaria criada com sucesso.")
    return redirect("contas_bancarias", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_conta_bancaria_modulo(request, empresa_id, conta_bancaria_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas Bancarias")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contas_bancarias", empresa_id=empresa.id)

    conta_bancaria = ContaBancaria.objects.filter(id=conta_bancaria_id, empresa=empresa).first()
    if not conta_bancaria:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Conta bancaria nao encontrada."}, status=404)
        messages.error(request, "Conta bancaria nao encontrada.")
        return redirect("contas_bancarias", empresa_id=empresa.id)

    erro = atualizar_conta_bancaria_por_dados(conta_bancaria, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("contas_bancarias", empresa_id=empresa.id)

    conta_bancaria.refresh_from_db()
    registro = build_contas_bancarias_tabulator([conta_bancaria], empresa.id)[0]
    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "registro": registro, "message": "Conta bancaria atualizada com sucesso."})
    messages.success(request, "Conta bancaria atualizada com sucesso.")
    return redirect("contas_bancarias", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_conta_bancaria_modulo(request, empresa_id, conta_bancaria_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas Bancarias")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contas_bancarias", empresa_id=empresa.id)

    conta_bancaria = ContaBancaria.objects.filter(id=conta_bancaria_id, empresa=empresa).first()
    if not conta_bancaria:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Conta bancaria nao encontrada."}, status=404)
        messages.error(request, "Conta bancaria nao encontrada.")
        return redirect("contas_bancarias", empresa_id=empresa.id)

    erro = excluir_conta_bancaria_por_dados(conta_bancaria, empresa)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("contas_bancarias", empresa_id=empresa.id)

    if _is_ajax_request(request):
        contas_qs = ContaBancaria.objects.filter(empresa=empresa).select_related("empresa_titular").order_by("id")
        return JsonResponse(
            {
                "ok": True,
                "message": "Conta bancaria excluida com sucesso.",
                "registros": build_contas_bancarias_tabulator(contas_qs, empresa.id),
            }
        )
    messages.success(request, "Conta bancaria excluida com sucesso.")
    return redirect("contas_bancarias", empresa_id=empresa.id)


@login_required(login_url="entrar")
def parametros_vendas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Vendas")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro, total_recalculado = criar_parametro_margem_vendas(empresa, request.POST)
        elif acao == "editar":
            item = ParametroMargemVendas.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_vendas", empresa_id=empresa.id)
            erro, total_recalculado = atualizar_parametro_margem_vendas(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroMargemVendas.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_vendas", empresa_id=empresa.id)
            erro, total_recalculado = excluir_parametro_margem_vendas(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros de vendas.")
            return redirect("parametros_vendas", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_vendas", empresa_id=empresa.id)
        messages.success(request, f"Parametros de vendas atualizados. Registros recalculados: {total_recalculado}.")
        return redirect("parametros_vendas", empresa_id=empresa.id)

    parametros_qs = ParametroMargemVendas.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_vendas_tabulator": build_parametros_margem_vendas_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_vendas.html", contexto)


@login_required(login_url="entrar")
def parametros_logistica(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Logistica")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro, total_recalculado = criar_parametro_margem_logistica(empresa, request.POST)
        elif acao == "editar":
            item = ParametroMargemLogistica.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_logistica", empresa_id=empresa.id)
            erro, total_recalculado = atualizar_parametro_margem_logistica(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroMargemLogistica.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_logistica", empresa_id=empresa.id)
            erro, total_recalculado = excluir_parametro_margem_logistica(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros de logistica.")
            return redirect("parametros_logistica", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_logistica", empresa_id=empresa.id)
        messages.success(request, f"Parametros de logistica atualizados. Registros recalculados: {total_recalculado}.")
        return redirect("parametros_logistica", empresa_id=empresa.id)

    parametros_qs = ParametroMargemLogistica.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_logistica_tabulator": build_parametros_margem_logistica_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_logistica.html", contexto)


@login_required(login_url="entrar")
def parametros_administracao(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Administracao")
    if not autorizado:
        return redirect("index")

    parametro, _ = ParametroMargemAdministracao.objects.get_or_create(empresa=empresa)
    if request.method == "POST":
        total_recalculado = salvar_parametro_margem_administracao(empresa, request.POST)
        messages.success(
            request,
            f"Parametros de administracao salvos. Registros de Controle de Margem recalculados: {total_recalculado}.",
        )
        return redirect("parametros_administracao", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "parametro": parametro,
    }
    return render(request, "parametros/parametros_administracao.html", contexto)


@login_required(login_url="entrar")
def parametros_financeiro(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Financeiro")
    if not autorizado:
        return redirect("index")

    parametros_qs = ParametroMargemFinanceiro.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros_financeiro_tabulator": build_parametros_margem_financeiro_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_financeiro.html", contexto)


@login_required(login_url="entrar")
def criar_parametro_margem_financeiro_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Financeiro")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    erro, total_recalculado = criar_parametro_margem_financeiro(empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    messages.success(request, f"Parametro financeiro criado. Registros recalculados: {total_recalculado}.")
    return redirect("parametros_financeiro", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_parametro_margem_financeiro_modulo(request, empresa_id, parametro_financeiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Financeiro")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    item = ParametroMargemFinanceiro.objects.filter(id=parametro_financeiro_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Parametro nao encontrado.")
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    erro, total_recalculado = atualizar_parametro_margem_financeiro(item, empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    messages.success(request, f"Parametro financeiro atualizado. Registros recalculados: {total_recalculado}.")
    return redirect("parametros_financeiro", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_parametro_margem_financeiro_modulo(request, empresa_id, parametro_financeiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Financeiro")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    item = ParametroMargemFinanceiro.objects.filter(id=parametro_financeiro_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Parametro nao encontrado.")
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    erro, total_recalculado = excluir_parametro_margem_financeiro(item, empresa)
    if erro:
        messages.error(request, erro)
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    messages.success(request, f"Parametro financeiro excluido. Registros recalculados: {total_recalculado}.")
    return redirect("parametros_financeiro", empresa_id=empresa.id)


@login_required(login_url="entrar")
def parametros_negocios(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros de Negocios")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro = criar_parametro_negocios(empresa, request.POST)
        elif acao == "editar":
            item = ParametroNegocios.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_negocios", empresa_id=empresa.id)
            erro = atualizar_parametro_negocios(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroNegocios.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_negocios", empresa_id=empresa.id)
            erro = excluir_parametro_negocios(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros de negocios.")
            return redirect("parametros_negocios", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_negocios", empresa_id=empresa.id)
        messages.success(request, "Parametros de negocios atualizados com sucesso.")
        return redirect("parametros_negocios", empresa_id=empresa.id)

    parametros_qs = ParametroNegocios.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_negocios_tabulator": build_parametros_negocios_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_negocios.html", contexto)


@login_required(login_url="entrar")
def descricoes_perfil(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Descricao Perfil")
    if not autorizado:
        return redirect("index")

    descricoes_qs = DescricaoPerfil.objects.filter(empresa=empresa).order_by("descricao", "id")
    contexto = {
        "empresa": empresa,
        "descricoes_perfil_tabulator": build_descricoes_perfil_tabulator(descricoes_qs, empresa.id),
    }
    return render(request, "parametros/descricoes_perfil.html", contexto)


@login_required(login_url="entrar")
def criar_descricao_perfil_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Descricao Perfil")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    erro = criar_descricao_perfil_por_dados(
        empresa,
        request.POST.get("descricao"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("descricoes_perfil", empresa_id=empresa.id)
    messages.success(request, "Descricao perfil criada com sucesso.")
    return redirect("descricoes_perfil", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_descricao_perfil_modulo(request, empresa_id, descricao_perfil_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Descricao Perfil")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    item = DescricaoPerfil.objects.filter(id=descricao_perfil_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Descricao perfil nao encontrada.")
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    erro = atualizar_descricao_perfil_por_dados(
        item,
        request.POST.get("descricao"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("descricoes_perfil", empresa_id=empresa.id)
    messages.success(request, "Descricao perfil atualizada com sucesso.")
    return redirect("descricoes_perfil", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_descricao_perfil_modulo(request, empresa_id, descricao_perfil_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Descricao Perfil")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    item = DescricaoPerfil.objects.filter(id=descricao_perfil_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Descricao perfil nao encontrada.")
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    try:
        item.excluir_descricao_perfil()
    except ProtectedError:
        messages.error(
            request,
            "Nao e possivel excluir a descricao perfil porque ha parametros metas vinculados.",
        )
        return redirect("descricoes_perfil", empresa_id=empresa.id)

    messages.success(request, "Descricao perfil excluida com sucesso.")
    return redirect("descricoes_perfil", empresa_id=empresa.id)


@login_required(login_url="entrar")
def parametros_metas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Metas")
    if not autorizado:
        return redirect("index")

    parametros_qs = ParametroMeta.objects.filter(empresa=empresa).select_related("descricao_perfil").order_by("id")
    descricoes_qs = DescricaoPerfil.objects.filter(empresa=empresa).order_by("descricao", "id")
    contexto = {
        "empresa": empresa,
        "descricoes_perfil": descricoes_qs,
        "descricoes_perfil_js": list(descricoes_qs.values("id", "descricao")),
        "parametros_metas_tabulator": build_parametros_metas_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_metas.html", contexto)


@login_required(login_url="entrar")
def criar_parametro_meta_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Metas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_metas", empresa_id=empresa.id)

    erro = criar_parametro_meta_por_dados(empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("parametros_metas", empresa_id=empresa.id)
    messages.success(request, "Parametro de metas criado com sucesso.")
    return redirect("parametros_metas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_parametro_meta_modulo(request, empresa_id, parametro_meta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Metas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_metas", empresa_id=empresa.id)

    item = ParametroMeta.objects.filter(id=parametro_meta_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Parametro de metas nao encontrado.")
        return redirect("parametros_metas", empresa_id=empresa.id)

    erro = atualizar_parametro_meta_por_dados(item, empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("parametros_metas", empresa_id=empresa.id)
    messages.success(request, "Parametro de metas atualizado com sucesso.")
    return redirect("parametros_metas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_parametro_meta_modulo(request, empresa_id, parametro_meta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Metas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("parametros_metas", empresa_id=empresa.id)

    item = ParametroMeta.objects.filter(id=parametro_meta_id, empresa=empresa).first()
    if not item:
        messages.error(request, "Parametro de metas nao encontrado.")
        return redirect("parametros_metas", empresa_id=empresa.id)

    item.excluir_parametro_meta()
    messages.success(request, "Parametro de metas excluido com sucesso.")
    return redirect("parametros_metas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def produtos(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")

    produtos_qs = Produto.objects.filter(empresa=empresa).order_by("codigo_produto")
    produtos_tabulator = build_produtos_tabulator(produtos_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "produtos": produtos_qs,
        "produtos_tabulator": produtos_tabulator,
    }
    return render(request, "parametros/produtos.html", contexto)


@login_required(login_url="entrar")
def criar_produto_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("produtos", empresa_id=empresa.id)

    erro = criar_produto_por_dados(empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("produtos", empresa_id=empresa.id)
    messages.success(request, "Produto criado com sucesso.")
    return redirect("produtos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_produto_modulo(request, empresa_id, produto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")

    produto = Produto.objects.filter(id=produto_id, empresa=empresa).first()
    if not produto:
        messages.error(request, "Produto nao encontrado.")
        return redirect("produtos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_produto_por_dados(produto, request.POST, empresa)
        if erro:
            messages.error(request, erro)
            return redirect("editar_produto_modulo", empresa_id=empresa.id, produto_id=produto.id)
        messages.success(request, "Produto atualizado com sucesso.")
        return redirect("produtos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "produto": produto,
    }
    return render(request, "parametros/produto_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_produto_modulo(request, empresa_id, produto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("produtos", empresa_id=empresa.id)

    produto = Produto.objects.filter(id=produto_id, empresa=empresa).first()
    if not produto:
        messages.error(request, "Produto nao encontrado.")
        return redirect("produtos", empresa_id=empresa.id)
    produto.excluir_produto()
    messages.success(request, "Produto excluido com sucesso.")
    return redirect("produtos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def unidades_federativas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")

    unidades_qs = UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo")
    unidades_tabulator = build_unidades_federativas_tabulator(unidades_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "unidades_federativas": unidades_qs,
        "unidades_federativas_tabulator": unidades_tabulator,
    }
    return render(request, "parametros/unidades_federativas.html", contexto)


@login_required(login_url="entrar")
def criar_unidade_federativa_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    erro = criar_unidade_federativa_por_dados(
        empresa,
        request.POST.get("codigo"),
        request.POST.get("sigla"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("unidades_federativas", empresa_id=empresa.id)
    messages.success(request, "Unidade federativa criada com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_unidade_federativa_modulo(request, empresa_id, unidade_federativa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa = UnidadeFederativa.objects.filter(id=unidade_federativa_id, empresa=empresa).first()
    if not unidade_federativa:
        messages.error(request, "Unidade federativa nao encontrada.")
        return redirect("unidades_federativas", empresa_id=empresa.id)

    erro = atualizar_unidade_federativa_por_dados(
        unidade_federativa,
        request.POST.get("codigo"),
        request.POST.get("sigla"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("unidades_federativas", empresa_id=empresa.id)
    messages.success(request, "Unidade federativa atualizada com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_unidade_federativa_modulo(request, empresa_id, unidade_federativa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa = UnidadeFederativa.objects.filter(id=unidade_federativa_id, empresa=empresa).first()
    if not unidade_federativa:
        messages.error(request, "Unidade federativa nao encontrada.")
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa.excluir_unidade_federativa()
    messages.success(request, "Unidade federativa excluida com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def motoristas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")

    motoristas_qs = Motorista.objects.filter(empresa=empresa).order_by("nome")
    motoristas_tabulator = build_motoristas_tabulator(motoristas_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "motoristas_tabulator": motoristas_tabulator,
    }
    return render(request, "parametros/motoristas.html", contexto)


@login_required(login_url="entrar")
def criar_motorista_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    erro = criar_motorista_por_dados(
        empresa,
        request.POST.get("codigo_motorista"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista criado com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_motorista_modulo(request, empresa_id, motorista_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    motorista = Motorista.objects.filter(id=motorista_id, empresa=empresa).first()
    if not motorista:
        messages.error(request, "Motorista nÃ£o encontrado.")
        return redirect("motoristas", empresa_id=empresa.id)

    erro = atualizar_motorista_por_dados(
        motorista,
        request.POST.get("codigo_motorista"),
        request.POST.get("nome"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista atualizado com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_motorista_modulo(request, empresa_id, motorista_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    motorista = Motorista.objects.filter(id=motorista_id, empresa=empresa).first()
    if not motorista:
        messages.error(request, "Motorista nÃ£o encontrado.")
        return redirect("motoristas", empresa_id=empresa.id)

    try:
        motorista.excluir_motorista()
    except ProtectedError:
        messages.error(request, "NÃ£o Ã© possÃ­vel excluir o motorista porque hÃ¡ agendas vinculadas.")
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista excluÃ­do com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def transportadoras(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")

    transportadoras_qs = Transportadora.objects.filter(empresa=empresa).order_by("nome")
    transportadoras_tabulator = build_transportadoras_tabulator(transportadoras_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "transportadoras_tabulator": transportadoras_tabulator,
    }
    return render(request, "parametros/transportadoras.html", contexto)


@login_required(login_url="entrar")
def criar_transportadora_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    erro = criar_transportadora_por_dados(
        empresa,
        request.POST.get("codigo_transportadora"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora criada com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_transportadora_modulo(request, empresa_id, transportadora_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    transportadora = Transportadora.objects.filter(id=transportadora_id, empresa=empresa).first()
    if not transportadora:
        messages.error(request, "Transportadora nÃ£o encontrada.")
        return redirect("transportadoras", empresa_id=empresa.id)

    erro = atualizar_transportadora_por_dados(
        transportadora,
        request.POST.get("codigo_transportadora"),
        request.POST.get("nome"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora atualizada com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_transportadora_modulo(request, empresa_id, transportadora_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    transportadora = Transportadora.objects.filter(id=transportadora_id, empresa=empresa).first()
    if not transportadora:
        messages.error(request, "Transportadora nÃ£o encontrada.")
        return redirect("transportadoras", empresa_id=empresa.id)

    try:
        transportadora.excluir_transportadora()
    except ProtectedError:
        messages.error(request, "NÃ£o Ã© possÃ­vel excluir a transportadora porque hÃ¡ agendas vinculadas.")
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora excluÃ­da com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def rotas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    rotas_qs = Rota.objects.filter(empresa=empresa).select_related("uf").order_by("nome")
    ufs_qs = UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo")
    contexto = {
        "empresa": empresa,
        "rotas_tabulator": build_rotas_tabulator(rotas_qs, empresa.id),
        "unidades_federativas": ufs_qs,
        "unidades_federativas_js": list(ufs_qs.values("id", "codigo", "sigla")),
    }
    return render(request, "parametros/rotas.html", contexto)


@login_required(login_url="entrar")
def criar_rota_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    erro = criar_rota_por_dados(
        empresa,
        request.POST.get("codigo_rota"),
        request.POST.get("nome"),
        request.POST.get("uf_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("rotas", empresa_id=empresa.id)
    messages.success(request, "Rota criada com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_rota_modulo(request, empresa_id, rota_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    rota = Rota.objects.filter(id=rota_id, empresa=empresa).first()
    if not rota:
        messages.error(request, "Rota nÃ£o encontrada.")
        return redirect("rotas", empresa_id=empresa.id)

    erro = atualizar_rota_por_dados(
        rota,
        request.POST.get("codigo_rota"),
        request.POST.get("nome"),
        empresa,
        request.POST.get("uf_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("rotas", empresa_id=empresa.id)
    messages.success(request, "Rota atualizada com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_rota_modulo(request, empresa_id, rota_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    rota = Rota.objects.filter(id=rota_id, empresa=empresa).first()
    if not rota:
        messages.error(request, "Rota nÃ£o encontrada.")
        return redirect("rotas", empresa_id=empresa.id)

    rota.excluir_rota()
    messages.success(request, "Rota excluÃ­da com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)

