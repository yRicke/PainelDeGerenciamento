from ..models import Empresa, Permissao
from django.contrib import messages
from django.shortcuts import redirect, render
import unicodedata


MODULOS_POR_AREA = {
    "Financeiro": [
        {"nome": "Comite Diario", "url": "comite_diario", "template": "financeiro/comite_diario.html"},
        {"nome": "Balanco Patrimonial", "url": "balanco_patrimonial", "template": "financeiro/balanco_patrimonial.html"},
        {"nome": "DRE", "url": "dre", "template": "financeiro/dre.html"},
        {"nome": "Contas a Receber", "url": "contas_a_receber", "template": "financeiro/contas_a_receber.html"},
        {"nome": "DFC", "url": "dfc", "template": "financeiro/dfc.html"},
        {"nome": "Adiantamentos", "url": "adiantamentos", "template": "financeiro/adiantamentos.html"},
        {"nome": "Contratos Redes", "url": "contratos_redes", "template": "financeiro/contratos_redes.html"},
        {"nome": "Saldos e Limites", "url": "saldos_e_limites", "template": "financeiro/saldos_e_limites.html"},
    ],
    "Administrativo": [
        {"nome": "Plano de Cargos e Salarios", "url": "plano_de_cargos_e_salarios", "template": "administrativo/plano_de_cargos_e_salarios.html"},
        {"nome": "Descritivos", "url": "descritivos", "template": "administrativo/descritivos.html"},
        {"nome": "TOFU Lista de Atividades", "url": "tofu_lista_de_atividades", "template": "administrativo/tofu_lista_de_atividades.html"},
        {"nome": "Fiscal e Contabil", "url": "fiscal_e_contabil", "template": "administrativo/fiscal_e_contabil.html"},
        {"nome": "Faturamento", "url": "faturamento", "template": "administrativo/faturamento.html"},
        {"nome": "Apuracao de Resultados", "url": "apuracao_de_resultados", "template": "administrativo/apuracao_de_resultados.html"},
        {"nome": "Orcamento x Realizado", "url": "orcamento", "template": "administrativo/orcamento.html"},
    ],
    "Comercial": [
        {"nome": "Carteira", "url": "carteira", "template": "comercial/carteira.html"},
        {"nome": "Pedidos Pendentes", "url": "pedidos_pendentes", "template": "comercial/pedidos_pendentes.html"},
        {"nome": "Vendas por Categoria", "url": "vendas_por_categoria", "template": "comercial/vendas_por_categoria.html"},
        {"nome": "Precificacao", "url": "precificacao", "template": "comercial/precificacao.html"},
        {"nome": "Controle de Margem", "url": "controle_de_margem", "template": "comercial/controle_de_margem.html"},
    ],
    "Parametros": [
        {"nome": "Produtos", "url": "produtos", "template": "parametros/produtos.html"},
        {"nome": "Titulos", "url": "titulos", "template": "financeiro/titulos.html"},
        {"nome": "Naturezas", "url": "naturezas", "template": "financeiro/naturezas.html"},
        {"nome": "Operacoes", "url": "operacoes", "template": "financeiro/operacoes.html"},
        {"nome": "Parceiros", "url": "parceiros", "template": "parametros/parceiros.html"},
        {"nome": "Centro Resultado", "url": "centros_resultado", "template": "financeiro/centros_resultado.html"},
        {"nome": "Colaboradores", "url": "colaboradores", "template": "administrativo/colaboradores.html"},
        {"nome": "Projetos", "url": "projetos", "template": "administrativo/projetos.html"},
        {"nome": "Cidades", "url": "cidades", "template": "comercial/cidades.html"},
        {"nome": "Regioes", "url": "regioes", "template": "comercial/regioes.html"},
        {"nome": "Unidades Federativas", "url": "unidades_federativas", "template": "parametros/unidades_federativas.html"},
        {"nome": "Rotas", "url": "rotas", "template": "parametros/rotas.html"},
        {"nome": "Motoristas", "url": "motoristas", "template": "parametros/motoristas.html"},
        {"nome": "Transportadoras", "url": "transportadoras", "template": "parametros/transportadoras.html"},
        {"nome": "Descricao Perfil", "url": "descricoes_perfil", "template": "parametros/descricoes_perfil.html"},
        {"nome": "Parametros Metas", "url": "parametros_metas", "template": "parametros/parametros_metas.html"},
        {"nome": "Parametros Vendas", "url": "parametros_vendas", "template": "parametros/parametros_vendas.html"},
        {"nome": "Parametros Logistica", "url": "parametros_logistica", "template": "parametros/parametros_logistica.html"},
        {"nome": "Parametros Administracao", "url": "parametros_administracao", "template": "parametros/parametros_administracao.html"},
        {"nome": "Parametros Financeiro", "url": "parametros_financeiro", "template": "parametros/parametros_financeiro.html"},
        {"nome": "Parametros de Negocios", "url": "parametros_negocios", "template": "parametros/parametros_negocios.html"},
        {"nome": "Bancos", "url": "bancos", "template": "parametros/bancos.html"},
        {"nome": "Contas Bancarias", "url": "contas_bancarias", "template": "parametros/contas_bancarias.html"},
        {"nome": "Empresas Titulares", "url": "empresas_titulares", "template": "parametros/empresas_titulares.html"},
    ],
    "Operacional": [
        {"nome": "Cargas em Aberto", "url": "cargas_em_aberto", "template": "operacional/cargas_em_aberto.html"},
        {"nome": "Operador Logistico", "url": "operador_logistico", "template": "operacional/operador_logistico.html"},
        {"nome": "Tabela de Fretes", "url": "tabela_de_fretes", "template": "operacional/tabela_de_fretes.html"},
        {"nome": "Estoque - PCP", "url": "estoque_pcp", "template": "operacional/estoque_pcp.html"},
        {"nome": "Producao", "url": "producao", "template": "operacional/producao.html"},
    ],
}

