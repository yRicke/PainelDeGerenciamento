from __future__ import annotations

from django.urls import reverse
from django.utils import timezone


def _fmt_date_br(data):
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")


def _situacao_margem(margem):
    try:
        valor = float(margem)
    except (TypeError, ValueError):
        valor = 0.0

    if valor < 10:
        return "Roxo"
    if valor < 13:
        return "Vermelho"
    if valor <= 14:
        return "Amarelo"
    return "Verde"


def build_atividades_tabulator(atividades_qs, empresa_id: int):
    return [
        {
            "id": atividade.id,
            "projeto": atividade.projeto.nome,
            "codigo_projeto": atividade.projeto.codigo or "-",
            "gestor": atividade.gestor.nome if atividade.gestor else "-",
            "responsavel": atividade.responsavel.nome if atividade.responsavel else "-",
            "interlocutor": atividade.interlocutor,
            "semana_de_prazo": atividade.semana_de_prazo or "-",
            "data_previsao_inicio": _fmt_date_br(atividade.data_previsao_inicio),
            "data_previsao_termino": _fmt_date_br(atividade.data_previsao_termino),
            "data_finalizada": _fmt_date_br(atividade.data_finalizada),
            "indicador": atividade.indicador,
            "historico": atividade.historico,
            "tarefa": atividade.tarefa,
            "progresso": atividade.progresso,
            "editar_url": reverse(
                "editar_atividade_tofu",
                kwargs={"empresa_id": empresa_id, "atividade_id": atividade.id},
            ),
        }
        for atividade in atividades_qs
    ]


def build_carteiras_tabulator(carteiras_qs, empresa_id: int):
    resultado = []
    for carteira_item in carteiras_qs:
        data_cadastro = carteira_item.get("data_cadastro")
        resultado.append(
            {
                "id": carteira_item.get("id"),
                "nome_parceiro": carteira_item.get("parceiro__nome") or "",
                "codigo_parceiro": carteira_item.get("parceiro__codigo") or "",
                "gerente": carteira_item.get("gerente") or "",
                "vendedor": carteira_item.get("vendedor") or "",
                "valor_faturado": float(carteira_item.get("valor_faturado_num") or 0),
                "limite_credito": float(carteira_item.get("limite_credito_num") or 0),
                "ultima_venda": _fmt_date_br(carteira_item.get("ultima_venda")),
                "qtd_dias_sem_venda": carteira_item.get("qtd_dias_sem_venda") or 0,
                "intervalo": carteira_item.get("intervalo") or "",
                "descricao_perfil": carteira_item.get("descricao_perfil") or "",
                "ativo_indicador": bool(carteira_item.get("ativo_indicador")),
                "cliente_indicador": bool(carteira_item.get("cliente_indicador")),
                "fornecedor_indicador": bool(carteira_item.get("fornecedor_indicador")),
                "transporte_indicador": bool(carteira_item.get("transporte_indicador")),
                "ano_cadastro": data_cadastro.year if data_cadastro else "",
                "data_cadastro": _fmt_date_br(data_cadastro),
                "regiao_nome": carteira_item.get("regiao__nome") or "",
                "regiao_codigo": carteira_item.get("regiao__codigo") or "",
                "cidade_nome": carteira_item.get("cidade__nome") or "",
                "cidade_codigo": carteira_item.get("cidade__codigo") or "",
                "editar_url": reverse(
                    "editar_carteira_modulo",
                    kwargs={"empresa_id": empresa_id, "carteira_id": carteira_item.get("id")},
                ),
            }
        )
    return resultado


def build_vendas_tabulator(vendas_qs, empresa_id: int):
    resultado = []
    for venda in vendas_qs:
        data_venda = venda.get("data_venda")
        margem_num = float(venda.get("margem_num") or 0)
        resultado.append(
            {
                "id": venda.get("id"),
                "codigo": venda.get("codigo") or "",
                "descricao": venda.get("descricao") or "",
                "valor_venda": float(venda.get("valor_venda_num") or 0),
                "qtd_notas": venda.get("qtd_notas") or 0,
                "custo_medio_icms_cmv": float(venda.get("custo_medio_icms_cmv_num") or 0),
                "lucro": float(venda.get("lucro_num") or 0),
                "peso_bruto": float(venda.get("peso_bruto_num") or 0),
                "peso_liquido": float(venda.get("peso_liquido_num") or 0),
                "margem": margem_num,
                "margem_situacao": _situacao_margem(margem_num),
                "data_venda": _fmt_date_br(data_venda),
                "data_venda_iso": data_venda.strftime("%Y-%m-%d") if data_venda else "",
                "ano_venda": data_venda.year if data_venda else "",
                "mes_venda": data_venda.month if data_venda else "",
                "editar_url": reverse(
                    "editar_venda_modulo",
                    kwargs={"empresa_id": empresa_id, "venda_id": venda.get("id")},
                ),
            }
        )
    return resultado


