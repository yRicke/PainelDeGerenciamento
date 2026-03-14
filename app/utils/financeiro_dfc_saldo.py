from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone

from ..models import DFCSaldoManual

_DFC_SALDO_DIA_SEMANA_ABREV = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
_DFC_SALDO_CHAVE_TOTAL_ANTERIOR = "total_anterior"
_DFC_SALDO_CHAVE_TOTAL_PERIODO = "total_periodo"
_DFC_SALDO_CHAVE_TOTAL_POSTERIOR = "total_posterior"
_DFC_SALDO_MANUAL_TIPOS = {
    "previsao_recebivel": DFCSaldoManual.TIPO_PREVISAO_RECEBIVEL,
    "outras_consideracoes_receita": DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_RECEITA,
    "adiantamentos_previsao": DFCSaldoManual.TIPO_ADIANTAMENTOS_PREVISAO,
    "outras_consideracoes_despesa": DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_DESPESA,
}
_DFC_SALDO_LABEL_SEM_TITULO = "<SEM TIPO DE TITULO>"
_DFC_SALDO_TITULOS_REGRA_DIA_ANTERIOR = {
    "boleto disponivel",
    "cheque a vista",
    "cheque pre datado",
    "cheque pre datado em custodia",
}
_DFC_SALDO_CONTAS_RECEBER_ORDEM_LEGADO = (
    "<SEM TIPO DE TITULO>",
    "ADIANTAMENTO",
    "BOLETO CARTORIO",
    "BOLETO COBRANCA INTERNA",
    "BOLETO DESCONTADO",
    "BOLETO DESPESA",
    "BOLETO DISPONIVEL",
    "BOLETO PROTESTADO",
    "CHEQUE A VISTA",
    "CHEQUE PRE DATADO",
    "CHEQUE PRE DATADO EM CUSTODIA",
    "COBRANCA INTERNA",
    "COBRANCA INTERNO (DESCONTADO)",
    "COMPENSACAO",
    "CONSULTH - COBRANCA EXTERNA",
    "DEBITO AUTOMATICO",
    "DEVOLUCAO DE VENDA",
    "DINHEIRO",
    "JURIDICO 1",
    "JURIDICO 2",
    "NEGATIVADO",
    "NOTA FISCAL DESCONTADA",
    "NOTA FISCAL DISPONIVEL",
    "PAGAMENTO ELETRONICO",
    "PAG-TED",
    "PDD",
)


def _parse_decimal_dfc_saldo_ou_zero(valor):
    texto = str(valor or "").strip()
    if not texto:
        return Decimal("0")

    texto = texto.replace("R$", "").replace(" ", "")
    texto_lower = texto.lower()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1 and "e" not in texto_lower:
        texto = texto.replace(".", "")

    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return Decimal("0")

    try:
        return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0")


def _normalizar_token_texto(valor):
    texto = str(valor or "").strip().lower()
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.split())


def _classificar_tipo_dfc_por_linha(item):
    valor = _parse_decimal_dfc_saldo_ou_zero(item.get("valor_liquido_num"))
    if valor > 0:
        return "receita"
    if valor < 0:
        return "despesa"

    tipo_movimento = _normalizar_token_texto(item.get("tipo_movimento"))
    if "receita" in tipo_movimento:
        return "receita"
    if "despesa" in tipo_movimento:
        return "despesa"

    operacao_descricao = _normalizar_token_texto(item.get("operacao__descricao_receita_despesa"))
    if "receita" in operacao_descricao:
        return "receita"
    if "despesa" in operacao_descricao:
        return "despesa"
    return ""


def _chave_coluna_dia_dfc_saldo(data_ref):
    return f"d_{data_ref.strftime('%Y_%m_%d')}"


def _somar_mapa_por_intervalo(mapa_por_data, *, inicio=None, fim=None):
    total = Decimal("0")
    for data_ref, valor in (mapa_por_data or {}).items():
        if inicio and data_ref < inicio:
            continue
        if fim and data_ref > fim:
            continue
        total += _parse_decimal_dfc_saldo_ou_zero(valor)
    return total


