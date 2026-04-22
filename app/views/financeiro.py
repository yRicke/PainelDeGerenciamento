import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import FloatField, Max, Min, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Cast
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Adiantamento,
    BalancoPatrimonial,
    BalancoPatrimonialAtivo,
    Banco,
    CentroResultado,
    ComiteDiario,
    ContratoRede,
    ContaBancaria,
    ContasAReceber,
    DRE,
    EmpresaTitular,
    Faturamento,
    FluxoDeCaixaDFC,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
    Parceiro,
    SaldoLimite,
    Titulo,
)
from ..services.financeiro import (
    atualizar_adiantamento_por_post,
    atualizar_balanco_patrimonial_por_dados,
    atualizar_balanco_patrimonial_ativo_por_dados,
    atualizar_centro_resultado_por_dados,
    atualizar_contas_a_receber_por_post,
    atualizar_contrato_rede_por_post,
    atualizar_dfc_por_post,
    atualizar_natureza_por_dados,
    atualizar_operacao_por_dados,
    atualizar_orcamento_planejado_por_post,
    atualizar_orcamento_por_post,
    atualizar_saldo_limite_por_dados,
    atualizar_comite_diario_por_dados,
    atualizar_dre_por_post,
    atualizar_titulo_por_dados,
    construir_payload_tabela_saldo_dfc,
    criar_adiantamento_por_post,
    criar_balanco_patrimonial_por_dados,
    criar_balanco_patrimonial_ativo_por_dados,
    criar_centro_resultado_por_dados,
    criar_contas_a_receber_por_post,
    criar_contrato_rede_por_post,
    criar_dfc_por_post,
    criar_natureza_por_dados,
    criar_operacao_por_dados,
    criar_orcamento_planejado_por_post,
    criar_orcamento_por_post,
    criar_saldo_limite_por_dados,
    criar_comite_diario_por_dados,
    criar_titulo_por_dados,
    excluir_saldo_limite_por_dados,
    excluir_balanco_patrimonial_por_dados,
    excluir_balanco_patrimonial_ativo_por_dados,
    excluir_comite_diario_por_dados,
    excluir_dfc_por_dados,
    importar_upload_adiantamentos,
    importar_upload_comite_diario,
    importar_upload_contas_a_receber,
    importar_upload_dfc,
    importar_upload_orcamento,
    preparar_diretorios_adiantamentos,
    preparar_diretorios_comite_diario,
    preparar_diretorios_contas_a_receber,
    preparar_diretorios_dfc,
    preparar_diretorios_orcamento,
    salvar_dfc_saldo_manual_por_post,
    sincronizar_dre_por_empresa_dfc,
)
from ..tabulator import (
    build_adiantamentos_tabulator,
    build_balanco_patrimonial_tabulator,
    build_balanco_patrimonial_ativos_tabulator,
    build_centros_resultado_tabulator,
    build_contas_a_receber_tabulator,
    build_contratos_redes_tabulator,
    build_dre_tabulator,
    build_dfc_tabulator,
    build_naturezas_tabulator,
    build_operacoes_tabulator,
    build_orcamento_tabulator,
    build_orcamento_x_realizado_tabulator,
    build_orcamentos_planejados_tabulator,
    build_saldos_limites_tabulator,
    build_comite_diario_tabulator,
    build_titulos_tabulator,
)
from ..utils.modulos_permissoes import (
    _obter_empresa_e_validar_permissao_modulo,
    _render_modulo_com_permissao,
)
from ..utils.financeiro import (
    _aplicar_filtros_contas_a_receber,
    _opcoes_externas_contas_a_receber,
    _ordenar_contas_a_receber,
    _resumo_contas_a_receber,
    _resumo_dashboard_faturamento_contas_a_receber,
)
from ..utils.pdf_renderer import render_template_to_pdf_bytes
from .shared import (
    TIPO_IMPORTACAO_POR_MODULO,
    _bloquear_criar_em_modulo_com_importacao_se_necessario,
    _bloquear_edicao_em_modulo_com_importacao_se_necessario,
    _coletar_param_json_lista,
    _empresa_bloqueia_cadastro_edicao_importacao,
    _montar_resumo_importacao,
    _obter_modulo,
    _resumir_arquivos_existentes,
)


