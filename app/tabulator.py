from __future__ import annotations

from django.urls import reverse


def _fmt_date_br(data):
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")


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