NOMES_EXIBICAO_MODULOS = {
    "Comite Diario": "Comitê Diário",
    "Balanco Patrimonial": "Balanço Patrimonial",
    "Plano de Cargos e Salarios": "Plano de Cargos e Salários",
    "Fiscal e Contabil": "Fiscal e Contábil",
    "Apuracao de Resultados": "Apuração de Resultados",
    "Orcamento x Realizado": "Orçamento x Realizado",
    "Precificacao": "Precificação",
    "Titulos": "Títulos",
    "Operacoes": "Operações",
    "Regioes": "Regiões",
    "Operador Logistico": "Operador Logístico",
    "Producao": "Produção",
    "Contas Bancarias": "Contas Bancarias",
}

PERMISSOES_POR_MODULO = {
    area: [modulo["nome"] for modulo in modulos]
    for area, modulos in MODULOS_POR_AREA.items()
}


def _normalizar_nome_permissao(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.strip().lower().split())


def _nome_exibicao_modulo(nome):
    return NOMES_EXIBICAO_MODULOS.get(nome, nome)


def _usuario_tem_permissao_modulo(usuario, nome_permissao):
    permissoes_usuario = {
        _normalizar_nome_permissao(nome)
        for nome in usuario.permissoes.values_list("nome", flat=True)
    }
    return _normalizar_nome_permissao(nome_permissao) in permissoes_usuario


def _usuario_tem_acesso_empresa(usuario, empresa):
    if not usuario or not empresa:
        return False
    if usuario.is_superuser:
        return True
    return bool(getattr(usuario, "empresa_id", None) and usuario.empresa_id == empresa.id)


def _modulos_com_acesso(usuario, area):
    modulos = MODULOS_POR_AREA[area]

    if usuario.is_staff or usuario.is_superuser:
        return [
            {
                "nome": _nome_exibicao_modulo(modulo["nome"]),
                "url": modulo["url"],
                "permitido": True,
            }
            for modulo in modulos
        ]

    permissoes_usuario = {
        _normalizar_nome_permissao(nome)
        for nome in usuario.permissoes.values_list("nome", flat=True)
    }
    return [
        {
            "nome": _nome_exibicao_modulo(modulo["nome"]),
            "url": modulo["url"],
            "permitido": _normalizar_nome_permissao(modulo["nome"]) in permissoes_usuario,
        }
        for modulo in modulos
    ]


def _obter_permissoes_por_modulo():
    permissoes_por_modulo = []
    for modulo, nomes_permissoes in PERMISSOES_POR_MODULO.items():
        permissoes = []
        for nome in nomes_permissoes:
            permissao, _ = Permissao.objects.get_or_create(nome=nome)
            permissoes.append(permissao)
        permissoes_por_modulo.append((modulo, permissoes))
    return permissoes_por_modulo


def _obter_permissoes_do_form(request):
    permissao_ids = request.POST.getlist("permissoes")
    if not permissao_ids:
        return []
    return list(Permissao.objects.filter(id__in=permissao_ids))


def _render_modulo_com_permissao(request, empresa_id, nome_permissao, template_path):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist:
        messages.error(request, "Empresa nao encontrada.")
        return redirect("index")

    mesma_empresa = _usuario_tem_acesso_empresa(request.user, empresa)
    tem_permissao = _usuario_tem_permissao_modulo(request.user, nome_permissao)
    if request.user.is_superuser:
        autorizado = True
    elif request.user.is_staff:
        autorizado = mesma_empresa
    else:
        autorizado = mesma_empresa and tem_permissao
    if not autorizado:
        messages.error(request, "Voce nao tem permissao para acessar esta pagina.")
        return redirect("index")

    contexto = {
        "empresa": empresa,
        "modulo_nome": nome_permissao,
    }
    return render(request, template_path, contexto)


def _obter_empresa_e_validar_permissao_modulo(request, empresa_id, nome_permissao):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist:
        messages.error(request, "Empresa nao encontrada.")
        return None, False

    mesma_empresa = _usuario_tem_acesso_empresa(request.user, empresa)
    tem_permissao = _usuario_tem_permissao_modulo(request.user, nome_permissao)
    if request.user.is_superuser:
        autorizado = True
    elif request.user.is_staff:
        autorizado = mesma_empresa
    else:
        autorizado = mesma_empresa and tem_permissao
    if not autorizado:
        messages.error(request, "Voce nao tem permissao para acessar esta pagina.")
        return None, False

    return empresa, True


def _obter_empresa_e_validar_permissao_tofu(request, empresa_id):
    return _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "TOFU Lista de Atividades",
    )