def _parse_data_dashboard_faturamento(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _payload_saldo_limite(item, empresa_id):
    registros = build_saldos_limites_tabulator([item], empresa_id)
    if not registros:
        return None
    return registros[0]


def _payload_comite_diario(item, empresa_id):
    registros = build_comite_diario_tabulator([item], empresa_id)
    if not registros:
        return None
    return registros[0]


def _payload_balanco_patrimonial(item, empresa_id):
    registros = build_balanco_patrimonial_tabulator([item], empresa_id)
    if not registros:
        return None
    return registros[0]


def _payload_balanco_patrimonial_ativo(item, empresa_id):
    registros = build_balanco_patrimonial_ativos_tabulator([item], empresa_id)
    if not registros:
        return None
    return registros[0]


def _payload_dre(item, empresa_id):
    registros = build_dre_tabulator([item], empresa_id, permitir_edicao=True)
    if not registros:
        return None
    return registros[0]


def _parse_iso_date_safe(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def _build_lancamentos_bancarios_payload(empresa, data_referencia_iso=""):
    data_referencia = _parse_iso_date_safe(data_referencia_iso)

    bancos_qs = Banco.objects.filter(empresa=empresa).order_by("nome", "id")
    bancos = [{"id": banco.id, "nome": banco.nome} for banco in bancos_qs]
    banco_ids = [item["id"] for item in bancos]

    linhas = {
        "saldo_atual": {str(banco_id): 0.0 for banco_id in banco_ids},
        "limite": {str(banco_id): 0.0 for banco_id in banco_ids},
        "antecipacoes": {str(banco_id): 0.0 for banco_id in banco_ids},
        "transferencias": {str(banco_id): 0.0 for banco_id in banco_ids},
    }

    saldos_qs = (
        SaldoLimite.objects.filter(empresa=empresa)
        .select_related("conta_bancaria", "conta_bancaria__banco")
    )
    data_saldos = data_referencia
    if data_saldos is None:
        data_saldos = saldos_qs.aggregate(data_max=Max("data")).get("data_max")
    if data_saldos:
        saldos_qs = saldos_qs.filter(data=data_saldos)
    else:
        saldos_qs = saldos_qs.none()

    agregados_saldos = (
        saldos_qs
        .values("conta_bancaria__banco_id", "tipo_movimentacao")
        .annotate(valor_total=Sum("valor_atual"))
    )
    saldos_por_banco_tipo = {}
    for item in agregados_saldos:
        banco_id = item.get("conta_bancaria__banco_id")
        tipo = str(item.get("tipo_movimentacao") or "").strip()
        if not banco_id or not tipo:
            continue
        chave = (int(banco_id), tipo)
        saldos_por_banco_tipo[chave] = float(item.get("valor_total") or 0)

    for banco_id in banco_ids:
        saldo_final = saldos_por_banco_tipo.get((banco_id, SaldoLimite.TIPO_SALDO_FINAL), 0.0)
        saldo_inicial = saldos_por_banco_tipo.get((banco_id, SaldoLimite.TIPO_SALDO_INICIAL), 0.0)
        limite_final = saldos_por_banco_tipo.get((banco_id, SaldoLimite.TIPO_LIMITE_FINAL), 0.0)
        limite_inicial = saldos_por_banco_tipo.get((banco_id, SaldoLimite.TIPO_LIMITE_INICIAL), 0.0)
        antecipacoes = saldos_por_banco_tipo.get((banco_id, SaldoLimite.TIPO_ANTECIPACAO), 0.0)

        linhas["saldo_atual"][str(banco_id)] = saldo_final if saldo_final != 0 else saldo_inicial
        linhas["limite"][str(banco_id)] = limite_final if limite_final != 0 else limite_inicial
        linhas["antecipacoes"][str(banco_id)] = antecipacoes

    comite_qs = ComiteDiario.objects.filter(empresa=empresa, decisao=ComiteDiario.DECISAO_TRANSFERIR)
    data_transferencias = data_referencia
    if data_transferencias is None:
        data_transferencias = comite_qs.aggregate(data_max=Max("data_vencimento")).get("data_max")
    if data_transferencias:
        comite_qs = comite_qs.filter(data_vencimento=data_transferencias)
    else:
        comite_qs = comite_qs.none()

    saidas = {
        int(item["de_banco_id"]): float(item["valor_total"] or 0)
        for item in (
            comite_qs
            .exclude(de_banco_id__isnull=True)
            .values("de_banco_id")
            .annotate(valor_total=Sum("valor_liquido"))
        )
        if item.get("de_banco_id")
    }
    entradas = {
        int(item["para_banco_id"]): float(item["valor_total"] or 0)
        for item in (
            comite_qs
            .exclude(para_banco_id__isnull=True)
            .values("para_banco_id")
            .annotate(valor_total=Sum("valor_liquido"))
        )
        if item.get("para_banco_id")
    }

    for banco_id in banco_ids:
        transferencia_liquida = float(saidas.get(banco_id, 0.0)) - float(entradas.get(banco_id, 0.0))
        linhas["transferencias"][str(banco_id)] = transferencia_liquida

    for chave in ("saldo_atual", "limite", "antecipacoes", "transferencias"):
        linhas[chave]["todos"] = sum(float(valor or 0) for valor in linhas[chave].values())

    return {
        "bancos": bancos,
        "linhas": linhas,
        "meta": {
            "data_referencia_filtro": data_referencia.isoformat() if data_referencia else "",
            "data_saldos": data_saldos.isoformat() if data_saldos else "",
            "data_transferencias": data_transferencias.isoformat() if data_transferencias else "",
        },
    }


def _formatar_moeda_br(valor):
    numero = float(valor or 0)
    valor_formatado = f"{numero:,.2f}"
    valor_formatado = valor_formatado.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {valor_formatado}"


def _formatar_percentual_br(valor):
    numero = float(valor or 0)
    return f"{numero:.2f}".replace(".", ",") + "%"


def _formatar_data_iso_br(valor):
    data = _parse_data_dashboard_faturamento(valor)
    return data.strftime("%d/%m/%Y") if data else "--/--/----"


def _formatar_valor_filtro_para_texto(valor):
    if isinstance(valor, (list, tuple, set)):
        valores = [str(item).strip() for item in valor if str(item).strip()]
        return ", ".join(valores) if valores else "-"
    texto = str(valor or "").strip()
    if not texto:
        return "-"
    if "||" in texto:
        valores = [item.strip() for item in texto.split("||") if item.strip()]
        return ", ".join(valores) if valores else "-"
    return texto


def _descrever_filtros_pagina_contas(filtros):
    if not filtros:
        return ["- Nenhum filtro de pagina aplicado."]

    titulos = {
        "status": "Status",
        "intervalo": "Intervalo",
        "data_arquivo_iso": "Data Arquivo",
        "titulo_descricao": "Descricao Tipo Titulo",
        "nome_fantasia_empresa": "Nome Fantasia Empresa",
        "natureza_descricao": "Descricao Natureza",
        "posicao_contagem": "Posicao",
        "data_negociacao": "Data Negociacao",
        "data_vencimento": "Data Vencimento",
        "numero_nota": "Numero Nota",
        "parceiro_nome": "Parceiro",
        "vendedor": "Vendedor",
        "operacao_descricao": "Receita/Despesa",
    }

    linhas = []
    for filtro in filtros:
        campo = str((filtro or {}).get("field") or "").strip()
        if not campo:
            continue
        tipo = str((filtro or {}).get("type") or "").strip().lower()
        valor = _formatar_valor_filtro_para_texto((filtro or {}).get("value"))
        titulo = titulos.get(campo, campo)
        sufixo = f" ({tipo})" if tipo and tipo not in {"=", "in"} else ""
        linhas.append(f"- {titulo}{sufixo}: {valor}")

    return linhas or ["- Nenhum filtro de pagina aplicado."]


def _carregar_payload_dashboard_comite_pdf(request):
    bruto = request.POST.get("payload_json")
    if not bruto:
        return {}
    try:
        payload = json.loads(bruto)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _texto_pdf_comite(valor, fallback="-", limite=220):
    texto = str(valor or "").strip()
    if not texto:
        return fallback
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


def _normalizar_linhas_pdf_comite(lista_linhas, limite_linhas=5000, limite_colunas=30):
    if not isinstance(lista_linhas, list):
        return []
    saida = []
    for linha in lista_linhas[:limite_linhas]:
        if isinstance(linha, dict):
            valores = linha.get("values")
        else:
            valores = linha
        if not isinstance(valores, list):
            continue
        saida.append(
            [_texto_pdf_comite(item, fallback="", limite=200) for item in valores[:limite_colunas]]
        )
    return saida


def _montar_contexto_dashboard_comite_pdf(empresa, payload):
    top_kpis = []
    for item in payload.get("top_kpis") if isinstance(payload.get("top_kpis"), list) else []:
        if not isinstance(item, dict):
            continue
        label = _texto_pdf_comite(item.get("label"), fallback="", limite=100)
        value = _texto_pdf_comite(item.get("value"), fallback="", limite=120)
        if not label:
            continue
        top_kpis.append({"label": label, "value": value or "-"})
        if len(top_kpis) >= 10:
            break

    lancamentos = payload.get("lancamentos") if isinstance(payload.get("lancamentos"), dict) else {}
    lancamentos_headers = [
        _texto_pdf_comite(item, fallback="", limite=90)
        for item in (lancamentos.get("headers") if isinstance(lancamentos.get("headers"), list) else [])[:30]
    ]
    lancamentos_rows = _normalizar_linhas_pdf_comite(lancamentos.get("rows"), limite_linhas=120, limite_colunas=30)
    lancamentos_meta = _texto_pdf_comite(lancamentos.get("meta"), fallback="", limite=300)

    resumo_rows = []
    for item in payload.get("resumo_rows") if isinstance(payload.get("resumo_rows"), list) else []:
        if not isinstance(item, dict):
            continue
        label = _texto_pdf_comite(item.get("label"), fallback="", limite=100)
        value = _texto_pdf_comite(item.get("value"), fallback="", limite=120)
        if not label:
            continue
        resumo_rows.append({"label": label, "value": value or "-"})
        if len(resumo_rows) >= 20:
            break

    tabela = payload.get("table") if isinstance(payload.get("table"), dict) else {}
    tabela_headers = [
        _texto_pdf_comite(item, fallback="", limite=90)
        for item in (tabela.get("headers") if isinstance(tabela.get("headers"), list) else [])[:30]
    ]
    tabela_rows = _normalizar_linhas_pdf_comite(tabela.get("rows"), limite_linhas=8000, limite_colunas=30)
    tabela_total_linhas = int(tabela.get("total_linhas") or len(tabela_rows))

    filtros_ativos = []
    for item in payload.get("filters") if isinstance(payload.get("filters"), list) else []:
        texto = _texto_pdf_comite(item, fallback="", limite=180)
        if texto:
            filtros_ativos.append(texto)
        if len(filtros_ativos) >= 120:
            break

    chart_img_uri = str(payload.get("chart_img_uri") or "").strip()
    if not chart_img_uri.startswith("data:image/"):
        chart_img_uri = ""

    return {
        "empresa": empresa,
        "gerado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        "titulo_dashboard": _texto_pdf_comite(
            payload.get("title"),
            fallback="Dashboard Comite Diario",
            limite=120,
        ),
        "top_kpis": top_kpis,
        "lancamentos_headers": lancamentos_headers,
        "lancamentos_rows": lancamentos_rows,
        "lancamentos_meta": lancamentos_meta,
        "resumo_rows": resumo_rows,
        "chart_img_uri": chart_img_uri,
        "filtros_ativos": filtros_ativos,
        "tabela_headers": tabela_headers,
        "tabela_rows": tabela_rows,
        "tabela_total_linhas": tabela_total_linhas,
    }


@login_required(login_url="entrar")
def comite_diario(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Comite Diario")
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not autorizado:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_comite_diario(empresa)
    dashboard_data_inicial_iso = str(request.GET.get("dashboard_data") or "").strip()

    if request.method == "POST":
        acao = str(request.POST.get("acao") or "").strip()
        if acao == "importar_comite_diario":
            arquivo = request.FILES.get("arquivo_comite_diario")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem, data_vencimento_referencia = importar_upload_comite_diario(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)

            redirect_url = reverse("comite_diario", kwargs={"empresa_id": empresa.id})
            if ok and data_vencimento_referencia:
                redirect_url = f"{redirect_url}?dashboard_data={data_vencimento_referencia}"
            return redirect(redirect_url)
        return redirect("comite_diario", empresa_id=empresa.id)

    comites_qs = (
        ComiteDiario.objects.filter(empresa=empresa)
        .select_related(
            "empresa_titular",
            "parceiro",
            "natureza",
            "centro_resultado",
            "de_banco",
            "para_banco",
            "para_empresa",
        )
        .order_by("-data_negociacao", "-id")
    )
    empresas_titulares_qs = EmpresaTitular.objects.filter(empresa=empresa).order_by("codigo", "id")
    parceiros_qs = Parceiro.objects.filter(empresa=empresa).order_by("codigo", "nome")
    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo", "descricao")
    centros_resultado_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao", "id")
    bancos_qs = Banco.objects.filter(empresa=empresa).order_by("nome", "id")
    ultima_data = comites_qs.aggregate(data_max=Max("data_negociacao")).get("data_max")
    saldo_adiantamentos_total = (
        Adiantamento.objects.filter(empresa=empresa).aggregate(total=Sum("saldo_real_em_reais")).get("total")
        or 0
    )
    filtros_intervalo_ate_90 = [
        {
            "field": "intervalo",
            "type": "in",
            "value": "0-5 (CML)||6-20 (FIN)||21-30 (POL)||31-60 (POL)||61-90 (POL)",
        }
    ]
    contas_receber_ate_90_qs = _aplicar_filtros_contas_a_receber(
        ContasAReceber.objects.filter(empresa=empresa),
        filtros_intervalo_ate_90,
    )
    resumo_contas_receber_ate_90 = _resumo_contas_a_receber(
        contas_receber_ate_90_qs,
        contas_receber_ate_90_qs.count(),
    )
    contas_receber_ate_90_valor = resumo_contas_receber_ate_90.get("valor_data_mais_recente") or 0
    bloquear_cadastro_edicao = _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="comite_diario",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )

    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "bloquear_cadastro_edicao_importacao": bloquear_cadastro_edicao,
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["comite_diario"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "dashboard_data_inicial_iso": dashboard_data_inicial_iso,
        "comite_diario_tabulator": build_comite_diario_tabulator(
            comites_qs,
            empresa.id,
            permitir_edicao=not bloquear_cadastro_edicao,
        ),
        "lancamentos_bancarios_payload": _build_lancamentos_bancarios_payload(empresa),
        "comite_dashboard_pdf_url": reverse(
            "comite_diario_dashboard_pdf",
            kwargs={"empresa_id": empresa.id},
        ),
        "comite_saldo_adiantamentos_texto": _formatar_moeda_br(saldo_adiantamentos_total),
        "comite_contas_receber_90_texto": _formatar_moeda_br(contas_receber_ate_90_valor),
        "empresas_titulares_opcoes": [
            {"id": item.id, "label": f"{item.codigo} - {item.nome}"}
            for item in empresas_titulares_qs
        ],
        "parceiros_opcoes": [
            {"id": item.id, "label": f"{item.codigo} - {item.nome}"}
            for item in parceiros_qs
        ],
        "naturezas_opcoes": [
            {"id": item.id, "label": f"{item.codigo} - {item.descricao}"}
            for item in naturezas_qs
        ],
        "centros_resultado_opcoes": [
            {"id": item.id, "label": item.descricao}
            for item in centros_resultado_qs
        ],
        "bancos_opcoes": [
            {"id": item.id, "label": item.nome}
            for item in bancos_qs
        ],
        "receita_despesa_opcoes": [
            {"value": value, "label": label}
            for value, label in ComiteDiario.RECEITA_DESPESA_CHOICES
        ],
        "tipo_movimento_opcoes": [
            {"value": value, "label": label}
            for value, label in ComiteDiario.TIPO_MOVIMENTO_CHOICES
        ],
        "decisao_opcoes": [
            {"value": value, "label": label}
            for value, label in ComiteDiario.DECISAO_CHOICES
        ],
        "hoje_iso": timezone.localdate().isoformat(),
        "ultima_data_iso": ultima_data.isoformat() if ultima_data else "",
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def comite_diario_lancamentos_dashboard_data(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Comite Diario")
    if not autorizado:
        return JsonResponse({"ok": False, "message": "Sem permissao."}, status=403)

    data_referencia_iso = str(request.GET.get("data") or "").strip()
    payload = _build_lancamentos_bancarios_payload(empresa, data_referencia_iso)
    return JsonResponse({"ok": True, "payload": payload})


@login_required(login_url="entrar")
def comite_diario_dashboard_pdf(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Comite Diario")
    if not autorizado:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Metodo nao permitido."}, status=405)

    payload = _carregar_payload_dashboard_comite_pdf(request)
    contexto = _montar_contexto_dashboard_comite_pdf(empresa, payload)

    try:
        pdf_bytes = render_template_to_pdf_bytes(
            "dashboards_pdf/financeiro/comite_diario.html",
            context=contexto,
            request=request,
        )
    except RuntimeError as erro:
        return JsonResponse({"detail": str(erro)}, status=500)

    resposta = HttpResponse(pdf_bytes, content_type="application/pdf")
    sufixo = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    resposta["Content-Disposition"] = (
        f'attachment; filename="dashboard-comite-diario-{sufixo}.pdf"'
    )
    return resposta


@login_required(login_url="entrar")
def criar_comite_diario_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Comite Diario")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("comite_diario", empresa_id=empresa.id)
    if _bloquear_criar_em_modulo_com_importacao_se_necessario(
        request,
        empresa,
        "criar_comite_diario",
        {"criar_comite_diario"},
    ):
        return redirect("comite_diario", empresa_id=empresa.id)

    erro = criar_comite_diario_por_dados(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("comite_diario", empresa_id=empresa.id)

    item = (
        ComiteDiario.objects.filter(empresa=empresa)
        .select_related(
            "empresa_titular",
            "parceiro",
            "natureza",
            "centro_resultado",
            "de_banco",
            "para_banco",
            "para_empresa",
        )
        .order_by("-id")
        .first()
    )

    if _is_ajax_request(request):
        if item is None:
            return JsonResponse(
                {"ok": False, "message": "Registro criado, mas nao foi possivel recarregar os dados."},
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_comite_diario(item, empresa.id),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("comite_diario", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_comite_diario_modulo(request, empresa_id, comite_diario_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Comite Diario")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("comite_diario", empresa_id=empresa.id)
    bloqueio_redirect = _bloquear_edicao_em_modulo_com_importacao_se_necessario(
        request,
        empresa,
        "comite_diario",
    )
    if bloqueio_redirect:
        return bloqueio_redirect

    item = ComiteDiario.objects.filter(id=comite_diario_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("comite_diario", empresa_id=empresa.id)

    erro = atualizar_comite_diario_por_dados(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("comite_diario", empresa_id=empresa.id)

    item = (
        ComiteDiario.objects.filter(id=item.id, empresa=empresa)
        .select_related(
            "empresa_titular",
            "parceiro",
            "natureza",
            "centro_resultado",
            "de_banco",
            "para_banco",
            "para_empresa",
        )
        .first()
    )

    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_comite_diario(item, empresa.id) if item else None,
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("comite_diario", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_comite_diario_modulo(request, empresa_id, comite_diario_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Comite Diario")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("comite_diario", empresa_id=empresa.id)
    bloqueio_redirect = _bloquear_edicao_em_modulo_com_importacao_se_necessario(
        request,
        empresa,
        "comite_diario",
    )
    if bloqueio_redirect:
        return bloqueio_redirect

    item = ComiteDiario.objects.filter(id=comite_diario_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("comite_diario", empresa_id=empresa.id)

    erro = excluir_comite_diario_por_dados(item, empresa)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("comite_diario", empresa_id=empresa.id)

    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "message": "Registro excluido com sucesso.", "id": comite_diario_id})

    messages.success(request, "Registro excluido com sucesso.")
    return redirect("comite_diario", empresa_id=empresa.id)


@login_required(login_url="entrar")
def balanco_patrimonial(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Balanco Patrimonial")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    registros_qs = BalancoPatrimonial.objects.filter(empresa=empresa).order_by(
        "-data_balanco_patrimonial",
        "-numero_registro",
        "-id",
    )

    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "balanco_patrimonial_tabulator": build_balanco_patrimonial_tabulator(registros_qs, empresa.id),
        "balanco_patrimonial_empresas_bp_opcoes": [
            {"value": value, "label": label}
            for value, label in BalancoPatrimonial.EMPRESA_BALANCO_PATRIMONIAL_CHOICES
        ],
        "balanco_patrimonial_tipo_movimentacao_opcoes": [
            {"value": "", "label": "Sem tipo"},
        ] + [
            {"value": value, "label": label}
            for value, label in BalancoPatrimonial.TIPO_MOVIMENTACAO_CHOICES
        ],
        "balanco_patrimonial_proximo_numero_registro": BalancoPatrimonial.proximo_numero_registro(empresa),
        "balanco_patrimonial_ativos_url": reverse("balanco_patrimonial_ativos", kwargs={"empresa_id": empresa.id}),
        "hoje_iso": timezone.localdate().isoformat(),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def criar_balanco_patrimonial_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    erro = criar_balanco_patrimonial_por_dados(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    item = BalancoPatrimonial.objects.filter(empresa=empresa).order_by("-id").first()
    if _is_ajax_request(request):
        if item is None:
            return JsonResponse(
                {"ok": False, "message": "Registro criado, mas nao foi possivel recarregar os dados."},
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_balanco_patrimonial(item, empresa.id),
                "proximo_numero_registro": BalancoPatrimonial.proximo_numero_registro(empresa),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("balanco_patrimonial", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_balanco_patrimonial_modulo(request, empresa_id, balanco_patrimonial_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    item = BalancoPatrimonial.objects.filter(id=balanco_patrimonial_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    erro = atualizar_balanco_patrimonial_por_dados(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    item = BalancoPatrimonial.objects.filter(id=item.id, empresa=empresa).first()
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_balanco_patrimonial(item, empresa.id) if item else None,
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("balanco_patrimonial", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_balanco_patrimonial_modulo(request, empresa_id, balanco_patrimonial_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    item = BalancoPatrimonial.objects.filter(id=balanco_patrimonial_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    erro = excluir_balanco_patrimonial_por_dados(item, empresa)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial", empresa_id=empresa.id)

    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro excluido com sucesso.",
                "id": balanco_patrimonial_id,
                "proximo_numero_registro": BalancoPatrimonial.proximo_numero_registro(empresa),
            }
        )

    messages.success(request, "Registro excluido com sucesso.")
    return redirect("balanco_patrimonial", empresa_id=empresa.id)


@login_required(login_url="entrar")
def balanco_patrimonial_ativos(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not permitido:
        return redirect("index")

    registros_qs = BalancoPatrimonialAtivo.objects.filter(empresa=empresa).order_by("-id")
    status_opcoes = []
    for status in (
        registros_qs.exclude(status__isnull=True)
        .exclude(status__exact="")
        .values_list("status", flat=True)
        .distinct()
        .order_by("status")
    ):
        status_opcoes.append({"value": status, "label": status})

    contexto = {
        "empresa": empresa,
        "modulo_nome": "Balanco Patrimonial - Ativos",
        "balanco_patrimonial_ativos_tabulator": build_balanco_patrimonial_ativos_tabulator(registros_qs, empresa.id),
        "balanco_patrimonial_ativos_empresas_bp_opcoes": [
            {"value": value, "label": label}
            for value, label in BalancoPatrimonialAtivo.EMPRESA_BP_CHOICES
        ],
        "balanco_patrimonial_ativos_categorias_opcoes": [
            {"value": value, "label": label}
            for value, label in BalancoPatrimonialAtivo.CATEGORIA_CHOICES
        ],
        "balanco_patrimonial_ativos_status_opcoes": status_opcoes,
        "hoje_iso": timezone.localdate().isoformat(),
    }
    return render(request, "financeiro/balanco_patrimonial_ativos.html", contexto)


@login_required(login_url="entrar")
def criar_balanco_patrimonial_ativo_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    erro = criar_balanco_patrimonial_ativo_por_dados(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    item = BalancoPatrimonialAtivo.objects.filter(empresa=empresa).order_by("-id").first()
    if _is_ajax_request(request):
        if item is None:
            return JsonResponse(
                {"ok": False, "message": "Registro criado, mas nao foi possivel recarregar os dados."},
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_balanco_patrimonial_ativo(item, empresa.id),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_balanco_patrimonial_ativo_modulo(request, empresa_id, ativo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    item = BalancoPatrimonialAtivo.objects.filter(id=ativo_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    erro = atualizar_balanco_patrimonial_ativo_por_dados(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    item = BalancoPatrimonialAtivo.objects.filter(id=item.id, empresa=empresa).first()
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_balanco_patrimonial_ativo(item, empresa.id) if item else None,
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_balanco_patrimonial_ativo_modulo(request, empresa_id, ativo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Balanco Patrimonial")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    item = BalancoPatrimonialAtivo.objects.filter(id=ativo_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    erro = excluir_balanco_patrimonial_ativo_por_dados(item, empresa)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)

    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "message": "Registro excluido com sucesso.", "id": ativo_id})

    messages.success(request, "Registro excluido com sucesso.")
    return redirect("balanco_patrimonial_ativos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def dre(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "DRE")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    total_dfc = FluxoDeCaixaDFC.objects.filter(empresa=empresa).count()
    total_dre = DRE.objects.filter(empresa=empresa).count()
    if total_dre != total_dfc:
        sincronizar_dre_por_empresa_dfc(empresa)

    dre_qs = (
        DRE.objects.filter(empresa=empresa)
        .annotate(
            valor_liquido_num=Cast("valor_liquido", FloatField()),
            valor_a_pagar_num=Cast("valor_a_pagar", FloatField()),
        )
        .values(
            "id",
            "empresa_id",
            "dfc_id",
            "data_baixa",
            "data_vencimento",
            "nome_fantasia_empresa",
            "receita_despesa",
            "parceiro",
            "nome_parceiro",
            "numero_nota",
            "natureza",
            "descricao_natureza",
            "valor_liquido_num",
            "valor_a_pagar_num",
            "descricao_tipo_operacao",
            "descricao_centro_resultado",
            "plano_contas_tipo_movimento",
            "tipo_dre",
        )
        .order_by("-data_baixa", "-id")
    )
    dre_registros = list(dre_qs)

    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "dre_tabulator": build_dre_tabulator(dre_registros, empresa.id, permitir_edicao=True),
        "dfc_url": reverse("dfc", kwargs={"empresa_id": empresa.id}),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def contas_a_receber(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_contas_a_receber(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_conta"},
        ):
            return redirect("contas_a_receber", empresa_id=empresa.id)
        if acao == "criar_conta":
            erro = criar_contas_a_receber_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Contas a Receber criado com sucesso.")
        else:
            arquivos = request.FILES.getlist("arquivos_contas_a_receber")
            ok, mensagem = importar_upload_contas_a_receber(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("contas_a_receber", empresa_id=empresa.id)

    arquivos_existentes = sorted(
        [
            str(f.relative_to(diretorio_importacao)).replace("\\", "/")
            for f in diretorio_importacao.rglob("*.xls")
            if diretorio_subscritos not in f.parents
        ]
    )
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="contas_a_receber",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    dashboard_empresas = list(
        ContasAReceber.objects.filter(empresa=empresa)
        .exclude(nome_fantasia_empresa="")
        .order_by("nome_fantasia_empresa")
        .values_list("nome_fantasia_empresa", flat=True)
        .distinct()
    )
    dashboard_periodo = Faturamento.objects.filter(empresa=empresa).aggregate(
        periodo_inicio=Min("data_faturamento"),
        periodo_fim=Max("data_faturamento"),
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["contas_a_receber"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "contas_tabulator_url": reverse("contas_a_receber_dados", kwargs={"empresa_id": empresa.id}),
        "contas_dashboard_faturamento_url": reverse(
            "contas_a_receber_dashboard_faturamento",
            kwargs={"empresa_id": empresa.id},
        ),
        "contas_dashboard_pdf_url": reverse(
            "contas_a_receber_dashboard_pdf",
            kwargs={"empresa_id": empresa.id},
        ),
        "contas_dashboard_empresas": dashboard_empresas,
        "contas_dashboard_periodo_inicio_padrao": (
            dashboard_periodo["periodo_inicio"].isoformat()
            if dashboard_periodo.get("periodo_inicio")
            else ""
        ),
        "contas_dashboard_periodo_fim_padrao": (
            dashboard_periodo["periodo_fim"].isoformat()
            if dashboard_periodo.get("periodo_fim")
            else ""
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def contas_a_receber_dados(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)

    page_raw = str(request.GET.get("page") or "").strip()
    size_raw = str(request.GET.get("size") or "").strip()
    try:
        page = int(page_raw) if page_raw else 1
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(size_raw) if size_raw else 100
    except (TypeError, ValueError):
        page_size = 100

    page = max(page, 1)
    page_size = max(1, min(page_size, 200))

    filtros = _coletar_param_json_lista(request, ("filters", "filter"))
    sorters = _coletar_param_json_lista(request, ("sorters", "sort"))

    base_qs = ContasAReceber.objects.filter(empresa=empresa)
    filtrado_qs = _aplicar_filtros_contas_a_receber(base_qs, filtros)
    ordenado_qs = _ordenar_contas_a_receber(filtrado_qs, sorters)
    filtros_externos = _opcoes_externas_contas_a_receber(base_qs, filtros)

    total_registros = ordenado_qs.count()
    total_paginas = max(1, (total_registros + page_size - 1) // page_size)
    if page > total_paginas:
        page = total_paginas

    inicio = (page - 1) * page_size
    fim = inicio + page_size

    contas_pagina_qs = (
        ordenado_qs
        .annotate(
            valor_desdobramento_num=Cast("valor_desdobramento", FloatField()),
            valor_liquido_num=Cast("valor_liquido", FloatField()),
        )
        .values(
            "id",
            "data_negociacao",
            "data_vencimento",
            "data_arquivo",
            "nome_fantasia_empresa",
            "numero_nota",
            "vendedor",
            "valor_desdobramento_num",
            "valor_liquido_num",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "parceiro__codigo",
            "parceiro__nome",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
        )[inicio:fim]
    )

    permitir_edicao = not _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    dados = build_contas_a_receber_tabulator(
        contas_pagina_qs,
        empresa.id,
        permitir_edicao=permitir_edicao,
    )
    resumo = _resumo_contas_a_receber(filtrado_qs, total_registros)

    return JsonResponse(
        {
            "data": dados,
            "last_page": total_paginas,
            "last_row": total_registros,
            "summary": resumo,
            "external_filters": filtros_externos,
        }
    )


@login_required(login_url="entrar")
def contas_a_receber_dashboard_faturamento(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)

    periodo_inicio = _parse_data_dashboard_faturamento(request.GET.get("periodo_inicio"))
    periodo_fim = _parse_data_dashboard_faturamento(request.GET.get("periodo_fim"))
    empresa_filtro = str(request.GET.get("empresa") or "").strip()

    payload = _resumo_dashboard_faturamento_contas_a_receber(
        qs_contas=ContasAReceber.objects.filter(empresa=empresa),
        qs_faturamento=Faturamento.objects.filter(empresa=empresa),
        data_inicio=periodo_inicio,
        data_fim=periodo_fim,
        empresa_filtro=empresa_filtro,
    )
    return JsonResponse(payload)


@login_required(login_url="entrar")
def contas_a_receber_dashboard_pdf(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)

    periodo_inicio = _parse_data_dashboard_faturamento(request.GET.get("periodo_inicio"))
    periodo_fim = _parse_data_dashboard_faturamento(request.GET.get("periodo_fim"))
    empresa_filtro = str(request.GET.get("empresa") or "").strip()
    filtros_pagina = _coletar_param_json_lista(request, ("filters", "filter"))

    qs_contas = ContasAReceber.objects.filter(empresa=empresa)
    qs_contas_filtrado = _aplicar_filtros_contas_a_receber(qs_contas, filtros_pagina)
    qs_faturamento = Faturamento.objects.filter(empresa=empresa)
    resumo_dashboard = _resumo_contas_a_receber(qs_contas_filtrado, qs_contas_filtrado.count())
    resumo_faturamento = _resumo_dashboard_faturamento_contas_a_receber(
        qs_contas=qs_contas,
        qs_faturamento=qs_faturamento,
        data_inicio=periodo_inicio,
        data_fim=periodo_fim,
        empresa_filtro=empresa_filtro,
    )

    contexto = {
        "empresa": empresa,
        "gerado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        "analitico": {
            "data_mais_recente": _formatar_data_iso_br(resumo_dashboard.get("data_mais_recente")),
            "valor_data_mais_recente": _formatar_moeda_br(resumo_dashboard.get("valor_data_mais_recente")),
            "quantidade_data_mais_recente": int(resumo_dashboard.get("quantidade_data_mais_recente") or 0),
        },
        "faturamento": {
            "periodo_inicio": _formatar_data_iso_br(resumo_faturamento.get("periodo_inicio")),
            "periodo_fim": _formatar_data_iso_br(resumo_faturamento.get("periodo_fim")),
            "empresa_filtro": resumo_faturamento.get("empresa") or "Todas",
            "faturamento_total": _formatar_moeda_br(resumo_faturamento.get("faturamento_total")),
            "inadimplencia_percentual": _formatar_percentual_br(resumo_faturamento.get("inadimplencia_percentual")),
            "data_snapshot": _formatar_data_iso_br(resumo_faturamento.get("data_snapshot")),
        },
        "periodo": {
            "data_inicial": _formatar_data_iso_br(resumo_dashboard.get("data_inicial")),
            "valor_data_inicial": _formatar_moeda_br(resumo_dashboard.get("valor_data_inicial")),
            "data_final": _formatar_data_iso_br(resumo_dashboard.get("data_final")),
            "valor_data_final": _formatar_moeda_br(resumo_dashboard.get("valor_data_final")),
            "diferenca_periodo": _formatar_moeda_br(resumo_dashboard.get("diferenca_periodo")),
        },
        "filtros_pagina": _descrever_filtros_pagina_contas(filtros_pagina),
    }
    texto_relatorio = render_to_string(
        "dashboards_pdf/financeiro/contas_a_receber_texto.txt",
        contexto,
        request=request,
    )
    contexto_pdf = dict(contexto)
    contexto_pdf["texto_relatorio"] = texto_relatorio
    try:
        pdf_bytes = render_template_to_pdf_bytes(
            "dashboards_pdf/financeiro/contas_a_receber.html",
            context=contexto_pdf,
            request=request,
        )
    except RuntimeError as erro:
        return JsonResponse({"detail": str(erro)}, status=500)

    resposta = HttpResponse(pdf_bytes, content_type="application/pdf")
    sufixo = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    resposta["Content-Disposition"] = (
        f'attachment; filename="dashboard-contas-a-receber-{sufixo}.pdf"'
    )
    return resposta


@login_required(login_url="entrar")
def dfc(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "DFC")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_dfc(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "salvar_dfc_saldo_manual":
            ok, mensagem, valor = salvar_dfc_saldo_manual_por_post(empresa, request.POST)
            status = 200 if ok else 400
            return JsonResponse(
                {
                    "ok": ok,
                    "message": mensagem,
                    "valor": float(valor),
                },
                status=status,
            )
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_dfc"},
        ):
            return redirect("dfc", empresa_id=empresa.id)
        if acao == "criar_dfc":
            erro = criar_dfc_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de DFC criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_dfc")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_dfc(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("dfc", empresa_id=empresa.id)

    dfc_qs = (
        FluxoDeCaixaDFC.objects.filter(empresa=empresa)
        .annotate(valor_liquido_num=Cast("valor_liquido", FloatField()))
        .values(
            "id",
            "empresa_id",
            "empresa__nome",
            "data_negociacao",
            "data_vencimento",
            "valor_liquido_num",
            "numero_nota",
            "titulo_id",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "centro_resultado_id",
            "centro_resultado__descricao",
            "natureza_id",
            "natureza__codigo",
            "natureza__descricao",
            "historico",
            "parceiro_id",
            "parceiro__codigo",
            "parceiro__nome",
            "operacao_id",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
            "tipo_movimento",
        )
        .order_by("-id")
    )
    dfc_registros = list(dfc_qs)

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="dfc",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["dfc"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "dfc_tabulator": build_dfc_tabulator(
            dfc_registros,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
        "dfc_saldo_planejado": construir_payload_tabela_saldo_dfc(empresa, dfc_registros),
    }
    return render(request, modulo["template"], contexto)


def _orcamentos_realizados_qs_para_tabulator(empresa):
    return (
        Orcamento.objects.filter(empresa=empresa)
        .annotate(
            valor_baixa_num=Cast("valor_baixa", FloatField()),
            valor_liquido_num=Cast("valor_liquido", FloatField()),
            valor_desdobramento_num=Cast("valor_desdobramento", FloatField()),
        )
        .values(
            "id",
            "nome_empresa",
            "data_vencimento",
            "data_baixa",
            "valor_baixa_num",
            "valor_liquido_num",
            "valor_desdobramento_num",
            "titulo_id",
            "natureza_id",
            "centro_resultado_id",
            "operacao_id",
            "parceiro_id",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
            "parceiro__codigo",
            "parceiro__nome",
        )
        .order_by("-data_vencimento", "-id")
    )


def _orcamentos_planejados_qs_para_tabulator(empresa):
    return (
        OrcamentoPlanejado.objects.filter(empresa=empresa)
        .annotate(
            janeiro_num=Cast("janeiro", FloatField()),
            fevereiro_num=Cast("fevereiro", FloatField()),
            marco_num=Cast("marco", FloatField()),
            abril_num=Cast("abril", FloatField()),
            maio_num=Cast("maio", FloatField()),
            junho_num=Cast("junho", FloatField()),
            julho_num=Cast("julho", FloatField()),
            agosto_num=Cast("agosto", FloatField()),
            setembro_num=Cast("setembro", FloatField()),
            outubro_num=Cast("outubro", FloatField()),
            novembro_num=Cast("novembro", FloatField()),
            dezembro_num=Cast("dezembro", FloatField()),
        )
        .values(
            "id",
            "nome_empresa",
            "ano",
            "natureza_id",
            "centro_resultado_id",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "janeiro_num",
            "fevereiro_num",
            "marco_num",
            "abril_num",
            "maio_num",
            "junho_num",
            "julho_num",
            "agosto_num",
            "setembro_num",
            "outubro_num",
            "novembro_num",
            "dezembro_num",
            "natureza__descricao",
            "centro_resultado__descricao",
        )
        .order_by("ano", "centro_resultado__descricao", "natureza__descricao")
    )


@login_required(login_url="entrar")
def orcamento(request, empresa_id):
    modulo = {"nome": "Orcamento x Realizado", "template": "administrativo/orcamento.html"}
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_orcamento(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "importar_orcamento":
            arquivos = request.FILES.getlist("arquivos_orcamento")
            ok, mensagem = importar_upload_orcamento(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.error(request, "Acao de importacao invalida.")
        return redirect("orcamento", empresa_id=empresa.id)

    orcamentos_realizados_qs = _orcamentos_realizados_qs_para_tabulator(empresa)
    orcamentos_qs = _orcamentos_planejados_qs_para_tabulator(empresa)

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="orcamento",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["orcamento"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "orcamento_x_realizado_tabulator": build_orcamento_x_realizado_tabulator(
            orcamentos_realizados_qs,
            orcamentos_qs,
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def orcamentos_realizados(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "criar_orcamento":
            erro = criar_orcamento_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Orcamento criado com sucesso.")
        else:
            messages.error(request, "Acao de Orcamento invalida.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamentos_realizados_qs = _orcamentos_realizados_qs_para_tabulator(empresa)

    titulos_qs = Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo")
    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    operacoes_qs = Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo")
    parceiros_qs = Parceiro.objects.filter(empresa=empresa).order_by("nome")
    centros_resultado_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")

    contexto = {
        "empresa": empresa,
        "orcamento_tabulator": build_orcamento_tabulator(orcamentos_realizados_qs, empresa.id),
        "titulos": titulos_qs,
        "naturezas": naturezas_qs,
        "operacoes": operacoes_qs,
        "parceiros": parceiros_qs,
        "centros_resultado": centros_resultado_qs,
        "orcamento_titulos_js": list(
            titulos_qs.values("id", "tipo_titulo_codigo", "descricao")
        ),
        "orcamento_naturezas_js": list(
            naturezas_qs.values("id", "codigo", "descricao")
        ),
        "orcamento_operacoes_js": list(
            operacoes_qs.values("id", "tipo_operacao_codigo", "descricao_receita_despesa")
        ),
        "orcamento_parceiros_js": list(
            parceiros_qs.values("id", "codigo", "nome")
        ),
        "orcamento_centros_resultado_js": list(
            centros_resultado_qs.values("id", "descricao")
        ),
    }
    return render(request, "administrativo/orcamentos_realizados.html", contexto)


@login_required(login_url="entrar")
def orcamentos(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "criar_orcamento_planejado":
            erro = criar_orcamento_planejado_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Orcamento planejado criado com sucesso.")
        else:
            messages.error(request, "Acao de Orcamento invalida.")
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamentos_qs = _orcamentos_planejados_qs_para_tabulator(empresa)

    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    centros_resultado_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")

    contexto = {
        "empresa": empresa,
        "orcamentos_tabulator": build_orcamentos_planejados_tabulator(orcamentos_qs, empresa.id),
        "naturezas": naturezas_qs,
        "centros_resultado": centros_resultado_qs,
        "orcamento_planejado_naturezas_js": list(
            naturezas_qs.values("id", "codigo", "descricao")
        ),
        "orcamento_planejado_centros_resultado_js": list(
            centros_resultado_qs.values("id", "descricao")
        ),
    }
    return render(request, "administrativo/orcamentos.html", contexto)


@login_required(login_url="entrar")
def editar_orcamento_modulo(request, empresa_id, orcamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    orcamento_item = Orcamento.objects.filter(id=orcamento_id, empresa=empresa).first()
    if not orcamento_item:
        messages.error(request, "Registro de Orcamento nao encontrado.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_orcamento_por_post(orcamento_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_orcamento_modulo", empresa_id=empresa.id, orcamento_id=orcamento_item.id)
        messages.success(request, "Registro de Orcamento atualizado com sucesso.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "orcamento_item": orcamento_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "administrativo/orcamento_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_orcamento_modulo(request, empresa_id, orcamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamento_item = Orcamento.objects.filter(id=orcamento_id, empresa=empresa).first()
    if not orcamento_item:
        messages.error(request, "Registro de Orcamento nao encontrado.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamento_item.excluir_orcamento()
    messages.success(request, "Registro de Orcamento excluido com sucesso.")
    return redirect("orcamentos_realizados", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_orcamento_planejado_modulo(request, empresa_id, orcamento_planejado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    orcamento_planejado_item = OrcamentoPlanejado.objects.filter(id=orcamento_planejado_id, empresa=empresa).first()
    if not orcamento_planejado_item:
        messages.error(request, "Orcamento planejado nao encontrado.")
        return redirect("orcamentos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_orcamento_planejado_por_post(orcamento_planejado_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect(
                "editar_orcamento_planejado_modulo",
                empresa_id=empresa.id,
                orcamento_planejado_id=orcamento_planejado_item.id,
            )
        messages.success(request, "Orcamento planejado atualizado com sucesso.")
        return redirect("orcamentos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "orcamento_planejado_item": orcamento_planejado_item,
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "administrativo/orcamento_planejado_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_orcamento_planejado_modulo(request, empresa_id, orcamento_planejado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamento_planejado_item = OrcamentoPlanejado.objects.filter(id=orcamento_planejado_id, empresa=empresa).first()
    if not orcamento_planejado_item:
        messages.error(request, "Orcamento planejado nao encontrado.")
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamento_planejado_item.excluir_orcamento_planejado()
    messages.success(request, "Orcamento planejado excluido com sucesso.")
    return redirect("orcamentos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def adiantamentos(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Adiantamentos")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_adiantamentos(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_adiantamento"},
        ):
            return redirect("adiantamentos", empresa_id=empresa.id)
        if acao == "criar_adiantamento":
            erro = criar_adiantamento_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Adiantamentos criado com sucesso.")
        else:
            arquivos = request.FILES.getlist("arquivos_adiantamentos")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_adiantamentos(
                empresa=empresa,
                arquivos=arquivos,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("adiantamentos", empresa_id=empresa.id)

    adiantamentos_qs = (
        Adiantamento.objects.filter(empresa=empresa)
        .annotate(
            saldo_banco_em_reais_num=Cast("saldo_banco_em_reais", FloatField()),
            saldo_real_em_reais_num=Cast("saldo_real_em_reais", FloatField()),
            saldo_real_num=Cast("saldo_real", FloatField()),
        )
        .values(
            "id",
            "empresa_id",
            "empresa__nome",
            "data_arquivo",
            "moeda",
            "saldo_banco_em_reais_num",
            "saldo_real_em_reais_num",
            "saldo_real_num",
            "conta_descricao",
            "saldo_banco",
            "banco",
            "agencia",
            "conta_bancaria",
            "empresa_descricao",
        )
        .order_by("-data_arquivo", "-id")
    )

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="adiantamentos",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["adiantamentos"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "adiantamentos_tabulator": build_adiantamentos_tabulator(
            adiantamentos_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def saldos_e_limites(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Saldos e Limites")
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not autorizado:
        return redirect("index")

    saldos_qs = (
        SaldoLimite.objects.filter(empresa=empresa)
        .select_related("empresa_titular", "conta_bancaria", "conta_bancaria__banco")
        .order_by("-data", "-id")
    )
    empresas_titulares_qs = EmpresaTitular.objects.filter(empresa=empresa).order_by("codigo", "id")
    contas_bancarias_qs = (
        ContaBancaria.objects.filter(empresa=empresa)
        .select_related("empresa_titular", "banco")
        .order_by("banco__nome", "agencia", "numero_conta", "id")
    )
    ultima_data = saldos_qs.aggregate(data_max=Max("data")).get("data_max")

    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "saldos_limites_tabulator": build_saldos_limites_tabulator(saldos_qs, empresa.id),
        "empresas_titulares_opcoes": [
            {
                "id": item.id,
                "codigo": item.codigo,
                "nome": item.nome,
                "label": f"{item.codigo} - {item.nome}",
            }
            for item in empresas_titulares_qs
        ],
        "contas_bancarias_opcoes": [
            {
                "id": conta.id,
                "empresa_titular_id": conta.empresa_titular_id,
                "label": f"{conta.agencia} / {conta.numero_conta}",
                "banco": conta.banco.nome if conta.banco_id else "",
                "titular_label": f"{conta.empresa_titular.codigo} - {conta.empresa_titular.nome}",
            }
            for conta in contas_bancarias_qs
        ],
        "tipos_movimentacao_opcoes": [
            {"value": codigo, "label": nome}
            for codigo, nome in SaldoLimite.TIPO_MOVIMENTACAO_CHOICES
        ],
        "hoje_iso": timezone.localdate().isoformat(),
        "ultima_data_iso": ultima_data.isoformat() if ultima_data else "",
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def criar_saldo_limite_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Saldos e Limites")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    erro = criar_saldo_limite_por_dados(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    item = (
        SaldoLimite.objects.filter(
            empresa=empresa,
            data=request.POST.get("data"),
            empresa_titular_id=request.POST.get("empresa_titular_id"),
            conta_bancaria_id=request.POST.get("conta_bancaria_id"),
            tipo_movimentacao=request.POST.get("tipo_movimentacao"),
        )
        .select_related("empresa_titular", "conta_bancaria", "conta_bancaria__banco")
        .order_by("-id")
        .first()
    )
    if item is None:
        item = (
            SaldoLimite.objects.filter(empresa=empresa)
            .select_related("empresa_titular", "conta_bancaria", "conta_bancaria__banco")
            .order_by("-id")
            .first()
        )

    if _is_ajax_request(request):
        if item is None:
            return JsonResponse(
                {"ok": False, "message": "Registro criado, mas nao foi possivel recarregar os dados."},
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_saldo_limite(item, empresa.id),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("saldos_e_limites", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_saldo_limite_modulo(request, empresa_id, saldo_limite_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Saldos e Limites")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    item = SaldoLimite.objects.filter(id=saldo_limite_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    erro = atualizar_saldo_limite_por_dados(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    item = (
        SaldoLimite.objects.filter(id=item.id, empresa=empresa)
        .select_related("empresa_titular", "conta_bancaria", "conta_bancaria__banco")
        .first()
    )
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_saldo_limite(item, empresa.id) if item else None,
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("saldos_e_limites", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_saldo_limite_modulo(request, empresa_id, saldo_limite_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Saldos e Limites")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    item = SaldoLimite.objects.filter(id=saldo_limite_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    erro = excluir_saldo_limite_por_dados(item, empresa)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("saldos_e_limites", empresa_id=empresa.id)

    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "message": "Registro excluido com sucesso.", "id": saldo_limite_id})

    messages.success(request, "Registro excluido com sucesso.")
    return redirect("saldos_e_limites", empresa_id=empresa.id)


@login_required(login_url="entrar")
def contratos_redes(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contratos Redes")
    if not autorizado:
        return redirect("index")

    contratos_qs = (
        ContratoRede.objects.filter(empresa=empresa)
        .select_related("parceiro")
        .order_by("-data_inicio", "-id")
    )
    parceiros_qs = Parceiro.objects.filter(empresa=empresa).order_by("codigo", "nome")
    contexto = {
        "empresa": empresa,
        "parceiros": parceiros_qs,
        "parceiros_js": list(parceiros_qs.values("id", "codigo", "nome")),
        "contratos_redes_tabulator": build_contratos_redes_tabulator(contratos_qs, empresa.id),
    }
    return render(request, "financeiro/contratos_redes.html", contexto)


@login_required(login_url="entrar")
def mascara_contrato_rede(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contratos Redes")
    if not autorizado:
        return redirect("index")

    contratos_qs = (
        ContratoRede.objects.filter(empresa=empresa)
        .select_related("parceiro")
        .order_by("numero_contrato", "id")
    )
    contratos_mascara_js = [
        {
            "id": contrato.id,
            "numero_contrato": contrato.numero_contrato or "",
            "data_inicio_iso": contrato.data_inicio.strftime("%Y-%m-%d") if contrato.data_inicio else "",
            "data_encerramento_iso": contrato.data_encerramento.strftime("%Y-%m-%d") if contrato.data_encerramento else "",
            "status_contrato": contrato.status_contrato or "Ativo",
            "parceiro_descricao": (
                f"{contrato.parceiro.codigo} - {contrato.parceiro.nome}"
                if contrato.parceiro
                else "Sem parceiro"
            ),
            "descricao_acordos": contrato.descricao_acordos or "",
            "valor_acordo": float(contrato.valor_acordo or 0),
        }
        for contrato in contratos_qs
    ]
    contexto = {
        "empresa": empresa,
        "numero_contrato_prefill": (request.GET.get("numero_contrato") or "").strip(),
        "contratos_mascara_js": contratos_mascara_js,
    }
    return render(request, "financeiro/contratos_redes_mascara.html", contexto)


@login_required(login_url="entrar")
def criar_contrato_rede_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contratos Redes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contratos_redes", empresa_id=empresa.id)

    erro = criar_contrato_rede_por_post(empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("contratos_redes", empresa_id=empresa.id)
    messages.success(request, "Contrato de rede criado com sucesso.")
    return redirect("contratos_redes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_contrato_rede_modulo(request, empresa_id, contrato_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contratos Redes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contratos_redes", empresa_id=empresa.id)

    contrato = ContratoRede.objects.filter(id=contrato_id, empresa=empresa).first()
    if not contrato:
        messages.error(request, "Contrato de rede nao encontrado.")
        return redirect("contratos_redes", empresa_id=empresa.id)

    erro = atualizar_contrato_rede_por_post(contrato, empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("contratos_redes", empresa_id=empresa.id)
    messages.success(request, "Contrato de rede atualizado com sucesso.")
    return redirect("contratos_redes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_contrato_rede_modulo(request, empresa_id, contrato_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contratos Redes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("contratos_redes", empresa_id=empresa.id)

    contrato = ContratoRede.objects.filter(id=contrato_id, empresa=empresa).first()
    if not contrato:
        messages.error(request, "Contrato de rede nao encontrado.")
        return redirect("contratos_redes", empresa_id=empresa.id)

    contrato.excluir_contrato_rede()
    messages.success(request, "Contrato de rede excluido com sucesso.")
    return redirect("contratos_redes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def titulos(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")

    titulos_qs = Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo")
    titulos_tabulator = build_titulos_tabulator(titulos_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "titulos": titulos_qs,
        "titulos_tabulator": titulos_tabulator,
    }
    return render(request, "financeiro/titulos.html", contexto)


@login_required(login_url="entrar")
def criar_titulo_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    erro = criar_titulo_por_dados(empresa, request.POST.get("tipo_titulo_codigo"), request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("titulos", empresa_id=empresa.id)
    messages.success(request, "Titulo criado com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_titulo_modulo(request, empresa_id, titulo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    titulo = Titulo.objects.filter(id=titulo_id, empresa=empresa).first()
    if not titulo:
        messages.error(request, "Titulo nao encontrado.")
        return redirect("titulos", empresa_id=empresa.id)

    erro = atualizar_titulo_por_dados(titulo, request.POST.get("tipo_titulo_codigo"), request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("titulos", empresa_id=empresa.id)
    messages.success(request, "Titulo atualizado com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_titulo_modulo(request, empresa_id, titulo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    titulo = Titulo.objects.filter(id=titulo_id, empresa=empresa).first()
    if not titulo:
        messages.error(request, "Titulo nao encontrado.")
        return redirect("titulos", empresa_id=empresa.id)
    titulo.excluir_titulo()
    messages.success(request, "Titulo excluido com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def naturezas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")

    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    naturezas_tabulator = build_naturezas_tabulator(naturezas_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "naturezas": naturezas_qs,
        "naturezas_tabulator": naturezas_tabulator,
    }
    return render(request, "financeiro/naturezas.html", contexto)


@login_required(login_url="entrar")
def criar_natureza_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    erro = criar_natureza_por_dados(empresa, request.POST.get("codigo"), request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("naturezas", empresa_id=empresa.id)
    messages.success(request, "Natureza criada com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_natureza_modulo(request, empresa_id, natureza_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    natureza = Natureza.objects.filter(id=natureza_id, empresa=empresa).first()
    if not natureza:
        messages.error(request, "Natureza nao encontrada.")
        return redirect("naturezas", empresa_id=empresa.id)

    erro = atualizar_natureza_por_dados(natureza, request.POST.get("codigo"), request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("naturezas", empresa_id=empresa.id)
    messages.success(request, "Natureza atualizada com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_natureza_modulo(request, empresa_id, natureza_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    natureza = Natureza.objects.filter(id=natureza_id, empresa=empresa).first()
    if not natureza:
        messages.error(request, "Natureza nao encontrada.")
        return redirect("naturezas", empresa_id=empresa.id)
    natureza.excluir_natureza()
    messages.success(request, "Natureza excluida com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def operacoes(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")

    operacoes_qs = Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo")
    operacoes_tabulator = build_operacoes_tabulator(operacoes_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "operacoes": operacoes_qs,
        "operacoes_tabulator": operacoes_tabulator,
    }
    return render(request, "financeiro/operacoes.html", contexto)


@login_required(login_url="entrar")
def criar_operacao_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    erro = criar_operacao_por_dados(
        empresa,
        request.POST.get("tipo_operacao_codigo"),
        request.POST.get("descricao_receita_despesa"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("operacoes", empresa_id=empresa.id)
    messages.success(request, "Operacao criada com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_operacao_modulo(request, empresa_id, operacao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    operacao = Operacao.objects.filter(id=operacao_id, empresa=empresa).first()
    if not operacao:
        messages.error(request, "Operacao nao encontrada.")
        return redirect("operacoes", empresa_id=empresa.id)

    erro = atualizar_operacao_por_dados(
        operacao,
        request.POST.get("tipo_operacao_codigo"),
        request.POST.get("descricao_receita_despesa"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("operacoes", empresa_id=empresa.id)
    messages.success(request, "Operacao atualizada com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_operacao_modulo(request, empresa_id, operacao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    operacao = Operacao.objects.filter(id=operacao_id, empresa=empresa).first()
    if not operacao:
        messages.error(request, "Operacao nao encontrada.")
        return redirect("operacoes", empresa_id=empresa.id)
    operacao.excluir_operacao()
    messages.success(request, "Operacao excluida com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def centros_resultado(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")

    centros_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")
    centros_tabulator = build_centros_resultado_tabulator(centros_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "centros_resultado": centros_qs,
        "centros_resultado_tabulator": centros_tabulator,
    }
    return render(request, "financeiro/centros_resultado.html", contexto)


@login_required(login_url="entrar")
def criar_centro_resultado_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    erro = criar_centro_resultado_por_dados(empresa, request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado criado com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_centro_resultado_modulo(request, empresa_id, centro_resultado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    centro_resultado = CentroResultado.objects.filter(id=centro_resultado_id, empresa=empresa).first()
    if not centro_resultado:
        messages.error(request, "Centro resultado nao encontrado.")
        return redirect("centros_resultado", empresa_id=empresa.id)

    erro = atualizar_centro_resultado_por_dados(centro_resultado, request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado atualizado com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_centro_resultado_modulo(request, empresa_id, centro_resultado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    centro_resultado = CentroResultado.objects.filter(id=centro_resultado_id, empresa=empresa).first()
    if not centro_resultado:
        messages.error(request, "Centro resultado nao encontrado.")
        return redirect("centros_resultado", empresa_id=empresa.id)
    try:
        centro_resultado.excluir_centro_resultado()
    except ProtectedError:
        messages.error(
            request,
            "Nao e possivel excluir este centro de resultado porque ele esta vinculado a Orcamentos Realizados.",
        )
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado excluido com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_dre_modulo(request, empresa_id, dre_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "DRE")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("dre", empresa_id=empresa.id)

    item = DRE.objects.filter(id=dre_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("dre", empresa_id=empresa.id)

    erro = atualizar_dre_por_post(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("dre", empresa_id=empresa.id)

    item = DRE.objects.filter(id=item.id, empresa=empresa).first()
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_dre(item, empresa.id) if item else None,
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("dre", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_dfc_modulo(request, empresa_id, dfc_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "DFC")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "dfc")
    if bloqueio:
        return bloqueio

    dfc_item = FluxoDeCaixaDFC.objects.filter(id=dfc_id, empresa=empresa).first()
    if not dfc_item:
        messages.error(request, "Registro DFC nao encontrado.")
        return redirect("dfc", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_dfc_por_post(dfc_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_dfc_modulo", empresa_id=empresa.id, dfc_id=dfc_item.id)
        messages.success(request, "Registro DFC atualizado com sucesso.")
        return redirect("dfc", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "dfc_item": dfc_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "financeiro/dfc_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_dfc_modulo(request, empresa_id, dfc_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "DFC")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("dfc", empresa_id=empresa.id)

    dfc_item = FluxoDeCaixaDFC.objects.filter(id=dfc_id, empresa=empresa).first()
    if not dfc_item:
        messages.error(request, "Registro DFC nao encontrado.")
        return redirect("dfc", empresa_id=empresa.id)
    erro = excluir_dfc_por_dados(dfc_item, empresa)
    if erro:
        messages.error(request, erro)
        return redirect("dfc", empresa_id=empresa.id)
    messages.success(request, "Registro DFC excluido com sucesso.")
    return redirect("dfc", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_adiantamento_modulo(request, empresa_id, adiantamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Adiantamentos")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "adiantamentos")
    if bloqueio:
        return bloqueio

    adiantamento_item = Adiantamento.objects.filter(id=adiantamento_id, empresa=empresa).first()
    if not adiantamento_item:
        messages.error(request, "Registro de Adiantamentos nao encontrado.")
        return redirect("adiantamentos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_adiantamento_por_post(adiantamento_item, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_adiantamento_modulo", empresa_id=empresa.id, adiantamento_id=adiantamento_item.id)
        messages.success(request, "Registro de Adiantamentos atualizado com sucesso.")
        return redirect("adiantamentos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "adiantamento_item": adiantamento_item,
    }
    return render(request, "financeiro/adiantamentos_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_adiantamento_modulo(request, empresa_id, adiantamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Adiantamentos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("adiantamentos", empresa_id=empresa.id)

    adiantamento_item = Adiantamento.objects.filter(id=adiantamento_id, empresa=empresa).first()
    if not adiantamento_item:
        messages.error(request, "Registro de Adiantamentos nao encontrado.")
        return redirect("adiantamentos", empresa_id=empresa.id)
    adiantamento_item.excluir_adiantamento()
    messages.success(request, "Registro de Adiantamentos excluido com sucesso.")
    return redirect("adiantamentos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_contas_a_receber_modulo(request, empresa_id, conta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas a Receber")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "contas_a_receber")
    if bloqueio:
        return bloqueio

    conta_item = ContasAReceber.objects.filter(id=conta_id, empresa=empresa).first()
    if not conta_item:
        messages.error(request, "Registro de Contas a Receber nao encontrado.")
        return redirect("contas_a_receber", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_contas_a_receber_por_post(conta_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_contas_a_receber_modulo", empresa_id=empresa.id, conta_id=conta_item.id)
        messages.success(request, "Registro de Contas a Receber atualizado com sucesso.")
        return redirect("contas_a_receber", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "conta_item": conta_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "financeiro/contas_a_receber_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_contas_a_receber_modulo(request, empresa_id, conta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas a Receber")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("contas_a_receber", empresa_id=empresa.id)

    conta_item = ContasAReceber.objects.filter(id=conta_id, empresa=empresa).first()
    if not conta_item:
        messages.error(request, "Registro de Contas a Receber nao encontrado.")
        return redirect("contas_a_receber", empresa_id=empresa.id)
    conta_item.excluir_conta_a_receber()
    messages.success(request, "Registro de Contas a Receber excluido com sucesso.")
    return redirect("contas_a_receber", empresa_id=empresa.id)

