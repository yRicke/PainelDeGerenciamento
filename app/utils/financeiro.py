import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Case, DecimalField, F, IntegerField, Max, Min, Q, Sum, Value, When
from django.db.models.functions import Coalesce


def _parse_data_tabulator(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _fmt_date_br(valor):
    if not valor:
        return ""
    return valor.strftime("%d/%m/%Y")


def _parse_decimal_tabulator(valor):
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extrair_valores_filtro(valor_bruto):
    if isinstance(valor_bruto, (list, tuple, set)):
        return [str(v).strip() for v in valor_bruto if str(v).strip()]
    texto = str(valor_bruto or "").strip()
    if not texto:
        return []
    if "||" in texto:
        return [item.strip() for item in texto.split("||") if item.strip()]
    return [texto]


def _intervalo_para_faixa_dias(intervalo_texto):
    texto = str(intervalo_texto or "").strip().lower()
    if not texto:
        return None, None
    if texto.startswith("+"):
        limite = "".join(ch for ch in texto if ch.isdigit())
        if not limite:
            return None, None
        return int(limite), None
    match = re.search(r"(\d+)\s*-\s*(\d+)", texto)
    if not match:
        return None, None
    inicio, fim = int(match.group(1)), int(match.group(2))
    if inicio > fim:
        inicio, fim = fim, inicio
    return inicio, fim


def _q_intervalo_contas(hoje, valor_intervalo):
    inicio, fim = _intervalo_para_faixa_dias(valor_intervalo)
    if inicio is None:
        return Q()

    if fim is None:
        return (
            Q(data_vencimento__lte=hoje - timedelta(days=inicio))
            | Q(data_vencimento__gte=hoje + timedelta(days=inicio))
        )

    return (
        Q(
            data_vencimento__gte=hoje - timedelta(days=fim),
            data_vencimento__lte=hoje - timedelta(days=inicio),
        )
        | Q(
            data_vencimento__gte=hoje + timedelta(days=inicio),
            data_vencimento__lte=hoje + timedelta(days=fim),
        )
    )


def _filtrar_contas_a_receber_por_intervalo(qs, valor_intervalo):
    hoje = datetime.now().date()
    q_intervalo = _q_intervalo_contas(hoje, valor_intervalo)
    if not q_intervalo:
        return qs
    return qs.filter(q_intervalo)


def _datas_posicao_contas(qs):
    datas = list(
        qs.exclude(data_arquivo__isnull=True)
        .order_by("-data_arquivo")
        .values_list("data_arquivo", flat=True)
        .distinct()[:2]
    )
    ultima = datas[0] if len(datas) >= 1 else None
    penultima = datas[1] if len(datas) >= 2 else None
    return ultima, penultima


def _aplicar_filtros_contas_a_receber(qs, filtros):
    hoje = datetime.now().date()
    for filtro in filtros:
        campo = str(filtro.get("field") or "").strip()
        tipo = str(filtro.get("type") or "").strip().lower()
        valores = _extrair_valores_filtro(filtro.get("value"))
        if not campo or not valores:
            continue

        if campo == "status":
            q_status = Q()
            for valor in valores:
                valor_lower = valor.lower()
                if "vencido" in valor_lower:
                    q_status |= Q(data_vencimento__lt=hoje)
                elif "vencer" in valor_lower:
                    q_status |= Q(data_vencimento__gte=hoje)
            if q_status:
                qs = qs.filter(q_status)
            continue

        if campo == "intervalo":
            q_intervalos = Q()
            for valor in valores:
                q_intervalo = _q_intervalo_contas(hoje, valor)
                if q_intervalo:
                    q_intervalos |= q_intervalo
            if q_intervalos:
                qs = qs.filter(q_intervalos)
            continue

        if campo == "dias_diferenca":
            q_dias = Q()
            for valor in valores:
                if re.fullmatch(r"-?\d+", valor):
                    q_dias |= Q(data_vencimento=hoje - timedelta(days=int(valor)))
            if q_dias:
                qs = qs.filter(q_dias)
            continue

        if campo in {"data_negociacao", "data_vencimento", "data_arquivo"}:
            q_datas = Q()
            for valor in valores:
                data = _parse_data_tabulator(valor)
                if data:
                    q_datas |= Q(**{campo: data})
                elif valor.isdigit() and len(valor) == 4:
                    q_datas |= Q(**{f"{campo}__year": int(valor)})
            if q_datas:
                qs = qs.filter(q_datas)
            continue

        if campo == "data_arquivo_iso":
            q_data_arquivo = Q()
            for valor in valores:
                data_iso = _parse_data_tabulator(valor)
                if data_iso:
                    q_data_arquivo |= Q(data_arquivo=data_iso)
            if q_data_arquivo:
                qs = qs.filter(q_data_arquivo)
            continue

        if campo in {"valor_desdobramento", "valor_liquido"}:
            q_valores = Q()
            for valor in valores:
                valor_decimal = _parse_decimal_tabulator(valor)
                if valor_decimal is not None:
                    q_valores |= Q(**{campo: valor_decimal})
            if q_valores:
                qs = qs.filter(q_valores)
            continue

        if campo == "posicao_contagem":
            ultima_data, penultima_data = _datas_posicao_contas(qs)
            q_posicao = Q()
            for valor in valores:
                token = str(valor or "").strip().lower()
                if token == "ultima_posicao" and ultima_data:
                    q_posicao |= Q(data_arquivo=ultima_data)
                elif token == "penultima_posicao" and penultima_data:
                    q_posicao |= Q(data_arquivo=penultima_data)
                elif token == "anteriores_posicao":
                    q_anteriores = Q()
                    if ultima_data:
                        q_anteriores &= ~Q(data_arquivo=ultima_data)
                    if penultima_data:
                        q_anteriores &= ~Q(data_arquivo=penultima_data)
                    q_posicao |= q_anteriores
            if q_posicao:
                qs = qs.filter(q_posicao)
            continue

        filtros_texto = {
            "nome_fantasia_empresa": "nome_fantasia_empresa__icontains",
            "parceiro_nome": "parceiro__nome__icontains",
            "numero_nota": "numero_nota__icontains",
            "titulo_descricao": "titulo__descricao__icontains",
            "natureza_descricao": "natureza__descricao__icontains",
            "centro_resultado_descricao": "centro_resultado__descricao__icontains",
            "vendedor": "vendedor__icontains",
            "operacao_descricao": "operacao__descricao_receita_despesa__icontains",
        }
        lookup = filtros_texto.get(campo)
        if lookup:
            q_texto = Q()
            if tipo == "in":
                lookup_exato = lookup.replace("__icontains", "")
                for valor in valores:
                    q_texto |= Q(**{lookup_exato: valor})
            else:
                for valor in valores:
                    q_texto |= Q(**{lookup: valor})
            if q_texto:
                qs = qs.filter(q_texto)

    return qs


def _ordenar_contas_a_receber(qs, sorters):
    mapeamento = {
        "id": "id",
        "data_negociacao": "data_negociacao",
        "data_vencimento": "data_vencimento",
        "data_arquivo": "data_arquivo",
        "nome_fantasia_empresa": "nome_fantasia_empresa",
        "parceiro_nome": "parceiro__nome",
        "numero_nota": "numero_nota",
        "valor_desdobramento": "valor_desdobramento",
        "valor_liquido": "valor_liquido",
        "titulo_descricao": "titulo__descricao",
        "natureza_descricao": "natureza__descricao",
        "centro_resultado_descricao": "centro_resultado__descricao",
        "vendedor": "vendedor",
        "operacao_descricao": "operacao__descricao_receita_despesa",
    }

    hoje = datetime.now().date()
    ordenacoes = []
    ordenar_por_status = False
    ordenar_por_intervalo = False
    intervalos_ordenacao = [
        "0-5 (CML)",
        "6-20 (FIN)",
        "21-30 (POL)",
        "31-60 (POL)",
        "61-90 (POL)",
        "91-120 (JUR1)",
        "121-180 (JUR1)",
        "+180 (JUR2)",
    ]

    for sorter in sorters:
        campo = str(sorter.get("field") or sorter.get("column") or "").strip()
        direcao = str(sorter.get("dir") or "asc").strip().lower()
        if direcao not in {"asc", "desc"}:
            direcao = "asc"

        if campo == "dias_diferenca":
            # dias_diferenca = hoje - data_vencimento:
            # ordem crescente de dias equivale a data_vencimento decrescente.
            direcao_data = "desc" if direcao == "asc" else "asc"
            prefixo = "-" if direcao_data == "desc" else ""
            ordenacoes.append(f"{prefixo}data_vencimento")
            continue

        if campo == "status":
            ordenar_por_status = True
            prefixo = "-" if direcao == "desc" else ""
            ordenacoes.append(f"{prefixo}status_ordem_sort")
            continue

        if campo == "intervalo":
            ordenar_por_intervalo = True
            prefixo = "-" if direcao == "desc" else ""
            ordenacoes.append(f"{prefixo}intervalo_ordem_sort")
            continue

        order_field = mapeamento.get(campo)
        if not order_field:
            continue
        prefixo = "-" if direcao == "desc" else ""
        ordenacoes.append(f"{prefixo}{order_field}")

    if ordenar_por_status:
        qs = qs.annotate(
            status_ordem_sort=Case(
                When(data_vencimento__gte=hoje, then=Value(0)),  # A Vencer
                When(data_vencimento__lt=hoje, then=Value(1)),   # Vencido
                default=Value(2),
                output_field=IntegerField(),
            )
        )

    if ordenar_por_intervalo:
        casos_intervalo = [
            When(_q_intervalo_contas(hoje, faixa), then=Value(indice))
            for indice, faixa in enumerate(intervalos_ordenacao, start=1)
        ]
        qs = qs.annotate(
            intervalo_ordem_sort=Case(
                *casos_intervalo,
                default=Value(9),
                output_field=IntegerField(),
            )
        )

    if not ordenacoes:
        ordenacoes = ["-id"]
    elif not any(item.lstrip("-") == "id" for item in ordenacoes):
        ordenacoes.append("-id")

    return qs.order_by(*ordenacoes)


def _resumo_contas_a_receber(qs, total_registros):
    def _somar_valor_assinado(qs_ref, campo_valor):
        agregado_local = qs_ref.aggregate(
            total=Coalesce(
                Sum(
                    Case(
                        When(
                            operacao__descricao_receita_despesa__icontains="despesa",
                            then=-F(campo_valor),
                        ),
                        default=F(campo_valor),
                        output_field=DecimalField(max_digits=18, decimal_places=2),
                    )
                ),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=18, decimal_places=2)),
            ),
        )
        return agregado_local.get("total") or Decimal("0.00")

    datas_referencia = qs.exclude(data_arquivo__isnull=True).aggregate(
        data_inicial=Min("data_arquivo"),
        data_final=Max("data_arquivo"),
    )
    campo_referencia = "data_arquivo"
    data_inicial = datas_referencia.get("data_inicial")
    data_final = datas_referencia.get("data_final")

    if data_inicial is None or data_final is None:
        datas_negociacao = qs.exclude(data_negociacao__isnull=True).aggregate(
            data_inicial=Min("data_negociacao"),
            data_final=Max("data_negociacao"),
        )
        if data_inicial is None:
            data_inicial = datas_negociacao.get("data_inicial")
        if data_final is None:
            data_final = datas_negociacao.get("data_final")
        campo_referencia = "data_negociacao"

    qs_data_final = qs.none()
    if data_final:
        qs_data_final = qs.filter(**{campo_referencia: data_final})

    qs_data_inicial = qs.none()
    if data_inicial:
        qs_data_inicial = qs.filter(**{campo_referencia: data_inicial})

    valor_faturado_total = _somar_valor_assinado(qs, "valor_liquido")
    valor_data_mais_recente = _somar_valor_assinado(qs_data_final, "valor_liquido")
    faturamento_data_mais_recente = _somar_valor_assinado(qs_data_final, "valor_desdobramento")
    valor_data_inicial = _somar_valor_assinado(qs_data_inicial, "valor_liquido")
    valor_data_final = valor_data_mais_recente
    quantidade_data_mais_recente = qs_data_final.count() if data_final else 0
    diferenca_periodo = valor_data_final - valor_data_inicial

    hoje = datetime.now().date()
    valor_inadimplente = _somar_valor_assinado(qs_data_final.filter(data_vencimento__lt=hoje), "valor_liquido")
    base_inadimplencia = abs(valor_data_mais_recente)
    inadimplencia_percentual = (
        (abs(valor_inadimplente) / base_inadimplencia * Decimal("100.00"))
        if base_inadimplencia > 0
        else Decimal("0.00")
    )

    return {
        "quantidade": int(total_registros or 0),
        "valor_faturado": float(valor_faturado_total),
        "data_mais_recente": data_final.isoformat() if data_final else "",
        "quantidade_data_mais_recente": int(quantidade_data_mais_recente),
        "valor_data_mais_recente": float(valor_data_mais_recente),
        "faturamento_data_mais_recente": float(faturamento_data_mais_recente),
        "inadimplencia_percentual": float(inadimplencia_percentual),
        "data_inicial": data_inicial.isoformat() if data_inicial else "",
        "valor_data_inicial": float(valor_data_inicial),
        "data_final": data_final.isoformat() if data_final else "",
        "valor_data_final": float(valor_data_final),
        "diferenca_periodo": float(diferenca_periodo),
    }