def build_cargas_tabulator(cargas_qs, empresa_id: int):
    resultado = []
    for carga in cargas_qs:
        resultado.append(
            {
                "id": carga.id,
                "situacao": carga.situacao or "",
                "ordem_de_carga_codigo": carga.ordem_de_carga_codigo or "",
                "data_inicio": _fmt_date_br(carga.data_inicio),
                "data_prevista_saida": _fmt_date_br(carga.data_prevista_saida),
                "data_chegada": _fmt_date_br(carga.data_chegada),
                "data_finalizacao": _fmt_date_br(carga.data_finalizacao),
                "nome_motorista": carga.nome_motorista or "",
                "nome_fantasia_empresa": carga.nome_fantasia_empresa or "",
                "regiao_nome": carga.regiao.nome if carga.regiao else "",
                "regiao_codigo": carga.regiao.codigo if carga.regiao else "",
                "prazo_maximo_dias": carga.prazo_maximo_dias or 0,
                "idade_dias": carga.idade_dias or 0,
                "verificacao": bool(carga.verificacao),
                "critica": carga.critica,
                "editar_url": reverse(
                    "editar_carga_modulo",
                    kwargs={"empresa_id": empresa_id, "carga_id": carga.id},
                ),
            }
        )
    return resultado


def build_colaboradores_tabulator(colaboradores_qs, empresa_id: int):
    return [
        {
            "id": colaborador.id,
            "nome": colaborador.nome,
            "editar_url": reverse(
                "editar_colaborador_modulo",
                kwargs={"empresa_id": empresa_id, "colaborador_id": colaborador.id},
            ),
            "excluir_url": reverse(
                "excluir_colaborador_modulo",
                kwargs={"empresa_id": empresa_id, "colaborador_id": colaborador.id},
            ),
        }
        for colaborador in colaboradores_qs
    ]


def build_projetos_tabulator(projetos_qs, empresa_id: int):
    return [
        {
            "id": projeto.id,
            "nome": projeto.nome,
            "codigo": projeto.codigo or "",
            "editar_url": reverse(
                "editar_projeto_modulo",
                kwargs={"empresa_id": empresa_id, "projeto_id": projeto.id},
            ),
            "excluir_url": reverse(
                "excluir_projeto_modulo",
                kwargs={"empresa_id": empresa_id, "projeto_id": projeto.id},
            ),
        }
        for projeto in projetos_qs
    ]


def build_cidades_tabulator(cidades_qs, empresa_id: int):
    return [
        {
            "id": cidade.id,
            "nome": cidade.nome,
            "codigo": cidade.codigo,
            "editar_url": reverse(
                "editar_cidade_modulo",
                kwargs={"empresa_id": empresa_id, "cidade_id": cidade.id},
            ),
            "excluir_url": reverse(
                "excluir_cidade_modulo",
                kwargs={"empresa_id": empresa_id, "cidade_id": cidade.id},
            ),
        }
        for cidade in cidades_qs
    ]


def build_regioes_tabulator(regioes_qs, empresa_id: int):
    return [
        {
            "id": regiao.id,
            "nome": regiao.nome,
            "codigo": regiao.codigo,
            "editar_url": reverse(
                "editar_regiao_modulo",
                kwargs={"empresa_id": empresa_id, "regiao_id": regiao.id},
            ),
            "excluir_url": reverse(
                "excluir_regiao_modulo",
                kwargs={"empresa_id": empresa_id, "regiao_id": regiao.id},
            ),
        }
        for regiao in regioes_qs
    ]


