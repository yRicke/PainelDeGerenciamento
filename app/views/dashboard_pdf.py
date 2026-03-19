import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone

from ..utils.modulos_permissoes import _obter_empresa_e_validar_permissao_modulo
from ..utils.pdf_renderer import render_template_to_pdf_bytes


DASHBOARD_EXPORT_CONFIG = {
    "financeiro_adiantamentos": {
        "modulo_nome": "Adiantamentos",
        "titulo_padrao": "Dashboard Adiantamentos",
    },
    "financeiro_dfc": {
        "modulo_nome": "DFC",
        "titulo_padrao": "Dashboard DFC",
    },
    "comercial_carteira": {
        "modulo_nome": "Carteira",
        "titulo_padrao": "Dashboard Carteira",
    },
    "comercial_vendas_por_categoria": {
        "modulo_nome": "Vendas por Categoria",
        "titulo_padrao": "Dashboard de Vendas por Categoria",
    },
    "comercial_pedidos_pendentes": {
        "modulo_nome": "Pedidos Pendentes",
        "titulo_padrao": "Dashboard Pedidos Pendentes",
    },
    "comercial_controle_de_margem": {
        "modulo_nome": "Controle de Margem",
        "titulo_padrao": "Dashboard Controle de Margem",
        "template_html": "dashboards_pdf/comercial/controle_de_margem.html",
        "template_text": "dashboards_pdf/comercial/controle_de_margem_texto.txt",
    },
    "operacional_estoque_pcp": {
        "modulo_nome": "Estoque - PCP",
        "titulo_padrao": "Dashboard Estoque - PCP",
    },
    "operacional_cargas_em_aberto": {
        "modulo_nome": "Cargas em Aberto",
        "titulo_padrao": "Dashboard Cargas em Aberto",
    },
    "operacional_producao": {
        "modulo_nome": "Producao",
        "titulo_padrao": "Dashboard Producao",
        "template_html": "dashboards_pdf/operacional/producao.html",
        "template_text": "dashboards_pdf/operacional/producao_texto.txt",
    },
    "administrativo_tofu_lista_de_atividades": {
        "modulo_nome": "TOFU Lista de Atividades",
        "titulo_padrao": "Dashboard TOFU Lista de Atividades",
        "template_html": "dashboards_pdf/administrativo/tofu_lista_de_atividades.html",
        "template_text": "dashboards_pdf/administrativo/tofu_lista_de_atividades_texto.txt",
    },
}


def _texto_limpo(valor, fallback="-", limite=220):
    texto = str(valor or "").strip()
    if not texto:
        return fallback
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


def _carregar_payload(request):
    bruto = request.POST.get("payload_json")
    if not bruto:
        return {}
    try:
        payload = json.loads(bruto)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalizar_kpis(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        label = _texto_limpo(item.get("label"), fallback="", limite=90)
        valor = _texto_limpo(item.get("value"), fallback="", limite=120)
        if not label or not valor:
            continue
        saida.append({"label": label, "value": valor})
        if len(saida) >= 40:
            break
    return saida


def _normalizar_filtros(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        texto = _texto_limpo(item, fallback="", limite=240)
        if texto:
            saida.append(texto)
        if len(saida) >= 80:
            break
    return saida or ["Nenhum filtro ativo."]


def _normalizar_graficos(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        titulo = _texto_limpo(item.get("title"), fallback="Grafico", limite=90)
        img_uri = str(item.get("img_uri") or "").strip()
        if not img_uri.startswith("data:image/"):
            continue
        saida.append({"title": titulo, "img_uri": img_uri})
        if len(saida) >= 30:
            break
    return saida


def _normalizar_percentual_num(valor):
    bruto = str(valor or "").strip().replace("%", "").replace(" ", "")
    if not bruto:
        return 0.0
    bruto = bruto.replace(".", "").replace(",", ".")
    try:
        numero = float(bruto)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, numero))


def _montar_contexto_generico(empresa, config, payload):
    kpis = _normalizar_kpis(payload.get("kpis"))
    graficos = _normalizar_graficos(payload.get("charts"))
    filtros = _normalizar_filtros(payload.get("filters"))

    return {
        "empresa": empresa,
        "gerado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        "titulo_dashboard": _texto_limpo(
            payload.get("title"),
            fallback=config.get("titulo_padrao") or "Dashboard",
            limite=120,
        ),
        "kpis": kpis,
        "graficos": graficos,
        "filtros_ativos": filtros,
        "detalhes_texto": _texto_limpo(payload.get("details"), fallback="-", limite=6000),
        "quantidade_kpis": len(kpis),
        "quantidade_graficos": len(graficos),
    }