def _resumo_dashboard_faturamento_contas_a_receber(
    qs_contas,
    qs_faturamento,
    data_inicio=None,
    data_fim=None,
    empresa_filtro="",
):
    def _somar_decimal(qs_ref, campo):
        agregado_local = qs_ref.aggregate(
            total=Coalesce(
                Sum(campo),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=18, decimal_places=2)),
            ),
        )
        return agregado_local.get("total") or Decimal("0.00")

    empresa_normalizada = str(empresa_filtro or "").strip()
    aplicar_filtro_empresa = bool(empresa_normalizada and empresa_normalizada != "__all__")
    if aplicar_filtro_empresa:
        qs_contas = qs_contas.filter(nome_fantasia_empresa__iexact=empresa_normalizada)
        qs_faturamento = qs_faturamento.filter(nome_empresa__iendswith=empresa_normalizada)
    else:
        empresa_normalizada = ""

    datas_faturamento = qs_faturamento.exclude(data_faturamento__isnull=True).aggregate(
        data_inicio=Min("data_faturamento"),
        data_fim=Max("data_faturamento"),
    )
    if data_inicio is None:
        data_inicio = datas_faturamento.get("data_inicio")
    if data_fim is None:
        data_fim = datas_faturamento.get("data_fim")
    if data_inicio and data_fim and data_inicio > data_fim:
        data_inicio, data_fim = data_fim, data_inicio

    qs_faturamento_periodo = qs_faturamento
    if data_inicio:
        qs_faturamento_periodo = qs_faturamento_periodo.filter(data_faturamento__gte=data_inicio)
    if data_fim:
        qs_faturamento_periodo = qs_faturamento_periodo.filter(data_faturamento__lte=data_fim)

    faturamento_total = _somar_decimal(qs_faturamento_periodo, "valor_nota_unico")

    # Regra BI: inadimplencia considera apenas a ultima posicao de contas a receber
    # e dentro dela filtra pelos titulos vencidos no periodo selecionado.
    data_snapshot = (
        qs_contas.exclude(data_arquivo__isnull=True)
        .aggregate(data_snapshot=Max("data_arquivo"))
        .get("data_snapshot")
    )

    valor_inadimplente = Decimal("0.00")
    if data_snapshot:
        hoje = datetime.now().date()
        qs_inadimplencia = qs_contas.filter(
            data_arquivo=data_snapshot,
            data_vencimento__lt=hoje,
        )
        if data_inicio:
            qs_inadimplencia = qs_inadimplencia.filter(data_vencimento__gte=data_inicio)
        if data_fim:
            qs_inadimplencia = qs_inadimplencia.filter(data_vencimento__lte=data_fim)
        valor_inadimplente = _somar_decimal(qs_inadimplencia, "valor_liquido")

    base_inadimplencia = abs(faturamento_total)
    inadimplencia_percentual = (
        (abs(valor_inadimplente) / base_inadimplencia * Decimal("100.00"))
        if base_inadimplencia > 0
        else Decimal("0.00")
    )

    return {
        "periodo_inicio": data_inicio.isoformat() if data_inicio else "",
        "periodo_fim": data_fim.isoformat() if data_fim else "",
        "empresa": empresa_normalizada,
        "faturamento_total": float(faturamento_total),
        "valor_inadimplente": float(valor_inadimplente),
        "inadimplencia_percentual": float(inadimplencia_percentual),
        "data_snapshot": data_snapshot.isoformat() if data_snapshot else "",
    }