def _calcular_totais_resumo_dfc_saldo(mapa_por_data, *, inicio_periodo, fim_periodo):
    return (
        _somar_mapa_por_intervalo(mapa_por_data, fim=inicio_periodo - timedelta(days=1)),
        _somar_mapa_por_intervalo(mapa_por_data, inicio=inicio_periodo, fim=fim_periodo),
        _somar_mapa_por_intervalo(mapa_por_data, inicio=fim_periodo + timedelta(days=1)),
    )


def _float_ou_none(valor_decimal):
    if valor_decimal is None:
        return None
    return float(_parse_decimal_dfc_saldo_ou_zero(valor_decimal))


def _atualizar_colunas_dia_em_valores_dfc_saldo(valores, datas_periodo, mapa_por_data):
    for data_ref in datas_periodo:
        chave = _chave_coluna_dia_dfc_saldo(data_ref)
        valores[chave] = _float_ou_none((mapa_por_data or {}).get(data_ref, Decimal("0")))


def _aplicar_totais_resumo_em_valores_dfc_saldo(
    valores,
    *,
    total_anterior,
    total_periodo,
    total_posterior,
):
    valores[_DFC_SALDO_CHAVE_TOTAL_ANTERIOR] = _float_ou_none(total_anterior)
    valores[_DFC_SALDO_CHAVE_TOTAL_PERIODO] = _float_ou_none(total_periodo)
    valores[_DFC_SALDO_CHAVE_TOTAL_POSTERIOR] = _float_ou_none(total_posterior)


def _obter_linha_por_chave_dfc_saldo(linhas, key):
    return next((row for row in linhas if row.get("key") == key), None)


def _montar_valores_linha_dfc_saldo(mapa_por_data, datas_periodo, inicio_periodo, fim_periodo):
    mapa = mapa_por_data or {}
    total_anterior, total_periodo, total_posterior = _calcular_totais_resumo_dfc_saldo(
        mapa,
        inicio_periodo=inicio_periodo,
        fim_periodo=fim_periodo,
    )
    valores = {
        _DFC_SALDO_CHAVE_TOTAL_ANTERIOR: _float_ou_none(total_anterior),
        _DFC_SALDO_CHAVE_TOTAL_PERIODO: _float_ou_none(total_periodo),
        _DFC_SALDO_CHAVE_TOTAL_POSTERIOR: _float_ou_none(total_posterior),
    }
    _atualizar_colunas_dia_em_valores_dfc_saldo(valores, datas_periodo, mapa)
    return valores


def _titulo_conta_receber_label_dfc_saldo(item):
    titulo_descricao = str(item.get("titulo__descricao") or "").strip()
    if not titulo_descricao:
        return _DFC_SALDO_LABEL_SEM_TITULO
    return titulo_descricao.upper()


def _titulo_conta_receber_usa_regra_dia_anterior(label):
    return _normalizar_token_texto(label) in _DFC_SALDO_TITULOS_REGRA_DIA_ANTERIOR


def _mapa_dias_receita_por_titulo(mapa_base_por_data, datas_periodo, usar_regra_dia_anterior):
    mapa_base = mapa_base_por_data or {}
    mapa_dias = {}
    if not usar_regra_dia_anterior:
        for data_ref in datas_periodo:
            mapa_dias[data_ref] = _parse_decimal_dfc_saldo_ou_zero(mapa_base.get(data_ref))
        return mapa_dias

    for data_ref in datas_periodo:
        dia_semana = data_ref.weekday()
        if dia_semana >= 5:
            mapa_dias[data_ref] = Decimal("0")
            continue
        if dia_semana == 0:  # segunda-feira considera sexta+sabado+domingo
            data_inicio = data_ref - timedelta(days=3)
            data_fim = data_ref - timedelta(days=1)
        else:
            data_inicio = data_ref - timedelta(days=1)
            data_fim = data_ref - timedelta(days=1)
        mapa_dias[data_ref] = _somar_mapa_por_intervalo(
            mapa_base,
            inicio=data_inicio,
            fim=data_fim,
        )
    return mapa_dias