def build_parceiros_tabulator(parceiros_qs, empresa_id: int):
    return [
        {
            "id": parceiro.id,
            "nome": parceiro.nome,
            "codigo": parceiro.codigo,
            "editar_url": reverse(
                "editar_parceiro_modulo",
                kwargs={"empresa_id": empresa_id, "parceiro_id": parceiro.id},
            ),
            "excluir_url": reverse(
                "excluir_parceiro_modulo",
                kwargs={"empresa_id": empresa_id, "parceiro_id": parceiro.id},
            ),
        }
        for parceiro in parceiros_qs
    ]


def build_titulos_tabulator(titulos_qs, empresa_id: int):
    return [
        {
            "id": titulo.id,
            "tipo_titulo_codigo": titulo.tipo_titulo_codigo,
            "descricao": titulo.descricao or "",
            "editar_url": reverse(
                "editar_titulo_modulo",
                kwargs={"empresa_id": empresa_id, "titulo_id": titulo.id},
            ),
            "excluir_url": reverse(
                "excluir_titulo_modulo",
                kwargs={"empresa_id": empresa_id, "titulo_id": titulo.id},
            ),
        }
        for titulo in titulos_qs
    ]


def build_naturezas_tabulator(naturezas_qs, empresa_id: int):
    return [
        {
            "id": natureza.id,
            "codigo": natureza.codigo,
            "descricao": natureza.descricao or "",
            "editar_url": reverse(
                "editar_natureza_modulo",
                kwargs={"empresa_id": empresa_id, "natureza_id": natureza.id},
            ),
            "excluir_url": reverse(
                "excluir_natureza_modulo",
                kwargs={"empresa_id": empresa_id, "natureza_id": natureza.id},
            ),
        }
        for natureza in naturezas_qs
    ]


def build_operacoes_tabulator(operacoes_qs, empresa_id: int):
    return [
        {
            "id": operacao.id,
            "tipo_operacao_codigo": operacao.tipo_operacao_codigo,
            "descricao_receita_despesa": operacao.descricao_receita_despesa or "",
            "editar_url": reverse(
                "editar_operacao_modulo",
                kwargs={"empresa_id": empresa_id, "operacao_id": operacao.id},
            ),
            "excluir_url": reverse(
                "excluir_operacao_modulo",
                kwargs={"empresa_id": empresa_id, "operacao_id": operacao.id},
            ),
        }
        for operacao in operacoes_qs
    ]


def build_centros_resultado_tabulator(centros_resultado_qs, empresa_id: int):
    return [
        {
            "id": centro.id,
            "descricao": centro.descricao,
            "editar_url": reverse(
                "editar_centro_resultado_modulo",
                kwargs={"empresa_id": empresa_id, "centro_resultado_id": centro.id},
            ),
            "excluir_url": reverse(
                "excluir_centro_resultado_modulo",
                kwargs={"empresa_id": empresa_id, "centro_resultado_id": centro.id},
            ),
        }
        for centro in centros_resultado_qs
    ]


def build_dfc_tabulator(dfc_qs, empresa_id: int):
    resultado = []
    for dfc_item in dfc_qs:
        resultado.append(
            {
                "id": dfc_item.get("id"),
                "data_negociacao": _fmt_date_br(dfc_item.get("data_negociacao")),
                "data_negociacao_iso": (
                    dfc_item.get("data_negociacao").strftime("%Y-%m-%d")
                    if dfc_item.get("data_negociacao")
                    else ""
                ),
                "data_vencimento": _fmt_date_br(dfc_item.get("data_vencimento")),
                "data_vencimento_iso": (
                    dfc_item.get("data_vencimento").strftime("%Y-%m-%d")
                    if dfc_item.get("data_vencimento")
                    else ""
                ),
                "ano_negociacao": (
                    dfc_item.get("data_negociacao").year
                    if dfc_item.get("data_negociacao")
                    else ""
                ),
                "mes_negociacao": (
                    dfc_item.get("data_negociacao").month
                    if dfc_item.get("data_negociacao")
                    else ""
                ),
                "valor_liquido": float(dfc_item.get("valor_liquido_num") or 0),
                "numero_nota": dfc_item.get("numero_nota") or "",
                "titulo_codigo": dfc_item.get("titulo__tipo_titulo_codigo") or "",
                "titulo_descricao": dfc_item.get("titulo__descricao") or "",
                "centro_resultado_descricao": dfc_item.get("centro_resultado__descricao") or "",
                "natureza_codigo": dfc_item.get("natureza__codigo") or "",
                "natureza_descricao": dfc_item.get("natureza__descricao") or "",
                "historico": dfc_item.get("historico") or "",
                "parceiro_codigo": dfc_item.get("parceiro__codigo") or "",
                "parceiro_nome": dfc_item.get("parceiro__nome") or "",
                "operacao_codigo": dfc_item.get("operacao__tipo_operacao_codigo") or "",
                "operacao_descricao": dfc_item.get("operacao__descricao_receita_despesa") or "",
                "tipo_movimento": dfc_item.get("tipo_movimento") or "",
                "editar_url": reverse(
                    "editar_dfc_modulo",
                    kwargs={"empresa_id": empresa_id, "dfc_id": dfc_item.get("id")},
                ),
            }
        )
    return resultado