def _filtros_sem_campo(filtros, campo):
    alvo = str(campo or "").strip()
    if not alvo:
        return list(filtros or [])
    return [
        filtro for filtro in (filtros or [])
        if str((filtro or {}).get("field") or "").strip() != alvo
    ]


def _opcoes_texto_distintas_contas(qs, campo_lookup):
    valores = (
        qs.exclude(**{f"{campo_lookup}__isnull": True})
        .exclude(**{campo_lookup: ""})
        .order_by(campo_lookup)
        .values_list(campo_lookup, flat=True)
        .distinct()
    )
    return [
        {"value": str(valor), "label": str(valor)}
        for valor in valores
        if str(valor or "").strip()
    ]


def _opcoes_data_arquivo_contas(qs):
    datas = (
        qs.exclude(data_arquivo__isnull=True)
        .order_by("-data_arquivo")
        .values_list("data_arquivo", flat=True)
        .distinct()
    )
    return [
        {"value": data.strftime("%Y-%m-%d"), "label": _fmt_date_br(data)}
        for data in datas
        if data
    ]


def _opcoes_externas_contas_a_receber(base_qs, filtros):
    filtros_status = _filtros_sem_campo(filtros, "status")
    filtros_intervalo = _filtros_sem_campo(filtros, "intervalo")
    filtros_data_arquivo = _filtros_sem_campo(filtros, "data_arquivo_iso")
    filtros_titulo = _filtros_sem_campo(filtros, "titulo_descricao")
    filtros_nome = _filtros_sem_campo(filtros, "nome_fantasia_empresa")
    filtros_natureza = _filtros_sem_campo(filtros, "natureza_descricao")
    filtros_posicao = _filtros_sem_campo(filtros, "posicao_contagem")

    qs_status = _aplicar_filtros_contas_a_receber(base_qs, filtros_status)
    qs_intervalo = _aplicar_filtros_contas_a_receber(base_qs, filtros_intervalo)
    qs_data_arquivo = _aplicar_filtros_contas_a_receber(base_qs, filtros_data_arquivo)
    qs_titulo = _aplicar_filtros_contas_a_receber(base_qs, filtros_titulo)
    qs_nome = _aplicar_filtros_contas_a_receber(base_qs, filtros_nome)
    qs_natureza = _aplicar_filtros_contas_a_receber(base_qs, filtros_natureza)
    qs_posicao = _aplicar_filtros_contas_a_receber(base_qs, filtros_posicao)

    hoje = datetime.now().date()
    opcoes_status = []
    if qs_status.filter(data_vencimento__lt=hoje).exists():
        opcoes_status.append({"value": "Vencido", "label": "Vencido"})
    if qs_status.filter(data_vencimento__gte=hoje).exists():
        opcoes_status.append({"value": "A Vencer", "label": "A Vencer"})

    opcoes_intervalo = []
    intervalos = [
        "0-5 (CML)",
        "6-20 (FIN)",
        "21-30 (POL)",
        "31-60 (POL)",
        "61-90 (POL)",
        "91-120 (JUR1)",
        "121-180 (JUR1)",
        "+180 (JUR2)",
    ]
    for item in intervalos:
        if _filtrar_contas_a_receber_por_intervalo(qs_intervalo, item).exists():
            opcoes_intervalo.append({"value": item, "label": item})

    ultima_data, penultima_data = _datas_posicao_contas(qs_posicao)
    opcoes_posicao = []
    if ultima_data:
        opcoes_posicao.append({"value": "ultima_posicao", "label": "Ultima Posicao"})
    if penultima_data:
        opcoes_posicao.append({"value": "penultima_posicao", "label": "Penultima Posicao"})

    q_anteriores = Q()
    if ultima_data:
        q_anteriores &= ~Q(data_arquivo=ultima_data)
    if penultima_data:
        q_anteriores &= ~Q(data_arquivo=penultima_data)
    if qs_posicao.filter(q_anteriores).exists():
        opcoes_posicao.append({"value": "anteriores_posicao", "label": "Anteriores"})

    return {
        "status": opcoes_status,
        "intervalo": opcoes_intervalo,
        "data_arquivo_iso": _opcoes_data_arquivo_contas(qs_data_arquivo),
        "titulo_descricao": _opcoes_texto_distintas_contas(qs_titulo, "titulo__descricao"),
        "nome_fantasia_empresa": _opcoes_texto_distintas_contas(qs_nome, "nome_fantasia_empresa"),
        "natureza_descricao": _opcoes_texto_distintas_contas(qs_natureza, "natureza__descricao"),
        "posicao_contagem": opcoes_posicao,
    }

