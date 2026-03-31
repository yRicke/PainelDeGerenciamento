from __future__ import annotations

from django.urls import reverse
from django.utils import timezone


def _fmt_date_br(data):
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")


def _fmt_datetime_br(data):
    if not data:
        return ""
    return data.strftime("%d/%m/%Y %H:%M")


def _normalizar_numero_unico_texto(valor):
    texto = (str(valor or "")).strip()
    if not texto:
        return ""
    if texto.endswith(".0"):
        texto = texto[:-2]
    texto = texto.replace(" ", "")
    if texto.isdigit():
        return str(int(texto))
    return texto


def _gerente_valido_ou_vazio(valor):
    texto = (str(valor or "")).strip()
    if not texto:
        return ""
    if texto.upper() in {"<SEM VENDEDOR>", "SEM VENDEDOR", "<SEM GERENTE>", "SEM GERENTE"}:
        return ""
    return texto


def _situacao_margem(margem):
    try:
        valor = float(margem)
    except (TypeError, ValueError):
        valor = 0.0

    if valor < 10:
        return "Roxo"
    if valor < 12:
        return "Vermelho"
    if valor < 14:
        return "Amarelo"
    return "Verde"


def build_atividades_tabulator(atividades_qs, empresa_id: int, usuario_logado=None):
    resultado = []
    for atividade in atividades_qs:
        item = {
            "id": atividade.id,
            "projeto": atividade.projeto.nome,
            "codigo_projeto": atividade.projeto.codigo or "-",
            "criada_por": atividade.usuario.username if atividade.usuario else "-",
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
        }
        if atividade.pode_ser_editada_por(usuario_logado):
            item["editar_url"] = reverse(
                "editar_atividade_tofu",
                kwargs={"empresa_id": empresa_id, "atividade_id": atividade.id},
            )
        resultado.append(item)
    return resultado


def build_carteiras_tabulator(carteiras_qs, empresa_id: int, permitir_edicao: bool = True):
    hoje = timezone.localdate()
    intervalo_labels = {
        "sem_venda": "Sem venda",
        "0_5": "0 a 5",
        "6_30": "6 a 30",
        "31_60": "31 a 60",
        "61_90": "61 a 90",
        "91_120": "91 a 120",
        "121_180": "121 a 180",
        "180_mais": "180+",
    }

    def _dias_sem_venda(ultima_venda):
        if not ultima_venda:
            return intervalo_labels["sem_venda"]
        dias = (hoje - ultima_venda).days
        return max(0, int(dias))

    def _intervalo_carteira(dias_sem_venda):
        if isinstance(dias_sem_venda, str):
            return intervalo_labels["sem_venda"]
        if dias_sem_venda <= 5:
            return intervalo_labels["0_5"]
        if dias_sem_venda <= 30:
            return intervalo_labels["6_30"]
        if dias_sem_venda <= 60:
            return intervalo_labels["31_60"]
        if dias_sem_venda <= 90:
            return intervalo_labels["61_90"]
        if dias_sem_venda <= 120:
            return intervalo_labels["91_120"]
        if dias_sem_venda <= 180:
            return intervalo_labels["121_180"]
        return intervalo_labels["180_mais"]

    resultado = []
    for carteira_item in carteiras_qs:
        data_cadastro = carteira_item.get("data_cadastro")
        dias_sem_venda = _dias_sem_venda(carteira_item.get("ultima_venda"))
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
                "qtd_dias_sem_venda": dias_sem_venda,
                "intervalo": _intervalo_carteira(dias_sem_venda),
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
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_carteira_modulo",
                kwargs={"empresa_id": empresa_id, "carteira_id": carteira_item.get("id")},
            )
    return resultado