def build_contas_a_receber_tabulator(contas_qs, empresa_id: int):
    resultado = []
    hoje = timezone.localdate()
    for conta in contas_qs:
        data_negociacao = conta.get("data_negociacao")
        data_vencimento = conta.get("data_vencimento")
        status = ""
        if data_vencimento:
            if data_vencimento < hoje:
                status = "Vencido"
            elif data_vencimento >= hoje:
                status = "A Vencer"

        dias_diferenca = ""
        if data_vencimento:
            dias_diferenca = (hoje - data_vencimento).days

        intervalo = ""
        if isinstance(dias_diferenca, int):
            dias_intervalo = abs(dias_diferenca)
            if dias_intervalo <= 5:
                intervalo = "0-5 (CML)"
            elif dias_intervalo <= 20:
                intervalo = "6-20 (FIN)"
            elif dias_intervalo <= 30:
                intervalo = "21-30 (POL)"
            elif dias_intervalo <= 60:
                intervalo = "31-60 (POL)"
            elif dias_intervalo <= 90:
                intervalo = "61-90 (POL)"
            elif dias_intervalo <= 120:
                intervalo = "91-120 (JUR1)"
            elif dias_intervalo <= 180:
                intervalo = "121-180 (JUR1)"
            else:
                intervalo = "+180 (JUR2)"

        resultado.append(
            {
                "id": conta.get("id"),
                "data_negociacao": _fmt_date_br(data_negociacao),
                "data_negociacao_iso": (
                    data_negociacao.strftime("%Y-%m-%d")
                    if data_negociacao
                    else ""
                ),
                "data_vencimento": _fmt_date_br(data_vencimento),
                "data_vencimento_iso": (
                    data_vencimento.strftime("%Y-%m-%d")
                    if data_vencimento
                    else ""
                ),
                "data_arquivo": _fmt_date_br(conta.get("data_arquivo")),
                "data_arquivo_iso": (
                    conta.get("data_arquivo").strftime("%Y-%m-%d")
                    if conta.get("data_arquivo")
                    else ""
                ),
                "ano_negociacao": (
                    conta.get("data_negociacao").year
                    if conta.get("data_negociacao")
                    else ""
                ),
                "mes_negociacao": (
                    conta.get("data_negociacao").month
                    if conta.get("data_negociacao")
                    else ""
                ),
                "nome_fantasia_empresa": conta.get("nome_fantasia_empresa") or "",
                "numero_nota": conta.get("numero_nota") or "",
                "vendedor": conta.get("vendedor") or "",
                "valor_desdobramento": float(conta.get("valor_desdobramento_num") or 0),
                "valor_liquido": float(conta.get("valor_liquido_num") or 0),
                "titulo_codigo": conta.get("titulo__tipo_titulo_codigo") or "",
                "titulo_descricao": conta.get("titulo__descricao") or "",
                "natureza_codigo": conta.get("natureza__codigo") or "",
                "natureza_descricao": conta.get("natureza__descricao") or "",
                "centro_resultado_descricao": conta.get("centro_resultado__descricao") or "",
                "parceiro_codigo": conta.get("parceiro__codigo") or "",
                "parceiro_nome": conta.get("parceiro__nome") or "",
                "operacao_codigo": conta.get("operacao__tipo_operacao_codigo") or "",
                "operacao_descricao": conta.get("operacao__descricao_receita_despesa") or "",
                "status": status,
                "dias_diferenca": dias_diferenca,
                "intervalo": intervalo,
                "editar_url": reverse(
                    "editar_contas_a_receber_modulo",
                    kwargs={"empresa_id": empresa_id, "conta_id": conta.get("id")},
                ),
            }
        )
    return resultado


