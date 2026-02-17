from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from ..tabulator import build_carteiras_tabulator, build_vendas_tabulator


def _to_decimal(valor):
    if valor in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _dividir_ou_zero(numerador: Decimal, denominador: Decimal) -> Decimal:
    if denominador <= 0:
        return Decimal("0")
    return numerador / denominador


def _format_numero(valor, casas=0):
    valor = _to_decimal(valor)
    quant = Decimal("1") if casas == 0 else Decimal("1").scaleb(-casas)
    valor = valor.quantize(quant, rounding=ROUND_HALF_UP)
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_percentual(valor):
    return f"{_format_numero(valor, 2)}%"


def _format_moeda(valor):
    return f"R$ {_format_numero(valor, 2)}"


def _calcular_dashboard_resumo_carteira(carteiras_qs):
    registros = list(carteiras_qs)

    qtd_total = len(registros)
    #Verificar limite e faturamento
    limite_total = sum(_to_decimal(item.get("limite_credito_num")) for item in registros)
    faturamento_total = sum(_to_decimal(item.get("valor_faturado_num")) for item in registros)

    registros_reais = [item for item in registros if _to_decimal(item.get("valor_faturado_num")) > 0]

    qtd_total_real = len(registros_reais)
    #Verificar limite e faturamento
    limite_total_real = sum(_to_decimal(item.get("limite_credito_num")) for item in registros_reais)
    faturamento_total_real = sum(_to_decimal(item.get("valor_faturado_num")) for item in registros_reais)

    qtd_total_decimal = Decimal(qtd_total)
    qtd_total_real_decimal = Decimal(qtd_total_real)

    positivacao_real = _dividir_ou_zero(qtd_total_real_decimal * Decimal("100"), qtd_total_decimal)
    positivacao_total = Decimal("100") - positivacao_real

    media_limite_total = _dividir_ou_zero(limite_total, qtd_total_decimal)
    media_faturamento_total = _dividir_ou_zero(faturamento_total, qtd_total_decimal)
    pulga_total = _dividir_ou_zero(faturamento_total * Decimal("100"), limite_total)

    media_limite_real = _dividir_ou_zero(limite_total_real, qtd_total_real_decimal)
    media_faturamento_real = _dividir_ou_zero(faturamento_total_real, qtd_total_real_decimal)
    pulga_real = _dividir_ou_zero(faturamento_total_real * Decimal("100"), limite_total_real)

    return {
        "registros": registros,
        "total_carteira": {
            "qtd_total": _format_numero(qtd_total, 0),
            "positivacao": _format_percentual(positivacao_total),
            "limite_credito": _format_moeda(limite_total),
            "total_faturamento": _format_moeda(faturamento_total),
            "media_limite": _format_moeda(media_limite_total),
            "media_faturamento": _format_numero(media_faturamento_total, 2),
            "pulga": _format_percentual(pulga_total),
        },
        "total_real": {
            "qtd_total": _format_numero(qtd_total_real, 0),
            "positivacao": _format_percentual(positivacao_real),
            "limite_credito": _format_moeda(limite_total_real),
            "total_faturamento": _format_moeda(faturamento_total_real),
            "media_limite": _format_moeda(media_limite_real),
            "media_faturamento": _format_numero(media_faturamento_real, 2),
            "pulga": _format_percentual(pulga_real),
        },
    }


def _calcular_dashboard_carteira(carteiras_dashboard_qs):
    hoje = date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month

    agregados_por_ano_mes = {}
    anos_disponiveis_set = set()
    for item in carteiras_dashboard_qs:
        data_cadastro = item.get("data_cadastro")
        if not data_cadastro:
            continue

        ano = data_cadastro.year
        mes = data_cadastro.month
        anos_disponiveis_set.add(ano)

        chave = f"{ano}-{mes:02d}"
        if chave not in agregados_por_ano_mes:
            agregados_por_ano_mes[chave] = {"qtd": 0, "valor": 0.0}

        agregados_por_ano_mes[chave]["qtd"] += 1
        valor = item.get("valor_faturado") or 0
        valor_decimal = _to_decimal(valor)
        agregados_por_ano_mes[chave]["valor"] += float(valor_decimal)

    anos_disponiveis = sorted(anos_disponiveis_set)
    for chave in agregados_por_ano_mes:
        agregados_por_ano_mes[chave]["valor"] = round(agregados_por_ano_mes[chave]["valor"], 2)

    if ano_atual in anos_disponiveis:
        ano_dashboard_inicial = ano_atual
    elif anos_disponiveis:
        ano_dashboard_inicial = anos_disponiveis[-1]
    else:
        ano_dashboard_inicial = ano_atual

    return {
        "dashboard_carteira_anos_disponiveis": anos_disponiveis,
        "dashboard_carteira_agregados_por_ano_mes": agregados_por_ano_mes,
        "dashboard_carteira_ano_inicial": ano_dashboard_inicial,
        "dashboard_carteira_ano_atual": ano_atual,
        "dashboard_carteira_mes_atual": mes_atual,
    }


def montar_contexto_carteira(
    *,
    empresa,
    modulo_nome,
    arquivo_existente,
    tem_arquivo_existente,
    carteiras_qs,
    cidades,
    regioes,
    parceiros,
    carteiras_dashboard_qs,
):
    dashboard_resumo = _calcular_dashboard_resumo_carteira(carteiras_qs)
    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo_nome,
        "arquivo_existente": arquivo_existente,
        "tem_arquivo_existente": tem_arquivo_existente,
        "carteiras_tabulator": build_carteiras_tabulator(dashboard_resumo["registros"], empresa.id),
        "cidades": cidades,
        "regioes": regioes,
        "parceiros": parceiros,
        "dashboard_resumo_total_carteira": dashboard_resumo["total_carteira"],
        "dashboard_resumo_total_real": dashboard_resumo["total_real"],
    }
    contexto.update(_calcular_dashboard_carteira(carteiras_dashboard_qs))
    return contexto


def montar_contexto_vendas(
    *,
    empresa,
    modulo_nome,
    arquivo_existente,
    tem_arquivo_existente,
    vendas_qs,
):
    return {
        "empresa": empresa,
        "modulo_nome": modulo_nome,
        "arquivo_existente": arquivo_existente,
        "tem_arquivo_existente": tem_arquivo_existente,
        "vendas_tabulator": build_vendas_tabulator(vendas_qs, empresa.id),
    }

def _definir_lucro(valor_venda, custo_medio_icms_cmv):
    lucro = _to_decimal(valor_venda) - _to_decimal(custo_medio_icms_cmv)
    return lucro


def _definir_margem(lucro, valor_venda):
    margem = _dividir_ou_zero(lucro, valor_venda) * 100
    return margem