def build_vendas_tabulator(vendas_qs, empresa_id: int, permitir_edicao: bool = True):
    from .models import Produto

    vendas = list(vendas_qs)
    codigos = {
        (item.get("codigo") or "").strip()
        for item in vendas
        if (item.get("codigo") or "").strip()
    }
    produtos_por_codigo = {}
    if codigos:
        produtos_por_codigo = {
            item["codigo_produto"]: {
                "kg": float(item.get("kg") or 0),
                "remuneracao_por_fardo": float(item.get("remuneracao_por_fardo") or 0),
            }
            for item in Produto.objects.filter(
                empresa_id=empresa_id,
                codigo_produto__in=codigos,
            ).values("codigo_produto", "kg", "remuneracao_por_fardo")
        }

    resultado = []
    for venda in vendas:
        codigo = (venda.get("codigo") or "").strip()
        produto = produtos_por_codigo.get(codigo) or {}
        kg = float(produto.get("kg") or 0)
        remuneracao_por_fardo = float(produto.get("remuneracao_por_fardo") or 0)
        peso_liquido = float(venda.get("peso_liquido_num") or 0)
        quantidade_fardos = (peso_liquido / kg) if kg > 0 else 0
        remuneracao_total = quantidade_fardos * remuneracao_por_fardo
        data_venda = venda.get("data_venda")
        margem_num = float(venda.get("margem_num") or 0)
        resultado.append(
            {
                "id": venda.get("id"),
                "codigo": codigo,
                "descricao": venda.get("descricao") or "",
                "valor_venda": float(venda.get("valor_venda_num") or 0),
                "qtd_notas": venda.get("qtd_notas") or 0,
                "custo_medio_icms_cmv": float(venda.get("custo_medio_icms_cmv_num") or 0),
                "lucro": float(venda.get("lucro_num") or 0),
                "peso_bruto": float(venda.get("peso_bruto_num") or 0),
                "peso_liquido": peso_liquido,
                "margem": margem_num,
                "margem_situacao": _situacao_margem(margem_num),
                "kg": kg,
                "remuneracao_por_fardo": remuneracao_por_fardo,
                "quantidade_fardos": quantidade_fardos,
                "remuneracao_total": remuneracao_total,
                "data_venda": _fmt_date_br(data_venda),
                "data_venda_iso": data_venda.strftime("%Y-%m-%d") if data_venda else "",
                "ano_venda": data_venda.year if data_venda else "",
                "mes_venda": data_venda.month if data_venda else "",
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_venda_modulo",
                kwargs={"empresa_id": empresa_id, "venda_id": venda.get("id")},
            )
    return resultado


def build_pedidos_pendentes_tabulator(
    pedidos_qs,
    empresa_id: int,
    agendas_por_numero=None,
    gerentes_por_parceiro=None,
    permitir_edicao: bool = True,
):
    agendas_por_numero = agendas_por_numero or {}
    gerentes_por_parceiro = gerentes_por_parceiro or {}
    resultado = []

    for item in pedidos_qs:
        data_para_calculo = item.data_para_calculo or item.previsao_entrega or item.dt_neg
        dias_negociados = (timezone.localdate() - data_para_calculo).days if data_para_calculo else ""
        if data_para_calculo is None:
            status = ""
        else:
            saldo_prazo = int(item.prazo_maximo or 0) - int(dias_negociados)
            if saldo_prazo < 0:
                status = "Atrasado"
            elif saldo_prazo == 0:
                status = "Atenção"
            else:
                status = "No Prazo"

        chave_numero = _normalizar_numero_unico_texto(item.numero_unico)
        agenda_item = agendas_por_numero.get(chave_numero) or agendas_por_numero.get(str(item.numero_unico or "").strip())
        gerente = _gerente_valido_ou_vazio(item.gerente) or gerentes_por_parceiro.get(item.parceiro_id, "")

        resultado.append(
            {
                "id": item.id,
                "numero_unico": item.numero_unico or "",
                "rota": item.rota_texto or (f"{item.rota.codigo_rota} - {item.rota.nome}" if item.rota else ""),
                "regiao": item.regiao_texto or (f"{item.regiao.codigo} - {item.regiao.nome}" if item.regiao else ""),
                "valor_tonelada_frete_safia": item.valor_tonelada_frete_safia or "",
                "pendente": item.pendente or "",
                "nome_cidade_parceiro_safia": item.nome_cidade_parceiro_safia or "",
                "previsao_entrega": _fmt_date_br(item.previsao_entrega),
                "previsao_entrega_iso": item.previsao_entrega.strftime("%Y-%m-%d") if item.previsao_entrega else "",
                "dt_neg": _fmt_date_br(item.dt_neg),
                "dt_neg_iso": item.dt_neg.strftime("%Y-%m-%d") if item.dt_neg else "",
                "prazo_maximo": int(item.prazo_maximo or 0),
                "dias_negociados": dias_negociados,
                "status": status,
                "tipo_venda": item.tipo_venda or "",
                "nome_empresa": item.nome_empresa or "",
                "cod_nome_parceiro": item.cod_nome_parceiro or "",
                "vlr_nota": float(item.vlr_nota or 0),
                "peso_bruto": float(item.peso_bruto or 0),
                "peso": float(item.peso or 0),
                "peso_liq_itens": float(item.peso_liq_itens or 0),
                "apelido_vendedor": item.apelido_vendedor or "",
                "gerente": gerente or "",
                "data_para_calculo": _fmt_date_br(data_para_calculo),
                "data_para_calculo_iso": data_para_calculo.strftime("%Y-%m-%d") if data_para_calculo else "",
                "descricao_tipo_negociacao": item.descricao_tipo_negociacao or "",
                "nro_nota": int(item.nro_nota or 0),
                "previsao_do_carregamento": _fmt_date_br(agenda_item.previsao_carregamento) if agenda_item else "",
                "motorista": agenda_item.motorista.nome if agenda_item and agenda_item.motorista else "",
                "transportadora": agenda_item.transportadora.nome if agenda_item and agenda_item.transportadora else "",
                "agenda_base_url": reverse("agenda", kwargs={"empresa_id": empresa_id}),
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_pedido_pendente_modulo",
                kwargs={"empresa_id": empresa_id, "pedido_id": item.id},
            )
    return resultado


def build_controle_margem_tabulator(controles_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in controles_qs:
        resultado.append(
            {
                "id": item.id,
                "data_origem": item.data_origem or "",
                "nro_unico": int(item.nro_unico or 0),
                "nome_empresa": item.nome_empresa or "",
                "cod_nome_parceiro": item.cod_nome_parceiro or "",
                "descricao_perfil": item.descricao_perfil or "",
                "apelido_vendedor": item.apelido_vendedor or "",
                "gerente": item.gerente or "",
                "dt_neg": _fmt_date_br(item.dt_neg),
                "previsao_entrega": _fmt_date_br(item.previsao_entrega),
                "tipo_venda": item.tipo_venda or "",
                "vlr_nota": float(item.vlr_nota or 0),
                "custo_total_produto": float(item.custo_total_produto or 0),
                "margem_bruta": float(item.margem_bruta or 0),
                "lucro_bruto": float(item.lucro_bruto or 0),
                "valor_tonelada_frete_safia": float(item.valor_tonelada_frete_safia or 0),
                "peso_bruto": float(item.peso_bruto or 0),
                "custo_por_kg": float(item.custo_por_kg or 0),
                "vendas": float(item.vendas or 0),
                "producao": float(item.producao or 0),
                "operador_logistica": float(item.operador_logistica or 0),
                "frete_distribuicao": float(item.frete_distribuicao or 0),
                "total_logistica": float(item.total_logistica or 0),
                "administracao": float(item.administracao or 0),
                "financeiro": float(item.financeiro or 0),
                "total_setores": float(item.total_setores or 0),
                "valor_liquido": float(item.valor_liquido or 0),
                "margem_liquida": float(item.margem_liquida or 0),
                "situacao": item.situacao or "",
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_controle_margem_modulo",
                kwargs={"empresa_id": empresa_id, "controle_id": item.id},
            )
    return resultado


def build_cargas_tabulator(cargas_qs, empresa_id: int, permitir_edicao: bool = True):
    def _normalizar_status(valor):
        texto = (str(valor or "")).strip().lower()
        if texto in {"aberta", "em aberto"}:
            return "aberta"
        if texto in {"fechada", "encerrada"}:
            return "fechada"
        return texto

    resultado = []
    for carga in cargas_qs:
        status = "Fechada" if carga.data_finalizacao else "Aberta"
        situacao = carga.situacao or ""
        verificacao_texto = (
            "Ok"
            if _normalizar_status(status) == _normalizar_status(situacao)
            else "Verificar"
        )
        resultado.append(
            {
                "id": carga.id,
                "situacao": situacao,
                "status": status,
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
                "verificacao_texto": verificacao_texto,
                "critica": carga.critica,
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_carga_modulo",
                kwargs={"empresa_id": empresa_id, "carga_id": carga.id},
            )
    return resultado


def build_producao_tabulator(producoes_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in producoes_qs:
        entrada_atividade = item.data_hora_entrada_atividade
        resultado.append(
            {
                "id": item.id,
                "data_origem": item.data_origem or "",
                "numero_operacao": item.numero_operacao or 0,
                "situacao": item.situacao or "",
                "produto_codigo": item.produto.codigo_produto if item.produto else "",
                "produto_descricao": item.produto.descricao_produto if item.produto else "",
                "tamanho_lote": item.tamanho_lote or "",
                "numero_lote": item.numero_lote or "",
                "data_hora_entrada_atividade": _fmt_datetime_br(entrada_atividade),
                "data_hora_entrada_atividade_iso": (
                    entrada_atividade.strftime("%Y-%m-%d")
                    if entrada_atividade
                    else ""
                ),
                "data_hora_aceite_atividade": _fmt_datetime_br(item.data_hora_aceite_atividade),
                "data_hora_inicio_atividade": _fmt_datetime_br(item.data_hora_inicio_atividade),
                "data_hora_fim_atividade": _fmt_datetime_br(item.data_hora_fim_atividade),
                "kg": float(item.kg or 0),
                "producao_por_dia": float(item.producao_por_dia or 0),
                "kg_por_lote": float(item.kg_por_lote or 0),
                "pacote_por_fardo_parametro": float(item.produto.pacote_por_fardo or 0) if item.produto else 0,
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_producao_modulo",
                kwargs={"empresa_id": empresa_id, "producao_id": item.id},
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


def build_plano_cargos_salarios_tabulator(planos_qs, empresa_id: int):
    resultado = []
    for item in planos_qs:
        resultado.append(
            {
                "id": item.id,
                "cadastro": item.cadastro,
                "funcionario": item.funcionario or "",
                "contrato": item.contrato or "",
                "genero": item.genero or "",
                "setor": item.setor or "",
                "cargo": item.cargo or "",
                "novo_cargo": item.novo_cargo or "",
                "data_admissao": _fmt_date_br(item.data_admissao),
                "data_admissao_iso": item.data_admissao.strftime("%Y-%m-%d") if item.data_admissao else "",
                "salario_carteira": float(item.salario_carteira) if item.salario_carteira is not None else None,
                "piso_categoria": float(item.piso_categoria) if item.piso_categoria is not None else None,
                "jr": float(item.jr) if item.jr is not None else None,
                "pleno": float(item.pleno) if item.pleno is not None else None,
                "senior": float(item.senior) if item.senior is not None else None,
                "editar_url": reverse(
                    "editar_plano_cargo_salario_modulo",
                    kwargs={"empresa_id": empresa_id, "plano_cargo_salario_id": item.id},
                ),
                "excluir_url": reverse(
                    "excluir_plano_cargo_salario_modulo",
                    kwargs={"empresa_id": empresa_id, "plano_cargo_salario_id": item.id},
                ),
            }
        )
    return resultado


def build_descritivo_tabulator_item(item, empresa_id: int):
    return {
        "id": item.id,
        "inicio": item.inicio.strftime("%H:%M") if item.inicio else "",
        "termino": item.termino.strftime("%H:%M") if item.termino else "",
        "contas_a_pagar": item.contas_a_pagar or "",
        "contas_a_receber": item.contas_a_receber or "",
        "supervisor_financeiro": item.supervisor_financeiro or "",
        "faturamento": item.faturamento or "",
        "supervisor_logistica": item.supervisor_logistica or "",
        "conferente": item.conferente or "",
        "gerente_de_producao": item.gerente_de_producao or "",
        "gerente_cml": item.gerente_cml or "",
        "assistente_comercial": item.assistente_comercial or "",
        "diretor": item.diretor or "",
        "editar_url": reverse(
            "editar_descritivo_modulo",
            kwargs={"empresa_id": empresa_id, "descritivo_id": item.id},
        ),
        "excluir_url": reverse(
            "excluir_descritivo_modulo",
            kwargs={"empresa_id": empresa_id, "descritivo_id": item.id},
        ),
    }


def build_descritivos_tabulator(descritivos_qs, empresa_id: int):
    return [build_descritivo_tabulator_item(item, empresa_id) for item in descritivos_qs]


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


def build_rotas_tabulator(rotas_qs, empresa_id: int):
    return [
        {
            "id": rota.id,
            "codigo_rota": rota.codigo_rota,
            "nome": rota.nome,
            "uf_id": rota.uf_id or "",
            "uf_sigla": rota.uf.sigla if rota.uf else "",
            "editar_url": reverse(
                "editar_rota_modulo",
                kwargs={"empresa_id": empresa_id, "rota_id": rota.id},
            ),
            "excluir_url": reverse(
                "excluir_rota_modulo",
                kwargs={"empresa_id": empresa_id, "rota_id": rota.id},
            ),
        }
        for rota in rotas_qs
    ]


def build_unidades_federativas_tabulator(unidades_qs, empresa_id: int):
    return [
        {
            "id": unidade.id,
            "codigo": unidade.codigo,
            "sigla": unidade.sigla,
            "editar_url": reverse(
                "editar_unidade_federativa_modulo",
                kwargs={"empresa_id": empresa_id, "unidade_federativa_id": unidade.id},
            ),
            "excluir_url": reverse(
                "excluir_unidade_federativa_modulo",
                kwargs={"empresa_id": empresa_id, "unidade_federativa_id": unidade.id},
            ),
        }
        for unidade in unidades_qs
    ]


def build_parceiros_tabulator(parceiros_qs, empresa_id: int):
    return [
        {
            "id": parceiro.id,
            "nome": parceiro.nome,
            "codigo": parceiro.codigo,
            "cidade_id": parceiro.cidade_id or "",
            "cidade_nome": parceiro.cidade.nome if parceiro.cidade else "",
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


def build_contas_bancarias_tabulator(contas_qs, empresa_id: int):
    return [
        {
            "id": conta.id,
            "agencia": conta.agencia,
            "numero_conta": conta.numero_conta,
            "banco_id": conta.banco_id,
            "banco_nome": conta.banco.nome if conta.banco_id else "",
            "empresa_titular_id": conta.empresa_titular_id,
            "empresa_titular_label": (
                f"{conta.empresa_titular.codigo} - {conta.empresa_titular.nome}"
                if conta.empresa_titular_id
                else ""
            ),
            "editar_url": reverse(
                "editar_conta_bancaria_modulo",
                kwargs={"empresa_id": empresa_id, "conta_bancaria_id": conta.id},
            ),
            "excluir_url": reverse(
                "excluir_conta_bancaria_modulo",
                kwargs={"empresa_id": empresa_id, "conta_bancaria_id": conta.id},
            ),
        }
        for conta in contas_qs
    ]


def build_bancos_tabulator(bancos_qs, empresa_id: int):
    return [
        {
            "id": banco.id,
            "nome": banco.nome or "",
            "editar_url": reverse(
                "editar_banco_modulo",
                kwargs={"empresa_id": empresa_id, "banco_id": banco.id},
            ),
            "excluir_url": reverse(
                "excluir_banco_modulo",
                kwargs={"empresa_id": empresa_id, "banco_id": banco.id},
            ),
        }
        for banco in bancos_qs
    ]


def build_empresas_titulares_tabulator(empresas_titulares_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "codigo": item.codigo,
            "nome": item.nome,
            "editar_url": reverse(
                "editar_empresa_titular_modulo",
                kwargs={"empresa_id": empresa_id, "empresa_titular_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_empresa_titular_modulo",
                kwargs={"empresa_id": empresa_id, "empresa_titular_id": item.id},
            ),
        }
        for item in empresas_titulares_qs
    ]


def build_motoristas_tabulator(motoristas_qs, empresa_id: int):
    return [
        {
            "id": motorista.id,
            "codigo_motorista": motorista.codigo_motorista,
            "nome": motorista.nome,
            "editar_url": reverse(
                "editar_motorista_modulo",
                kwargs={"empresa_id": empresa_id, "motorista_id": motorista.id},
            ),
            "excluir_url": reverse(
                "excluir_motorista_modulo",
                kwargs={"empresa_id": empresa_id, "motorista_id": motorista.id},
            ),
        }
        for motorista in motoristas_qs
    ]


def build_transportadoras_tabulator(transportadoras_qs, empresa_id: int):
    return [
        {
            "id": transportadora.id,
            "codigo_transportadora": transportadora.codigo_transportadora,
            "nome": transportadora.nome,
            "editar_url": reverse(
                "editar_transportadora_modulo",
                kwargs={"empresa_id": empresa_id, "transportadora_id": transportadora.id},
            ),
            "excluir_url": reverse(
                "excluir_transportadora_modulo",
                kwargs={"empresa_id": empresa_id, "transportadora_id": transportadora.id},
            ),
        }
        for transportadora in transportadoras_qs
    ]


def build_descricoes_perfil_tabulator(descricoes_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "descricao": item.descricao or "",
            "editar_url": reverse(
                "editar_descricao_perfil_modulo",
                kwargs={"empresa_id": empresa_id, "descricao_perfil_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_descricao_perfil_modulo",
                kwargs={"empresa_id": empresa_id, "descricao_perfil_id": item.id},
            ),
        }
        for item in descricoes_qs
    ]


def build_parametros_metas_tabulator(parametros_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "descricao_perfil_id": item.descricao_perfil_id or "",
            "descricao_perfil_descricao": item.descricao_perfil.descricao if item.descricao_perfil else "",
            "meta_acabado_percentual": (
                float(item.meta_acabado_percentual) if item.meta_acabado_percentual is not None else None
            ),
            "valor_meta_pd_acabado": (
                float(item.valor_meta_pd_acabado) if item.valor_meta_pd_acabado is not None else None
            ),
            "meta_mt_prima_percentual": (
                float(item.meta_mt_prima_percentual) if item.meta_mt_prima_percentual is not None else None
            ),
            "editar_url": reverse(
                "editar_parametro_meta_modulo",
                kwargs={"empresa_id": empresa_id, "parametro_meta_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_parametro_meta_modulo",
                kwargs={"empresa_id": empresa_id, "parametro_meta_id": item.id},
            ),
        }
        for item in parametros_qs
    ]


def build_agenda_tabulator(agenda_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "data_registro": _fmt_date_br(item.data_registro),
            "data_registro_iso": item.data_registro.strftime("%Y-%m-%d") if item.data_registro else "",
            "numero_unico": item.numero_unico or "",
            "previsao_carregamento": _fmt_date_br(item.previsao_carregamento),
            "previsao_carregamento_iso": (
                item.previsao_carregamento.strftime("%Y-%m-%d")
                if item.previsao_carregamento
                else ""
            ),
            "motorista_id": item.motorista_id or "",
            "motorista_nome": item.motorista.nome if item.motorista else "",
            "transportadora_id": item.transportadora_id or "",
            "transportadora_nome": item.transportadora.nome if item.transportadora else "",
            "editar_url": reverse(
                "editar_agenda_modulo",
                kwargs={"empresa_id": empresa_id, "agenda_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_agenda_modulo",
                kwargs={"empresa_id": empresa_id, "agenda_id": item.id},
            ),
        }
        for item in agenda_qs
    ]


def build_produtos_tabulator(produtos_qs, empresa_id: int):
    return [
        {
            "id": produto.id,
            "codigo_produto": produto.codigo_produto,
            "status": produto.status or "Ativo",
            "descricao_produto": produto.descricao_produto or "",
            "kg": float(produto.kg or 0),
            "remuneracao_por_fardo": float(produto.remuneracao_por_fardo or 0),
            "ppm": float(produto.ppm or 0),
            "peso_kg": float(produto.peso_kg or 0),
            "pacote_por_fardo": float(produto.pacote_por_fardo or 0),
            "turno": float(produto.turno or 0),
            "horas": float(produto.horas or 0),
            "setup": float(produto.setup or 0),
            "horas_uteis": float(produto.horas_uteis or 0),
            "empacotadeiras": float(produto.empacotadeiras or 0),
            "producao_por_dia_fd": float(produto.producao_por_dia_fd or 0),
            "estoque_minimo_pacote": float(produto.estoque_minimo_pacote or 0),
            "editar_url": reverse(
                "editar_produto_modulo",
                kwargs={"empresa_id": empresa_id, "produto_id": produto.id},
            ),
            "excluir_url": reverse(
                "excluir_produto_modulo",
                kwargs={"empresa_id": empresa_id, "produto_id": produto.id},
            ),
        }
        for produto in produtos_qs
    ]


def build_fretes_tabulator(fretes_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in fretes_qs:
        resultado.append(
            {
                "id": item.id,
                "cidade_codigo": item.cidade.codigo if item.cidade else "",
                "cidade_nome": item.cidade.nome if item.cidade else "",
                "unidade_federativa_codigo": item.unidade_federativa.codigo if item.unidade_federativa else "",
                "unidade_federativa_sigla": item.unidade_federativa.sigla if item.unidade_federativa else "",
                "regiao_codigo": item.regiao.codigo if item.regiao else "",
                "regiao_nome": item.regiao.nome if item.regiao else "",
                "valor_frete_comercial": float(item.valor_frete_comercial or 0),
                "data_hora_alteracao": _fmt_datetime_br(item.data_hora_alteracao),
                "data_hora_alteracao_iso": (
                    item.data_hora_alteracao.strftime("%Y-%m-%dT%H:%M")
                    if item.data_hora_alteracao
                    else ""
                ),
                "valor_frete_minimo": float(item.valor_frete_minimo or 0),
                "valor_frete_tonelada": float(item.valor_frete_tonelada or 0),
                "tipo_frete": item.tipo_frete or "",
                "valor_frete_por_km": float(item.valor_frete_por_km or 0),
                "valor_taxa_entrada": float(item.valor_taxa_entrada or 0),
                "venda_minima": float(item.venda_minima or 0),
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_frete_modulo",
                kwargs={"empresa_id": empresa_id, "frete_id": item.id},
            )
    return resultado


def build_estoque_tabulator(estoques_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in estoques_qs:
        resultado.append(
            {
                "id": item.id,
                "nome_origem": _fmt_date_br(item.nome_origem),
                "nome_origem_iso": item.nome_origem.strftime("%Y-%m-%d") if item.nome_origem else "",
                "data_contagem": _fmt_date_br(item.data_contagem),
                "data_contagem_iso": item.data_contagem.strftime("%Y-%m-%d") if item.data_contagem else "",
                "status": item.status or "",
                "codigo_empresa": item.codigo_empresa or "",
                "produto_codigo": item.produto.codigo_produto if item.produto else "",
                "produto_descricao": item.produto.descricao_produto if item.produto else "",
                "qtd_estoque": float(item.qtd_estoque or 0),
                "giro_mensal": float(item.giro_mensal or 0),
                "lead_time_fornecimento": float(item.lead_time_fornecimento or 0),
                "codigo_volume": item.codigo_volume or "",
                "custo_total": float(item.custo_total or 0),
                "reservado": float(item.reservado or 0),
                "pacote_por_fardo": float(item.pacote_por_fardo or 0),
                "sub_total_est_pen": float(item.sub_total_est_pen or 0),
                "estoque_minimo": float(item.estoque_minimo or 0),
                "producao_por_dia_fd": float(item.producao_por_dia_fd or 0),
                "total_pcp_pacote": float(item.total_pcp_pacote or 0),
                "total_pcp_fardo": float(item.total_pcp_fardo or 0),
                "dia_de_producao": float(item.dia_de_producao or 0),
                "codigo_local": item.codigo_local or "",
                "ano_contagem": item.data_contagem.year if item.data_contagem else "",
                "mes_contagem": item.data_contagem.month if item.data_contagem else "",
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_estoque_modulo",
                kwargs={"empresa_id": empresa_id, "estoque_id": item.id},
            )
    return resultado


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


def build_contratos_redes_tabulator(contratos_qs, empresa_id: int):
    return [
        {
            "id": contrato.id,
            "codigo_registro": contrato.codigo_registro,
            "numero_contrato": contrato.numero_contrato,
            "data_inicio": contrato.data_inicio.strftime("%Y-%m-%d") if contrato.data_inicio else "",
            "data_encerramento": contrato.data_encerramento.strftime("%Y-%m-%d") if contrato.data_encerramento else "",
            "parceiro_id": contrato.parceiro_id or "",
            "parceiro_codigo": contrato.parceiro.codigo if contrato.parceiro else "",
            "parceiro_nome": contrato.parceiro.nome if contrato.parceiro else "",
            "descricao_acordos": contrato.descricao_acordos or "",
            "valor_acordo": float(contrato.valor_acordo or 0),
            "status_contrato": contrato.status_contrato or "Ativo",
            "editar_url": reverse(
                "editar_contrato_rede_modulo",
                kwargs={"empresa_id": empresa_id, "contrato_id": contrato.id},
            ),
            "excluir_url": reverse(
                "excluir_contrato_rede_modulo",
                kwargs={"empresa_id": empresa_id, "contrato_id": contrato.id},
            ),
        }
        for contrato in contratos_qs
    ]


def build_parametros_margem_vendas_tabulator(parametros_qs, empresa_id: int):
    acao_url = reverse("parametros_vendas", kwargs={"empresa_id": empresa_id})
    return [
        {
            "id": item.id,
            "parametro": item.parametro or "",
            "criterio": item.criterio or "",
            "remuneracao_percentual": float(item.remuneracao_percentual or 0),
            "acao_url": acao_url,
        }
        for item in parametros_qs
    ]


def build_parametros_margem_logistica_tabulator(parametros_qs, empresa_id: int):
    acao_url = reverse("parametros_logistica", kwargs={"empresa_id": empresa_id})
    return [
        {
            "id": item.id,
            "parametro": item.parametro or "",
            "criterio": item.criterio or "",
            "remuneracao_rs": float(item.remuneracao_rs or 0),
            "acao_url": acao_url,
        }
        for item in parametros_qs
    ]


def build_parametros_margem_financeiro_tabulator(parametros_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "parametro": item.parametro or "",
            "taxa_ao_mes": float(item.taxa_ao_mes or 0),
            "remuneracao_percentual": float(item.remuneracao_percentual or 0),
            "editar_url": reverse(
                "editar_parametro_margem_financeiro_modulo",
                kwargs={"empresa_id": empresa_id, "parametro_financeiro_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_parametro_margem_financeiro_modulo",
                kwargs={"empresa_id": empresa_id, "parametro_financeiro_id": item.id},
            ),
        }
        for item in parametros_qs
    ]


def build_parametros_negocios_tabulator(parametros_qs, empresa_id: int):
    acao_url = reverse("parametros_negocios", kwargs={"empresa_id": empresa_id})
    return [
        {
            "id": item.id,
            "direcao": item.direcao or "",
            "meta": float(item.meta or 0),
            "compromisso": float(item.compromisso or 0),
            "gerente_pa_e_outros": float(item.gerente_pa_e_outros or 0),
            "gerente_mp_e_gerente_luciano": float(item.gerente_mp_e_gerente_luciano or 0),
            "acao_url": acao_url,
        }
        for item in parametros_qs
    ]


def build_saldos_limites_tabulator(saldos_qs, empresa_id: int):
    return [
        {
            "id": item.id,
            "data": _fmt_date_br(item.data),
            "data_iso": item.data.isoformat() if item.data else "",
            "empresa_titular_id": item.empresa_titular_id,
            "empresa_titular_label": (
                f"{item.empresa_titular.codigo} - {item.empresa_titular.nome}"
                if item.empresa_titular_id
                else ""
            ),
            "conta_bancaria_id": item.conta_bancaria_id,
            "conta_label": (
                f"{item.conta_bancaria.agencia} / {item.conta_bancaria.numero_conta}"
                if item.conta_bancaria_id
                else ""
            ),
            "banco": item.conta_bancaria.banco.nome if item.conta_bancaria_id and item.conta_bancaria.banco_id else "",
            "tipo_movimentacao": item.tipo_movimentacao,
            "tipo_movimentacao_label": item.get_tipo_movimentacao_display(),
            "valor_atual": float(item.valor_atual or 0),
            "editar_url": reverse(
                "editar_saldo_limite_modulo",
                kwargs={"empresa_id": empresa_id, "saldo_limite_id": item.id},
            ),
            "excluir_url": reverse(
                "excluir_saldo_limite_modulo",
                kwargs={"empresa_id": empresa_id, "saldo_limite_id": item.id},
            ),
        }
        for item in saldos_qs
    ]


def build_comite_diario_tabulator(comites_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in comites_qs:
        row = {
            "id": item.id,
            "data_negociacao": _fmt_date_br(item.data_negociacao),
            "data_negociacao_iso": item.data_negociacao.isoformat() if item.data_negociacao else "",
            "data_vencimento": _fmt_date_br(item.data_vencimento),
            "data_vencimento_iso": item.data_vencimento.isoformat() if item.data_vencimento else "",
            "receita_despesa": item.receita_despesa,
            "receita_despesa_label": item.get_receita_despesa_display(),
            "empresa_titular_id": item.empresa_titular_id or "",
            "empresa_titular_label": (
                f"{item.empresa_titular.codigo} - {item.empresa_titular.nome}"
                if item.empresa_titular_id
                else ""
            ),
            "parceiro_id": item.parceiro_id or "",
            "parceiro_label": (
                f"{item.parceiro.codigo} - {item.parceiro.nome}"
                if item.parceiro_id
                else ""
            ),
            "natureza_id": item.natureza_id or "",
            "natureza_label": (
                f"{item.natureza.codigo} - {item.natureza.descricao}"
                if item.natureza_id
                else ""
            ),
            "centro_resultado_id": item.centro_resultado_id or "",
            "centro_resultado_label": item.centro_resultado.descricao if item.centro_resultado_id else "",
            "historico": item.historico or "",
            "numero_nota": item.numero_nota,
            "valor_liquido": float(item.valor_liquido or 0),
            "tipo_movimento": item.tipo_movimento,
            "tipo_movimento_label": item.get_tipo_movimento_display(),
            "decisao": item.decisao,
            "decisao_label": item.get_decisao_display(),
            "data_prorrogada": _fmt_date_br(item.data_prorrogada),
            "data_prorrogada_iso": item.data_prorrogada.isoformat() if item.data_prorrogada else "",
            "de_banco_id": item.de_banco_id or "",
            "de_banco_label": item.de_banco.nome if item.de_banco_id else "",
            "para_banco_id": item.para_banco_id or "",
            "para_banco_label": item.para_banco.nome if item.para_banco_id else "",
            "para_empresa_id": item.para_empresa_id or "",
            "para_empresa_label": (
                f"{item.para_empresa.codigo} - {item.para_empresa.nome}"
                if item.para_empresa_id
                else ""
            ),
        }
        if permitir_edicao:
            row["editar_url"] = reverse(
                "editar_comite_diario_modulo",
                kwargs={"empresa_id": empresa_id, "comite_diario_id": item.id},
            )
            row["excluir_url"] = reverse(
                "excluir_comite_diario_modulo",
                kwargs={"empresa_id": empresa_id, "comite_diario_id": item.id},
            )
        resultado.append(row)
    return resultado


def build_dfc_tabulator(dfc_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for dfc_item in dfc_qs:
        resultado.append(
            {
                "id": dfc_item.get("id"),
                "empresa_id": dfc_item.get("empresa_id") or "",
                "empresa_nome": dfc_item.get("empresa__nome") or "",
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
                "titulo_id": dfc_item.get("titulo_id") or "",
                "titulo_codigo": dfc_item.get("titulo__tipo_titulo_codigo") or "",
                "titulo_descricao": dfc_item.get("titulo__descricao") or "",
                "centro_resultado_id": dfc_item.get("centro_resultado_id") or "",
                "centro_resultado_descricao": dfc_item.get("centro_resultado__descricao") or "",
                "natureza_id": dfc_item.get("natureza_id") or "",
                "natureza_codigo": dfc_item.get("natureza__codigo") or "",
                "natureza_descricao": dfc_item.get("natureza__descricao") or "",
                "historico": dfc_item.get("historico") or "",
                "parceiro_id": dfc_item.get("parceiro_id") or "",
                "parceiro_codigo": dfc_item.get("parceiro__codigo") or "",
                "parceiro_nome": dfc_item.get("parceiro__nome") or "",
                "operacao_id": dfc_item.get("operacao_id") or "",
                "operacao_codigo": dfc_item.get("operacao__tipo_operacao_codigo") or "",
                "operacao_descricao": dfc_item.get("operacao__descricao_receita_despesa") or "",
                "tipo_movimento": dfc_item.get("tipo_movimento") or "",
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_dfc_modulo",
                kwargs={"empresa_id": empresa_id, "dfc_id": dfc_item.get("id")},
            )
    return resultado


def build_faturamento_tabulator(faturamento_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in faturamento_qs:
        data_faturamento = item.get("data_faturamento")
        parceiro_codigo = item.get("parceiro__codigo") or ""
        parceiro_nome = item.get("parceiro__nome") or ""
        parceiro_label = ""
        if parceiro_codigo and parceiro_nome:
            parceiro_label = f"{parceiro_codigo} - {parceiro_nome}"
        else:
            parceiro_label = parceiro_codigo or parceiro_nome

        produto_codigo = item.get("produto__codigo_produto") or ""
        produto_descricao = item.get("produto__descricao_produto") or ""
        produto_label = ""
        if produto_codigo and produto_descricao:
            produto_label = f"{produto_codigo} - {produto_descricao}"
        else:
            produto_label = produto_codigo or produto_descricao

        resultado.append(
            {
                "id": item.get("id"),
                "nome_origem": item.get("nome_origem") or "",
                "data_faturamento": _fmt_date_br(data_faturamento),
                "data_faturamento_iso": (
                    data_faturamento.strftime("%Y-%m-%d")
                    if data_faturamento
                    else ""
                ),
                "ano_faturamento": data_faturamento.year if data_faturamento else "",
                "mes_faturamento": data_faturamento.month if data_faturamento else "",
                "nome_empresa": item.get("nome_empresa") or "",
                "parceiro_id": item.get("parceiro_id") or "",
                "parceiro_label": parceiro_label,
                "numero_nota": int(item.get("numero_nota") or 0),
                "valor_nota": float(item.get("valor_nota_num") or 0),
                "participacao_venda_geral": float(item.get("participacao_venda_geral_num") or 0),
                "participacao_venda_cliente": float(item.get("participacao_venda_cliente_num") or 0),
                "valor_nota_unico": float(item.get("valor_nota_unico_num") or 0),
                "peso_bruto_unico": float(item.get("peso_bruto_unico_num") or 0),
                "quantidade_volumes": float(item.get("quantidade_volumes_num") or 0),
                "quantidade_saida": float(item.get("quantidade_saida_num") or 0),
                "status_nfe": item.get("status_nfe") or "",
                "apelido_vendedor": item.get("apelido_vendedor") or "",
                "operacao_id": item.get("operacao_id") or "",
                "operacao_descricao": item.get("operacao__descricao_receita_despesa") or "",
                "natureza_id": item.get("natureza_id") or "",
                "natureza_descricao": item.get("natureza__descricao") or "",
                "centro_resultado_id": item.get("centro_resultado_id") or "",
                "centro_resultado_descricao": item.get("centro_resultado__descricao") or "",
                "tipo_movimento": item.get("tipo_movimento") or "",
                "prazo_medio": float(item.get("prazo_medio_num") or 0),
                "media_unica": float(item.get("media_unica_num") or 0),
                "tipo_venda": item.get("tipo_venda") or "",
                "produto_id": item.get("produto_id") or "",
                "produto_label": produto_label,
                "cidade_parceiro": item.get("parceiro__cidade__nome") or "",
                "gerente": item.get("gerente") or "",
                "descricao_perfil": item.get("descricao_perfil") or "",
                "valor_frete": (
                    float(item.get("valor_frete_num"))
                    if item.get("valor_frete_num") is not None
                    else None
                ),
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_faturamento_modulo",
                kwargs={"empresa_id": empresa_id, "faturamento_id": item.get("id")},
            )
    return resultado


def build_adiantamentos_tabulator(adiantamentos_qs, empresa_id: int, permitir_edicao: bool = True):
    resultado = []
    for item in adiantamentos_qs:
        resultado.append(
            {
                "id": item.get("id"),
                "empresa_id": item.get("empresa_id") or "",
                "empresa_nome": item.get("empresa__nome") or "",
                "moeda": item.get("moeda") or "",
                "saldo_banco_em_reais": float(item.get("saldo_banco_em_reais_num") or 0),
                "saldo_real_em_reais": float(item.get("saldo_real_em_reais_num") or 0),
                "saldo_real": float(item.get("saldo_real_num") or 0),
                "conta_descricao": item.get("conta_descricao") or "",
                "saldo_banco": int(item.get("saldo_banco") or 0),
                "banco": item.get("banco") or "",
                "agencia": item.get("agencia") or "",
                "conta_bancaria": item.get("conta_bancaria") or "",
                "empresa_descricao": item.get("empresa_descricao") or "",
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_adiantamento_modulo",
                kwargs={"empresa_id": empresa_id, "adiantamento_id": item.get("id")},
            )
    return resultado


def build_contas_a_receber_tabulator(contas_qs, empresa_id: int, permitir_edicao: bool = True):
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
            }
        )
        if permitir_edicao:
            resultado[-1]["editar_url"] = reverse(
                "editar_contas_a_receber_modulo",
                kwargs={"empresa_id": empresa_id, "conta_id": conta.get("id")},
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
                "titulo_id": item.get("titulo_id") or "",
                "natureza_id": item.get("natureza_id") or "",
                "centro_resultado_id": item.get("centro_resultado_id") or "",
                "operacao_id": item.get("operacao_id") or "",
                "parceiro_id": item.get("parceiro_id") or "",
                "titulo_codigo": item.get("titulo__tipo_titulo_codigo") or "",
                "titulo_descricao": item.get("titulo__descricao") or "",
                "natureza_codigo": item.get("natureza__codigo") or "",
                "natureza_descricao": item.get("natureza__descricao") or "",
                "centro_resultado_descricao": centro_resultado_descricao,
                "operacao_codigo": item.get("operacao__tipo_operacao_codigo") or "",
                "operacao_descricao": item.get("operacao__descricao_receita_despesa") or "",
                "parceiro_codigo": item.get("parceiro__codigo") or "",
                "parceiro_nome": item.get("parceiro__nome") or "",
                "editar_url": reverse(
                    "editar_orcamento_modulo",
                    kwargs={"empresa_id": empresa_id, "orcamento_id": item.get("id")},
                ),
                "excluir_url": reverse(
                    "excluir_orcamento_modulo",
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
                "centro_resultado_id": item.get("centro_resultado_id") or "",
                "centro_resultado_descricao": item.get("centro_resultado__descricao") or "",
                "natureza_id": item.get("natureza_id") or "",
                "natureza_codigo": item.get("natureza__codigo") or "",
                "natureza_descricao": item.get("natureza__descricao") or "",
                "nome_empresa": item.get("nome_empresa") or "",
                "ano": item.get("ano") or "",
                **valores,
                "total": sum(valores.values()),
                "editar_url": reverse(
                    "editar_orcamento_planejado_modulo",
                    kwargs={"empresa_id": empresa_id, "orcamento_planejado_id": item.get("id")},
                ),
                "excluir_url": reverse(
                    "excluir_orcamento_planejado_modulo",
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