def build_orcamento_tabulator(orcamentos_qs, empresa_id: int):
    resultado = []
    for item in orcamentos_qs:
        data_vencimento = item.get("data_vencimento")
        data_baixa = item.get("data_baixa")
        centro_resultado_descricao = (item.get("centro_resultado__descricao") or "").strip()
        if centro_resultado_descricao and not any(ch.isalpha() for ch in centro_resultado_descricao):
            centro_resultado_descricao = ""
        resultado.append(
            {
                "id": item.get("id"),
                "nome_empresa": item.get("nome_empresa") or "",
                "data_vencimento": _fmt_date_br(data_vencimento),
                "data_vencimento_iso": data_vencimento.strftime("%Y-%m-%d") if data_vencimento else "",
                "data_baixa": _fmt_date_br(data_baixa),
                "data_baixa_iso": data_baixa.strftime("%Y-%m-%d") if data_baixa else "",
                "valor_baixa": float(item.get("valor_baixa_num") or 0),
                "valor_liquido": float(item.get("valor_liquido_num") or 0),
                "valor_desdobramento": float(item.get("valor_desdobramento_num") or 0),
                "titulo_descricao": item.get("titulo__descricao") or "",
                "natureza_descricao": item.get("natureza__descricao") or "",
                "centro_resultado_descricao": centro_resultado_descricao,
                "operacao_descricao": item.get("operacao__descricao_receita_despesa") or "",
                "parceiro_codigo": item.get("parceiro__codigo") or "",
                "parceiro_nome": item.get("parceiro__nome") or "",
                "editar_url": reverse(
                    "editar_orcamento_modulo",
                    kwargs={"empresa_id": empresa_id, "orcamento_id": item.get("id")},
                ),
            }
        )
    return resultado


def build_orcamentos_planejados_tabulator(orcamentos_qs, empresa_id: int):
    resultado = []
    for item in orcamentos_qs:
        valores = {
            "janeiro": float(item.get("janeiro_num") or 0),
            "fevereiro": float(item.get("fevereiro_num") or 0),
            "marco": float(item.get("marco_num") or 0),
            "abril": float(item.get("abril_num") or 0),
            "maio": float(item.get("maio_num") or 0),
            "junho": float(item.get("junho_num") or 0),
            "julho": float(item.get("julho_num") or 0),
            "agosto": float(item.get("agosto_num") or 0),
            "setembro": float(item.get("setembro_num") or 0),
            "outubro": float(item.get("outubro_num") or 0),
            "novembro": float(item.get("novembro_num") or 0),
            "dezembro": float(item.get("dezembro_num") or 0),
        }
        resultado.append(
            {
                "id": item.get("id"),
                "centro_resultado_descricao": item.get("centro_resultado__descricao") or "",
                "natureza_descricao": item.get("natureza__descricao") or "",
                "nome_empresa": item.get("nome_empresa") or "",
                "ano": item.get("ano") or "",
                **valores,
                "total": sum(valores.values()),
                "editar_url": reverse(
                    "editar_orcamento_planejado_modulo",
                    kwargs={"empresa_id": empresa_id, "orcamento_planejado_id": item.get("id")},
                ),
            }
        )
    return resultado


