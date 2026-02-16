from __future__ import annotations

from django.urls import reverse


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
                "nome_parceiro": carteira_item.get("nome_parceiro") or "",
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
