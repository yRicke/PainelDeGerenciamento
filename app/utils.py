from .models import Permissao, Empresa
from django.contrib import messages
from datetime import date, datetime
from django.shortcuts import render, redirect

MODULOS_POR_AREA = {
    "Financeiro": [
        {"nome": "Comite Diario", "url": "comite_diario", "template": "financeiro/comite_diario.html"},
        {"nome": "Balanco Patrimonial", "url": "balanco_patrimonial", "template": "financeiro/balanco_patrimonial.html"},
        {"nome": "DRE", "url": "dre", "template": "financeiro/dre.html"},
        {"nome": "Contas a Receber", "url": "contas_a_receber", "template": "financeiro/contas_a_receber.html"},
        {"nome": "DFC", "url": "dfc", "template": "financeiro/dfc.html"},
        {"nome": "Adiantamentos", "url": "adiantamentos", "template": "financeiro/adiantamentos.html"},
        {"nome": "Contratos Redes", "url": "contratos_redes", "template": "financeiro/contratos_redes.html"},
    ],
    "Administrativo": [
        {"nome": "Plano de Cargos e Salarios", "url": "plano_de_cargos_e_salarios", "template": "administrativo/plano_de_cargos_e_salarios.html"},
        {"nome": "Descritivos", "url": "descritivos", "template": "administrativo/descritivos.html"},
        {"nome": "TOFU Lista de Atividades", "url": "tofu_lista_de_atividades", "template": "administrativo/tofu_lista_de_atividades.html"},
        {"nome": "Fiscal e Contabil", "url": "fiscal_e_contabil", "template": "administrativo/fiscal_e_contabil.html"},
        {"nome": "Faturamento", "url": "faturamento", "template": "administrativo/faturamento.html"},
        {"nome": "Apuracao de Resultados", "url": "apuracao_de_resultados", "template": "administrativo/apuracao_de_resultados.html"},
        {"nome": "Orcamento x Realizado", "url": "orcamento_x_realizado", "template": "administrativo/orcamento_x_realizado.html"},
        {"nome": "Colaboradores", "url": "colaboradores", "template": "administrativo/colaboradores.html"},
        {"nome": "Projetos", "url": "projetos", "template": "administrativo/projetos.html"},
    ],
    "Comercial": [
        {"nome": "Carteira", "url": "carteira", "template": "comercial/carteira.html"},
        {"nome": "Pedidos Pendentes", "url": "pedidos_pendentes", "template": "comercial/pedidos_pendentes.html"},
        {"nome": "Vendas por Categoria", "url": "vendas_por_categoria", "template": "comercial/vendas_por_categoria.html"},
        {"nome": "Precificacao", "url": "precificacao", "template": "comercial/precificacao.html"},
        {"nome": "Controle de Margem", "url": "controle_de_margem", "template": "comercial/controle_de_margem.html"},
    ],
    "Operacional": [
        {"nome": "Cargas em Aberto", "url": "cargas_em_aberto", "template": "operacional/cargas_em_aberto.html"},
        {"nome": "Operador Logistico", "url": "operador_logistico", "template": "operacional/operador_logistico.html"},
        {"nome": "Tabela de Fretes", "url": "tabela_de_fretes", "template": "operacional/tabela_de_fretes.html"},
        {"nome": "Estoque - PCP", "url": "estoque_pcp", "template": "operacional/estoque_pcp.html"},
        {"nome": "Producao", "url": "producao", "template": "operacional/producao.html"},
    ],
}

PERMISSOES_POR_MODULO = {
    area: [modulo["nome"] for modulo in modulos]
    for area, modulos in MODULOS_POR_AREA.items()
}

def _modulos_com_acesso(usuario, area):
    modulos = MODULOS_POR_AREA[area]

    if usuario.is_staff or usuario.is_superuser:
        return [
            {
                "nome": modulo["nome"],
                "url": modulo["url"],
                "permitido": True,
            }
            for modulo in modulos
        ]

    permissoes_usuario = set(usuario.permissoes.values_list("nome", flat=True))
    return [
        {
            "nome": modulo["nome"],
            "url": modulo["url"],
            "permitido": modulo["nome"] in permissoes_usuario,
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

    mesma_empresa = request.user.empresa_id == empresa.id
    tem_permissao = request.user.permissoes.filter(nome=nome_permissao).exists()
    if not ((mesma_empresa and tem_permissao) or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Voce nao tem permissao para acessar esta pagina.")
        return redirect("index")

    contexto = {
        "empresa": empresa,
        "modulo_nome": nome_permissao,
    }
    return render(request, template_path, contexto)

#TOFU
def _obter_empresa_e_validar_permissao_modulo(request, empresa_id, nome_permissao):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist:
        messages.error(request, "Empresa nao encontrada.")
        return None, False

    mesma_empresa = request.user.empresa_id == empresa.id
    tem_permissao = request.user.permissoes.filter(nome=nome_permissao).exists()
    if not ((mesma_empresa and tem_permissao) or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Voce nao tem permissao para acessar esta pagina.")
        return None, False

    return empresa, True


def _obter_empresa_e_validar_permissao_tofu(request, empresa_id):
    return _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "TOFU Lista de Atividades",
    )


def _transformar_int_ou_none(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _transformar_date_ou_none(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _transformar_iso_week_parts_ou_none(value):
    if not value:
        return None
    try:
        ano_str, semana_str = value.split("-W")
        ano = int(ano_str)
        semana = int(semana_str)
        if semana < 1 or semana > 53:
            return None
        date.fromisocalendar(ano, semana, 1)
        return ano, semana
    except (TypeError, ValueError):
        return None


def _set_prazo_inicio_e_prazo_termino(ano, semana):
    inicio = date.fromisocalendar(ano, semana, 1)
    termino = date.fromisocalendar(ano, semana, 7)
    return inicio, termino

