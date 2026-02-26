from __future__ import annotations

from decimal import Decimal

from ..models import (
    ParametroMargemAdministracao,
    ParametroMargemFinanceiro,
    ParametroMargemLogistica,
    ParametroMargemVendas,
)


def _primeiro_parametro_ou_none(qs):
    return qs.order_by("id").first()


def _parametro_logistica_operador_ou_fallback(empresa):
    operador = (
        ParametroMargemLogistica.objects.filter(empresa=empresa, parametro__icontains="operador")
        .order_by("id")
        .first()
    )
    if operador:
        return operador
    return _primeiro_parametro_ou_none(ParametroMargemLogistica.objects.filter(empresa=empresa))


def obter_parametros_controle_margem(empresa):
    parametro_vendas = _primeiro_parametro_ou_none(ParametroMargemVendas.objects.filter(empresa=empresa))
    if parametro_vendas is None:
        parametro_vendas = ParametroMargemVendas.objects.create(
            empresa=empresa,
            parametro="Vendas",
            criterio="Geral",
            remuneracao_percentual=Decimal("0"),
        )

    parametro_logistica = _parametro_logistica_operador_ou_fallback(empresa)
    if parametro_logistica is None:
        parametro_logistica = ParametroMargemLogistica.objects.create(
            empresa=empresa,
            parametro="Operador Logistico",
            criterio="Entrega+Balcao",
            remuneracao_rs=Decimal("0"),
        )

    parametro_administracao, _ = ParametroMargemAdministracao.objects.get_or_create(empresa=empresa)
    parametro_financeiro = _primeiro_parametro_ou_none(ParametroMargemFinanceiro.objects.filter(empresa=empresa))
    if parametro_financeiro is None:
        parametro_financeiro = ParametroMargemFinanceiro.objects.create(
            empresa=empresa,
            parametro="Contas a Receber",
            taxa_ao_mes=Decimal("0"),
            remuneracao_percentual=Decimal("0"),
        )
    return {
        "vendas": parametro_vendas,
        "logistica": parametro_logistica,
        "administracao": parametro_administracao,
        "financeiro": parametro_financeiro,
    }


def _empresa_filial(nome_empresa: str) -> bool:
    return (str(nome_empresa or "").strip().upper() == "5 - SAFIA DISTRIBUIDORA FILIAL")


def calcular_campos_controle_margem_legado(
    *,
    nome_empresa: str,
    gerente: str | None,
    tipo_venda: str | None,
    vlr_nota,
    custo_total_produto,
    peso_bruto,
    valor_tonelada_frete_safia,
    taxa_vendas_percentual,
    taxa_operador_logistica_rs,
    taxa_administracao_percentual,
    taxa_financeiro_mes,
):
    vlr_nota = Decimal(vlr_nota or 0)
    custo_total_produto = Decimal(custo_total_produto or 0)
    peso_bruto = Decimal(peso_bruto or 0)
    valor_tonelada_frete_safia = Decimal(valor_tonelada_frete_safia or 0)

    lucro_bruto = vlr_nota - custo_total_produto
    margem_bruta = Decimal("0") if vlr_nota == 0 else (lucro_bruto / vlr_nota)
    custo_por_kg = Decimal("0") if peso_bruto == 0 else (custo_total_produto / peso_bruto)

    filial = _empresa_filial(nome_empresa)
    tipo_venda_norm = str(tipo_venda or "").strip().lower()
    gerente_norm = str(gerente or "").strip().upper()

    vendas = Decimal("0") if filial else (Decimal(taxa_vendas_percentual or 0) * vlr_nota)
    producao = Decimal("0")
    if not filial and gerente_norm == "GERENTE PA":
        producao = (peso_bruto / Decimal("30")) * Decimal("1.4")

    operador_logistica = (
        Decimal("0")
        if filial
        else (peso_bruto / Decimal("1000")) * Decimal(taxa_operador_logistica_rs or 0)
    )

    frete_distribuicao = Decimal("0")
    if tipo_venda_norm == "entrega":
        frete_distribuicao = (peso_bruto / Decimal("1000")) * valor_tonelada_frete_safia

    total_logistica = Decimal("0") if filial else (operador_logistica + frete_distribuicao)
    administracao = Decimal("0") if filial else (Decimal(taxa_administracao_percentual or 0) * vlr_nota)
    financeiro = Decimal(taxa_financeiro_mes or 0) * vlr_nota

    total_setores = vendas + producao + total_logistica + administracao + financeiro
    valor_liquido = lucro_bruto - total_setores
    margem_liquida = Decimal("0") if vlr_nota == 0 else (valor_liquido / vlr_nota)

    return {
        "lucro_bruto": lucro_bruto,
        "margem_bruta": margem_bruta,
        "custo_por_kg": custo_por_kg,
        "vendas": vendas,
        "producao": producao,
        "operador_logistica": operador_logistica,
        "frete_distribuicao": frete_distribuicao,
        "total_logistica": total_logistica,
        "administracao": administracao,
        "financeiro": financeiro,
        "total_setores": total_setores,
        "valor_liquido": valor_liquido,
        "margem_liquida": margem_liquida,
    }