def _chave_detalhe_conta_receber(label, indice):
    base = _normalizar_token_texto(label)
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    if not base:
        base = "sem_titulo"
    return f"contas_receber_detalhe_{indice}_{base}"


def _aplicar_ajustes_legacy_totais_linha_receita(
    *,
    mapa_base_por_data,
    inicio_periodo,
    fim_periodo,
    ajuste_prev_titulo4=Decimal("0"),
):
    total_anterior, total_periodo, total_posterior = _calcular_totais_resumo_dfc_saldo(
        mapa_base_por_data,
        inicio_periodo=inicio_periodo,
        fim_periodo=fim_periodo,
    )
    ajuste_prev = _parse_decimal_dfc_saldo_ou_zero(ajuste_prev_titulo4)
    ajuste_dia_final = _parse_decimal_dfc_saldo_ou_zero(mapa_base_por_data.get(fim_periodo, Decimal("0"))).copy_abs()
    total_anterior = total_anterior - ajuste_prev
    total_periodo = total_periodo + ajuste_prev - ajuste_dia_final
    total_posterior = total_posterior + ajuste_dia_final
    return total_anterior, total_periodo, total_posterior


def _mapa_dfc_saldos_manuais_por_tipo(empresa):
    resultado = {tipo: {} for tipo in _DFC_SALDO_MANUAL_TIPOS.values()}
    saldos_qs = DFCSaldoManual.objects.filter(empresa=empresa).values("data_referencia", "tipo", "valor")
    for item in saldos_qs:
        tipo = item.get("tipo")
        data_ref = item.get("data_referencia")
        if not tipo or not data_ref:
            continue
        if tipo not in resultado:
            resultado[tipo] = {}
        resultado[tipo][data_ref] = _parse_decimal_dfc_saldo_ou_zero(item.get("valor"))
    return resultado


def _montar_linha_saldo_inicial_e_saldos_dia(
    *,
    datas_periodo,
    mapa_contas_receber,
    mapa_previsao_recebivel,
    mapa_outras_receita,
    mapa_contas_pagar,
    mapa_adiantamentos_previsao,
    mapa_outras_despesa,
    incluir_previsoes=True,
    incluir_outras=True,
):
    saldo_inicial_por_data = {}
    saldo_dia_por_data = {}
    saldo_final_por_data = {}

    for indice, data_ref in enumerate(datas_periodo):
        if indice <= 0:
            saldo_inicial = Decimal("0")
        else:
            dia_anterior = datas_periodo[indice - 1]
            saldo_inicial = saldo_final_por_data.get(dia_anterior, Decimal("0"))
        saldo_inicial_por_data[data_ref] = saldo_inicial

        entradas = _parse_decimal_dfc_saldo_ou_zero(mapa_contas_receber.get(data_ref, Decimal("0")))
        saidas = _parse_decimal_dfc_saldo_ou_zero(mapa_contas_pagar.get(data_ref, Decimal("0")))

        if incluir_previsoes:
            entradas += _parse_decimal_dfc_saldo_ou_zero(mapa_previsao_recebivel.get(data_ref, Decimal("0")))
            saidas += _parse_decimal_dfc_saldo_ou_zero(mapa_adiantamentos_previsao.get(data_ref, Decimal("0")))

        if incluir_outras:
            entradas += _parse_decimal_dfc_saldo_ou_zero(mapa_outras_receita.get(data_ref, Decimal("0")))
            saidas += _parse_decimal_dfc_saldo_ou_zero(mapa_outras_despesa.get(data_ref, Decimal("0")))

        saldo_dia = entradas - saidas
        saldo_final = saldo_inicial + saldo_dia
        saldo_dia_por_data[data_ref] = saldo_dia
        saldo_final_por_data[data_ref] = saldo_final

    return saldo_inicial_por_data, saldo_dia_por_data, saldo_final_por_data