def _normalizar_cards_tofu(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        linhas = []
        for linha in item.get("linhas") if isinstance(item.get("linhas"), list) else []:
            if not isinstance(linha, dict):
                continue
            label = _texto_limpo(linha.get("label"), fallback="", limite=80)
            valor = _texto_limpo(linha.get("value"), fallback="", limite=80)
            if not label or not valor:
                continue
            linhas.append({"label": label, "value": valor})
            if len(linhas) >= 6:
                break

        saida.append(
            {
                "titulo": _texto_limpo(item.get("titulo"), fallback="Indicador", limite=80),
                "percentual": _texto_limpo(item.get("percentual"), fallback="0,0%", limite=30),
                "tone": _texto_limpo(item.get("tone"), fallback="a-fazer", limite=20).lower(),
                "linhas": linhas,
            }
        )
        if len(saida) >= 8:
            break
    return saida


def _montar_contexto_tofu(empresa, config, payload):
    contexto_base = _montar_contexto_generico(empresa, config, payload)
    modulo = payload.get("module_payload") if isinstance(payload.get("module_payload"), dict) else {}
    contexto_base["tofu"] = {
        "total_atividades": _texto_limpo(modulo.get("total_atividades"), fallback="0", limite=30),
        "cards": _normalizar_cards_tofu(modulo.get("cards")),
    }
    return contexto_base


def _normalizar_cards_controle(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        saida.append(
            {
                "titulo": _texto_limpo(item.get("titulo"), fallback="Indicador", limite=80),
                "valor": _texto_limpo(item.get("valor"), fallback="R$ 0,00", limite=60),
                "tone": _texto_limpo(item.get("tone"), fallback="padrao", limite=20).lower(),
            }
        )
        if len(saida) >= 8:
            break
    return saida


def _normalizar_setores_controle(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        percentual_num = item.get("percentual_num")
        if percentual_num is None:
            percentual_num = _normalizar_percentual_num(item.get("percentual"))
        else:
            try:
                percentual_num = max(0.0, min(100.0, float(percentual_num)))
            except (TypeError, ValueError):
                percentual_num = 0.0

        saida.append(
            {
                "label": _texto_limpo(item.get("label"), fallback="Setor", limite=80),
                "valor": _texto_limpo(item.get("valor"), fallback="R$ 0,00", limite=60),
                "percentual": _texto_limpo(item.get("percentual"), fallback="0%", limite=20),
                "percentual_num": f"{percentual_num:.2f}",
                "tone": _texto_limpo(item.get("tone"), fallback="padrao", limite=20).lower(),
            }
        )
        if len(saida) >= 12:
            break
    return saida


def _montar_contexto_controle_margem(empresa, config, payload):
    contexto_base = _montar_contexto_generico(empresa, config, payload)
    modulo = payload.get("module_payload") if isinstance(payload.get("module_payload"), dict) else {}
    contexto_base["controle_margem"] = {
        "cards_principais": _normalizar_cards_controle(modulo.get("cards_principais")),
        "setores": _normalizar_setores_controle(modulo.get("setores")),
        "logistica": _normalizar_setores_controle(modulo.get("logistica")),
        "resumo_cards": _normalizar_cards_controle(modulo.get("resumo_cards")),
    }
    return contexto_base


def _normalizar_reloginhos_producao(payload):
    itens = payload if isinstance(payload, list) else []
    saida = []
    for item in itens:
        if not isinstance(item, dict):
            continue

        def _ang(valor):
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                numero = -90.0
            numero = max(-90.0, min(90.0, numero))
            return f"{numero:.2f}"

        saida.append(
            {
                "sufixo": _texto_limpo(item.get("sufixo"), fallback="", limite=20),
                "titulo": _texto_limpo(item.get("titulo"), fallback="Relogio", limite=60),
                "meta_acum": _texto_limpo(item.get("meta_acum"), fallback="0", limite=40),
                "real": _texto_limpo(item.get("real"), fallback="0", limite=40),
                "percentual": _texto_limpo(item.get("percentual"), fallback="0,00%", limite=20),
                "meta_angulo": _ang(item.get("meta_angulo")),
                "real_angulo": _ang(item.get("real_angulo")),
                "meta80_angulo": _ang(item.get("meta80_angulo")) if item.get("meta80_angulo") is not None else "",
            }
        )
        if len(saida) >= 8:
            break
    return saida


def _montar_contexto_producao(empresa, config, payload):
    contexto_base = _montar_contexto_generico(empresa, config, payload)
    modulo = payload.get("module_payload") if isinstance(payload.get("module_payload"), dict) else {}
    contexto_base["producao"] = {
        "reloginhos": _normalizar_reloginhos_producao(modulo.get("reloginhos")),
    }
    return contexto_base


CONTEXT_BUILDERS = {
    "administrativo_tofu_lista_de_atividades": _montar_contexto_tofu,
    "comercial_controle_de_margem": _montar_contexto_controle_margem,
    "operacional_producao": _montar_contexto_producao,
}


@login_required(login_url="entrar")
def dashboard_pdf_generico(request, empresa_id, dashboard_slug):
    slug = str(dashboard_slug or "").strip()
    config = DASHBOARD_EXPORT_CONFIG.get(slug)
    if not config:
        return JsonResponse({"detail": "Dashboard nao mapeado para exportacao."}, status=404)

    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        config["modulo_nome"],
    )
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Metodo nao permitido."}, status=405)

    payload = _carregar_payload(request)
    contexto_builder = CONTEXT_BUILDERS.get(slug, _montar_contexto_generico)
    contexto = contexto_builder(empresa, config, payload)
    template_text = config.get("template_text") or "dashboards_pdf/shared/generic_dashboard_texto.txt"
    texto_relatorio = render_to_string(
        template_text,
        contexto,
        request=request,
    )
    contexto_pdf = dict(contexto)
    contexto_pdf["texto_relatorio"] = texto_relatorio

    try:
        template_html = config.get("template_html") or "dashboards_pdf/shared/generic_dashboard.html"
        pdf_bytes = render_template_to_pdf_bytes(
            template_html,
            context=contexto_pdf,
            request=request,
        )
    except RuntimeError as erro:
        return JsonResponse({"detail": str(erro)}, status=500)

    resposta = HttpResponse(pdf_bytes, content_type="application/pdf")
    sufixo = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    sufixo_slug = str(dashboard_slug).replace("_", "-")
    resposta["Content-Disposition"] = (
        f'attachment; filename="dashboard-{sufixo_slug}-{sufixo}.pdf"'
    )
    return resposta