def build_orcamento_x_realizado_tabulator(orcamentos_realizados_qs, orcamentos_planejados_qs):
    meses = [
        ("janeiro", 1),
        ("fevereiro", 2),
        ("marco", 3),
        ("abril", 4),
        ("maio", 5),
        ("junho", 6),
        ("julho", 7),
        ("agosto", 8),
        ("setembro", 9),
        ("outubro", 10),
        ("novembro", 11),
        ("dezembro", 12),
    ]
    mes_por_numero = {numero: campo for campo, numero in meses}

    def _chave_texto(valor, padrao):
        texto = (valor or "").strip()
        return texto if texto else padrao

    def _novo_bucket():
        return {
            "meses": {campo: {"real": 0.0, "orcamento": 0.0} for campo, _numero in meses},
            "naturezas": {},
        }

    centros = {}

    for item in orcamentos_planejados_qs:
        centro = _chave_texto(item.get("centro_resultado__descricao"), "<SEM CENTRO DE RESULTADO>")
        natureza = _chave_texto(item.get("natureza__descricao"), "<SEM NATUREZA>")

        centro_bucket = centros.setdefault(centro, _novo_bucket())
        natureza_bucket = centro_bucket["naturezas"].setdefault(
            natureza,
            {"meses": {campo: {"real": 0.0, "orcamento": 0.0} for campo, _numero in meses}},
        )

        for campo_mes, _numero in meses:
            valor_orcamento = float(item.get(f"{campo_mes}_num") or 0)
            centro_bucket["meses"][campo_mes]["orcamento"] += valor_orcamento
            natureza_bucket["meses"][campo_mes]["orcamento"] += valor_orcamento

    for item in orcamentos_realizados_qs:
        data_baixa = item.get("data_baixa")
        if not data_baixa:
            continue
        campo_mes = mes_por_numero.get(data_baixa.month)
        if not campo_mes:
            continue

        centro = _chave_texto(item.get("centro_resultado__descricao"), "<SEM CENTRO DE RESULTADO>")
        natureza = _chave_texto(item.get("natureza__descricao"), "<SEM NATUREZA>")
        valor_real = float(item.get("valor_baixa_num") or 0)

        centro_bucket = centros.setdefault(centro, _novo_bucket())
        natureza_bucket = centro_bucket["naturezas"].setdefault(
            natureza,
            {"meses": {campo: {"real": 0.0, "orcamento": 0.0} for campo, _numero in meses}},
        )

        centro_bucket["meses"][campo_mes]["real"] += valor_real
        natureza_bucket["meses"][campo_mes]["real"] += valor_real

    def _calc_desvio(real, orcamento):
        if orcamento == 0:
            return 0.0, "0,00%"
        valor = ((real - orcamento) / orcamento) * 100
        return valor, f"{valor:.2f}%".replace(".", ",")

    def _serializar_linha(descricao, meses_bucket, tipo_linha):
        linha = {
            "descricao": descricao,
            "tipo_linha": tipo_linha,
        }
        total_real = 0.0
        total_orcamento = 0.0
        for campo_mes, _numero in meses:
            real = float(meses_bucket[campo_mes]["real"])
            orcamento = float(meses_bucket[campo_mes]["orcamento"])
            desvio_num, desvio_label = _calc_desvio(real, orcamento)
            linha[f"{campo_mes}_real"] = real
            linha[f"{campo_mes}_orcamento"] = orcamento
            linha[f"{campo_mes}_desvio"] = desvio_num
            linha[f"{campo_mes}_desvio_label"] = desvio_label
            total_real += real
            total_orcamento += orcamento

        total_desvio_num, total_desvio_label = _calc_desvio(total_real, total_orcamento)
        linha["total_real"] = total_real
        linha["total_orcamento"] = total_orcamento
        linha["total_desvio"] = total_desvio_num
        linha["total_desvio_label"] = total_desvio_label
        return linha

    linhas = []
    grand_total_bucket = {campo: {"real": 0.0, "orcamento": 0.0} for campo, _numero in meses}

    for centro_nome in sorted(centros.keys()):
        centro_bucket = centros[centro_nome]
        linha_centro = _serializar_linha(centro_nome, centro_bucket["meses"], "centro")
        filhos = []
        for natureza_nome in sorted(centro_bucket["naturezas"].keys()):
            natureza_bucket = centro_bucket["naturezas"][natureza_nome]
            filhos.append(_serializar_linha(natureza_nome, natureza_bucket["meses"], "natureza"))

        linha_centro["_children"] = filhos
        linhas.append(linha_centro)

        for campo_mes, _numero in meses:
            grand_total_bucket[campo_mes]["real"] += centro_bucket["meses"][campo_mes]["real"]
            grand_total_bucket[campo_mes]["orcamento"] += centro_bucket["meses"][campo_mes]["orcamento"]

    linha_grand_total = _serializar_linha("Grand Total", grand_total_bucket, "grand_total")
    linha_grand_total["is_grand_total"] = True
    linhas.append(linha_grand_total)

    return linhas