def _ajuste_legacy_resumo_contas_receber(
    *,
    dfc_registros,
    mapa_contas_receber,
    inicio_periodo,
    fim_periodo,
):
    # Compatibilidade com o legado:
    # 1) Total posterior considera o dia final do periodo como parte do bloco posterior.
    # 2) Total anterior desconsidera receitas do dia anterior ao inicio com titulo codigo "4",
    #    deslocando esse valor para o total do periodo.
    dia_anterior = inicio_periodo - timedelta(days=1)
    ajuste_prev_titulo4 = Decimal("0")
    for item in dfc_registros or []:
        data_vencimento = item.get("data_vencimento")
        if data_vencimento != dia_anterior:
            continue
        titulo_codigo = str(item.get("titulo__tipo_titulo_codigo") or "").strip()
        if titulo_codigo != "4":
            continue
        if _classificar_tipo_dfc_por_linha(item) != "receita":
            continue
        ajuste_prev_titulo4 += _parse_decimal_dfc_saldo_ou_zero(item.get("valor_liquido_num")).copy_abs()

    ajuste_dia_final = _parse_decimal_dfc_saldo_ou_zero(mapa_contas_receber.get(fim_periodo, Decimal("0"))).copy_abs()
    return ajuste_prev_titulo4, ajuste_dia_final


def construir_payload_tabela_saldo_dfc(empresa, dfc_registros, hoje=None, dias_periodo=10):
    hoje_ref = hoje or timezone.localdate()
    datas_periodo = [hoje_ref + timedelta(days=offset) for offset in range(max(0, int(dias_periodo)) + 1)]
    if not datas_periodo:
        datas_periodo = [hoje_ref]
    inicio_periodo = datas_periodo[0]
    fim_periodo = datas_periodo[-1]

    mapa_contas_receber = {}
    mapa_contas_pagar = {}
    mapa_contas_receber_por_titulo_norm = {}
    mapa_rotulo_titulo_por_norm = {}
    ajuste_prev_titulo4_por_norm = {}
    dia_anterior_inicio = inicio_periodo - timedelta(days=1)
    for item in dfc_registros or []:
        data_ref = item.get("data_vencimento") or item.get("data_negociacao")
        if not data_ref:
            continue
        valor = _parse_decimal_dfc_saldo_ou_zero(item.get("valor_liquido_num"))
        tipo = _classificar_tipo_dfc_por_linha(item)
        if tipo == "receita":
            mapa_contas_receber[data_ref] = mapa_contas_receber.get(data_ref, Decimal("0")) + valor.copy_abs()
            titulo_label = _titulo_conta_receber_label_dfc_saldo(item)
            titulo_norm = _normalizar_token_texto(titulo_label)
            if titulo_norm not in mapa_contas_receber_por_titulo_norm:
                mapa_contas_receber_por_titulo_norm[titulo_norm] = {}
            if titulo_norm not in mapa_rotulo_titulo_por_norm:
                mapa_rotulo_titulo_por_norm[titulo_norm] = titulo_label
            mapa_contas_receber_por_titulo_norm[titulo_norm][data_ref] = (
                mapa_contas_receber_por_titulo_norm[titulo_norm].get(data_ref, Decimal("0")) + valor.copy_abs()
            )
            if data_ref == dia_anterior_inicio and str(item.get("titulo__tipo_titulo_codigo") or "").strip() == "4":
                ajuste_prev_titulo4_por_norm[titulo_norm] = (
                    ajuste_prev_titulo4_por_norm.get(titulo_norm, Decimal("0")) + valor.copy_abs()
                )
        elif tipo == "despesa":
            mapa_contas_pagar[data_ref] = mapa_contas_pagar.get(data_ref, Decimal("0")) + valor.copy_abs()

    mapa_manuais = _mapa_dfc_saldos_manuais_por_tipo(empresa)
    mapa_previsao_recebivel = mapa_manuais.get(DFCSaldoManual.TIPO_PREVISAO_RECEBIVEL, {})
    mapa_outras_receita = mapa_manuais.get(DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_RECEITA, {})
    mapa_adiantamentos_previsao = mapa_manuais.get(DFCSaldoManual.TIPO_ADIANTAMENTOS_PREVISAO, {})
    mapa_outras_despesa = mapa_manuais.get(DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_DESPESA, {})
    mapa_contas_receber_base = dict(mapa_contas_receber)

    detalhes_contas_receber = []
    mapa_contas_receber_dias = {data_ref: Decimal("0") for data_ref in datas_periodo}
    ordem_norm_legacy = [
        (_normalizar_token_texto(label), label)
        for label in _DFC_SALDO_CONTAS_RECEBER_ORDEM_LEGADO
    ]
    normas_legacy = {norm for norm, _ in ordem_norm_legacy}
    extras_norm = sorted(
        [norm for norm in mapa_contas_receber_por_titulo_norm.keys() if norm not in normas_legacy],
        key=lambda norm: _normalizar_token_texto(mapa_rotulo_titulo_por_norm.get(norm, norm)),
    )
    ordem_final = list(ordem_norm_legacy) + [
        (norm, mapa_rotulo_titulo_por_norm.get(norm, "").upper() or norm.upper())
        for norm in extras_norm
    ]

    for indice, (titulo_norm, titulo_label_exibicao) in enumerate(ordem_final, start=1):
        mapa_base_titulo = mapa_contas_receber_por_titulo_norm.get(titulo_norm, {})
        usar_regra_dia_anterior = _titulo_conta_receber_usa_regra_dia_anterior(titulo_label_exibicao)
        mapa_dias_titulo = _mapa_dias_receita_por_titulo(
            mapa_base_titulo,
            datas_periodo,
            usar_regra_dia_anterior,
        )
        for data_ref in datas_periodo:
            mapa_contas_receber_dias[data_ref] = (
                mapa_contas_receber_dias.get(data_ref, Decimal("0"))
                + _parse_decimal_dfc_saldo_ou_zero(mapa_dias_titulo.get(data_ref))
            )
        valores_titulo = _montar_valores_linha_dfc_saldo(
            mapa_base_titulo,
            datas_periodo,
            inicio_periodo,
            fim_periodo,
        )
        (
            total_anterior_titulo,
            total_periodo_titulo,
            total_posterior_titulo,
        ) = _aplicar_ajustes_legacy_totais_linha_receita(
            mapa_base_por_data=mapa_base_titulo,
            inicio_periodo=inicio_periodo,
            fim_periodo=fim_periodo,
            ajuste_prev_titulo4=ajuste_prev_titulo4_por_norm.get(titulo_norm, Decimal("0")),
        )
        _aplicar_totais_resumo_em_valores_dfc_saldo(
            valores_titulo,
            total_anterior=total_anterior_titulo,
            total_periodo=total_periodo_titulo,
            total_posterior=total_posterior_titulo,
        )
        _atualizar_colunas_dia_em_valores_dfc_saldo(valores_titulo, datas_periodo, mapa_dias_titulo)
        detalhes_contas_receber.append(
            {
                "key": _chave_detalhe_conta_receber(titulo_label_exibicao, indice),
                "label": titulo_label_exibicao,
                "group": "receita",
                "editable_day": False,
                "manual_tipo": "",
                "values": valores_titulo,
                "is_detail": True,
                "parent_key": "contas_receber",
                "use_checkbox": True,
                "checked_default": True,
                "uses_special_day_rule": usar_regra_dia_anterior,
            }
        )

    valores_contas_receber = _montar_valores_linha_dfc_saldo(
        mapa_contas_receber,
        datas_periodo,
        inicio_periodo,
        fim_periodo,
    )
    _atualizar_colunas_dia_em_valores_dfc_saldo(valores_contas_receber, datas_periodo, mapa_contas_receber_dias)

    saldo_inicial_por_data, saldo_dia_por_data, saldo_final_por_data = _montar_linha_saldo_inicial_e_saldos_dia(
        datas_periodo=datas_periodo,
        mapa_contas_receber=mapa_contas_receber_dias,
        mapa_previsao_recebivel=mapa_previsao_recebivel,
        mapa_outras_receita=mapa_outras_receita,
        mapa_contas_pagar=mapa_contas_pagar,
        mapa_adiantamentos_previsao=mapa_adiantamentos_previsao,
        mapa_outras_despesa=mapa_outras_despesa,
        incluir_previsoes=True,
        incluir_outras=True,
    )

    colunas = [
        {
            "key": _DFC_SALDO_CHAVE_TOTAL_ANTERIOR,
            "label": f"Total Anterior a {inicio_periodo.strftime('%d/%m/%Y')}",
            "kind": "summary",
        },
        {
            "key": _DFC_SALDO_CHAVE_TOTAL_PERIODO,
            "label": "TOTAL Periodo",
            "kind": "summary",
        },
        {
            "key": _DFC_SALDO_CHAVE_TOTAL_POSTERIOR,
            "label": f"Total Posterior a {fim_periodo.strftime('%d/%m/%Y')}",
            "kind": "summary",
        },
    ]
    for data_ref in datas_periodo:
        colunas.append(
            {
                "key": _chave_coluna_dia_dfc_saldo(data_ref),
                "label": f"{data_ref.strftime('%d/%m/%y')} - {_DFC_SALDO_DIA_SEMANA_ABREV[data_ref.weekday()]}",
                "kind": "day",
                "date_iso": data_ref.strftime("%Y-%m-%d"),
            }
        )

    linha_saldo_inicial = {
        _DFC_SALDO_CHAVE_TOTAL_ANTERIOR: None,
        _DFC_SALDO_CHAVE_TOTAL_PERIODO: None,
        _DFC_SALDO_CHAVE_TOTAL_POSTERIOR: None,
    }
    linha_saldo_dia = {
        _DFC_SALDO_CHAVE_TOTAL_ANTERIOR: None,
        _DFC_SALDO_CHAVE_TOTAL_PERIODO: _float_ou_none(sum(saldo_dia_por_data.values(), Decimal("0"))),
        _DFC_SALDO_CHAVE_TOTAL_POSTERIOR: None,
    }
    linha_saldo_final = {
        _DFC_SALDO_CHAVE_TOTAL_ANTERIOR: None,
        _DFC_SALDO_CHAVE_TOTAL_PERIODO: _float_ou_none(sum(saldo_final_por_data.values(), Decimal("0"))),
        _DFC_SALDO_CHAVE_TOTAL_POSTERIOR: None,
    }
    for data_ref in datas_periodo:
        chave = _chave_coluna_dia_dfc_saldo(data_ref)
        linha_saldo_inicial[chave] = _float_ou_none(saldo_inicial_por_data.get(data_ref, Decimal("0")))
        linha_saldo_dia[chave] = _float_ou_none(saldo_dia_por_data.get(data_ref, Decimal("0")))
        linha_saldo_final[chave] = _float_ou_none(saldo_final_por_data.get(data_ref, Decimal("0")))

    linhas = [
        {
            "key": "saldo_inicial",
            "label": "Saldo Inicial",
            "group": "total",
            "editable_day": False,
            "manual_tipo": "",
            "values": linha_saldo_inicial,
        },
        {
            "key": "contas_receber",
            "label": "CONTAS A RECEBER",
            "group": "receita",
            "editable_day": False,
            "manual_tipo": "",
            "values": valores_contas_receber,
            "has_children": bool(detalhes_contas_receber),
            "expanded_default": False,
            "use_checkbox": False,
        },
        *detalhes_contas_receber,
        {
            "key": "previsao_recebivel",
            "label": "PREVISAO RECEBIVEL",
            "group": "receita",
            "editable_day": True,
            "manual_tipo": DFCSaldoManual.TIPO_PREVISAO_RECEBIVEL,
            "values": _montar_valores_linha_dfc_saldo(mapa_previsao_recebivel, datas_periodo, inicio_periodo, fim_periodo),
        },
        {
            "key": "outras_consideracoes_receita",
            "label": "OUTRAS CONSIDERACOES",
            "group": "receita",
            "editable_day": True,
            "manual_tipo": DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_RECEITA,
            "values": _montar_valores_linha_dfc_saldo(mapa_outras_receita, datas_periodo, inicio_periodo, fim_periodo),
        },
        {
            "key": "contas_pagar",
            "label": "CONTAS A PAGAR",
            "group": "despesa",
            "editable_day": False,
            "manual_tipo": "",
            "values": _montar_valores_linha_dfc_saldo(mapa_contas_pagar, datas_periodo, inicio_periodo, fim_periodo),
        },
        {
            "key": "adiantamentos_previsao",
            "label": "ADIANTAMENTOS PREVISAO",
            "group": "despesa",
            "editable_day": True,
            "manual_tipo": DFCSaldoManual.TIPO_ADIANTAMENTOS_PREVISAO,
            "values": _montar_valores_linha_dfc_saldo(
                mapa_adiantamentos_previsao,
                datas_periodo,
                inicio_periodo,
                fim_periodo,
            ),
        },
        {
            "key": "outras_consideracoes_despesa",
            "label": "OUTRAS CONSIDERACOES",
            "group": "despesa",
            "editable_day": True,
            "manual_tipo": DFCSaldoManual.TIPO_OUTRAS_CONSIDERACOES_DESPESA,
            "values": _montar_valores_linha_dfc_saldo(mapa_outras_despesa, datas_periodo, inicio_periodo, fim_periodo),
        },
        {
            "key": "saldo_dia",
            "label": "SALDO DO DIA",
            "group": "total",
            "editable_day": False,
            "manual_tipo": "",
            "values": linha_saldo_dia,
        },
        {
            "key": "saldo_final",
            "label": "SALDO FINAL",
            "group": "total",
            "editable_day": False,
            "manual_tipo": "",
            "values": linha_saldo_final,
        },
    ]

    contas_receber_row = _obter_linha_por_chave_dfc_saldo(linhas, "contas_receber")
    if contas_receber_row:
        ajuste_prev_titulo4, _ = _ajuste_legacy_resumo_contas_receber(
            dfc_registros=dfc_registros,
            mapa_contas_receber=mapa_contas_receber_base,
            inicio_periodo=inicio_periodo,
            fim_periodo=fim_periodo,
        )
        total_anterior, total_periodo, total_posterior = _aplicar_ajustes_legacy_totais_linha_receita(
            mapa_base_por_data=mapa_contas_receber_base,
            inicio_periodo=inicio_periodo,
            fim_periodo=fim_periodo,
            ajuste_prev_titulo4=ajuste_prev_titulo4,
        )

        valores = contas_receber_row.get("values") or {}
        _aplicar_totais_resumo_em_valores_dfc_saldo(
            valores,
            total_anterior=total_anterior,
            total_periodo=total_periodo,
            total_posterior=total_posterior,
        )
        # Compatibilidade legado: a ultima coluna diaria da linha azul replica o Total Posterior.
        chave_dia_final = _chave_coluna_dia_dfc_saldo(fim_periodo)
        valores[chave_dia_final] = _float_ou_none(total_posterior)

        mapa_contas_receber_ajustado = {}
        for data_ref in datas_periodo:
            chave_dia = _chave_coluna_dia_dfc_saldo(data_ref)
            mapa_contas_receber_ajustado[data_ref] = _parse_decimal_dfc_saldo_ou_zero(valores.get(chave_dia))

        (
            saldo_inicial_ajustado_por_data,
            saldo_dia_ajustado_por_data,
            saldo_final_ajustado_por_data,
        ) = _montar_linha_saldo_inicial_e_saldos_dia(
            datas_periodo=datas_periodo,
            mapa_contas_receber=mapa_contas_receber_ajustado,
            mapa_previsao_recebivel=mapa_previsao_recebivel,
            mapa_outras_receita=mapa_outras_receita,
            mapa_contas_pagar=mapa_contas_pagar,
            mapa_adiantamentos_previsao=mapa_adiantamentos_previsao,
            mapa_outras_despesa=mapa_outras_despesa,
            incluir_previsoes=True,
            incluir_outras=True,
        )

        saldo_inicial_row = _obter_linha_por_chave_dfc_saldo(linhas, "saldo_inicial")
        saldo_dia_row = _obter_linha_por_chave_dfc_saldo(linhas, "saldo_dia")
        saldo_final_row = _obter_linha_por_chave_dfc_saldo(linhas, "saldo_final")

        if saldo_inicial_row:
            valores_saldo_inicial = saldo_inicial_row.get("values") or {}
            _atualizar_colunas_dia_em_valores_dfc_saldo(
                valores_saldo_inicial,
                datas_periodo,
                saldo_inicial_ajustado_por_data,
            )

        if saldo_dia_row:
            valores_saldo_dia = saldo_dia_row.get("values") or {}
            valores_saldo_dia[_DFC_SALDO_CHAVE_TOTAL_PERIODO] = _float_ou_none(
                sum(saldo_dia_ajustado_por_data.values(), Decimal("0"))
            )
            _atualizar_colunas_dia_em_valores_dfc_saldo(
                valores_saldo_dia,
                datas_periodo,
                saldo_dia_ajustado_por_data,
            )

        if saldo_final_row:
            valores_saldo_final = saldo_final_row.get("values") or {}
            valores_saldo_final[_DFC_SALDO_CHAVE_TOTAL_PERIODO] = _float_ou_none(
                sum(saldo_final_ajustado_por_data.values(), Decimal("0"))
            )
            _atualizar_colunas_dia_em_valores_dfc_saldo(
                valores_saldo_final,
                datas_periodo,
                saldo_final_ajustado_por_data,
            )

    return {
        "columns": colunas,
        "rows": linhas,
        "today_iso": hoje_ref.strftime("%Y-%m-%d"),
        "period_end_iso": fim_periodo.strftime("%Y-%m-%d"),
        "checkbox_defaults": {
            "incluir_previsoes": True,
            "incluir_outras_consideracoes": True,
        },
    }


def salvar_dfc_saldo_manual_por_post(empresa, post_data):
    data_raw = str(post_data.get("data_referencia") or "").strip()
    tipo_raw = str(post_data.get("tipo") or "").strip()
    valor = _parse_decimal_dfc_saldo_ou_zero(post_data.get("valor"))

    if tipo_raw not in _DFC_SALDO_MANUAL_TIPOS.values():
        return False, "Tipo de linha invalido.", Decimal("0")

    try:
        data_referencia = datetime.strptime(data_raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return False, "Data de referencia invalida.", Decimal("0")

    if valor == Decimal("0"):
        DFCSaldoManual.objects.filter(
            empresa=empresa,
            data_referencia=data_referencia,
            tipo=tipo_raw,
        ).delete()
        return True, "Valor removido.", Decimal("0")

    DFCSaldoManual.objects.update_or_create(
        empresa=empresa,
        data_referencia=data_referencia,
        tipo=tipo_raw,
        defaults={"valor": valor},
    )
    return True, "Valor salvo com sucesso.", valor
