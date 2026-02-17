from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import shutil

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from .models import (
    Atividade,
    Cargas,
    Carteira,
    Cidade,
    Colaborador,
    Empresa,
    FluxoDeCaixaDFC,
    Natureza,
    Operacao,
    Parceiro,
    Projeto,
    Regiao,
    Titulo,
    Usuario,
    Venda,
)
from .utils.administrativo_utils import (
    _set_prazo_inicio_e_prazo_termino,
    _transformar_date_ou_none,
    _transformar_int_ou_none,
    _transformar_iso_week_parts_ou_none,
)
from .utils.comercial_importacao import importar_carteira_do_diretorio, importar_vendas_do_diretorio
from .utils.financeiro_importacao import importar_dfc_do_diretorio
from .utils.operacional_importacao import importar_cargas_do_diretorio


def calcular_dashboard_tofu(atividades_qs):
    hoje = timezone.localdate()
    inicio_semana_atual = hoje - timedelta(days=hoje.isoweekday() - 1)
    fim_semana_atual = inicio_semana_atual + timedelta(days=6)
    inicio_proxima_semana = inicio_semana_atual + timedelta(days=7)
    fim_proxima_semana = inicio_semana_atual + timedelta(days=13)
    inicio_duas_semanas_apos = inicio_semana_atual + timedelta(days=14)

    atrasados_qs = atividades_qs.filter(
        progresso__lt=100,
        data_previsao_termino__lt=hoje,
    )
    alertas_qs = atividades_qs.filter(
        progresso__lt=100,
        data_previsao_termino__gte=hoje,
        data_previsao_termino__lte=fim_proxima_semana,
    )
    concluidos_qs = atividades_qs.filter(progresso__gte=100)
    a_fazer_qs = atividades_qs.filter(
        progresso__lt=100,
        data_previsao_termino__gte=inicio_duas_semanas_apos,
    )

    atrasados_total = atrasados_qs.count()
    alertas_total = alertas_qs.count()
    concluidos_total = concluidos_qs.count()
    a_fazer_total = a_fazer_qs.count()
    total_atividades = atividades_qs.count()

    concluidos_no_prazo = concluidos_qs.filter(
        data_finalizada__isnull=False,
        data_previsao_inicio__isnull=False,
        data_previsao_termino__isnull=False,
        data_finalizada__gte=F("data_previsao_inicio"),
        data_finalizada__lte=F("data_previsao_termino"),
    ).count()
    concluidos_fora_prazo = concluidos_qs.filter(
        data_finalizada__isnull=False,
        data_previsao_termino__isnull=False,
        data_finalizada__gt=F("data_previsao_termino"),
    ).count()

    def _pct(valor, total):
        if total <= 0:
            return 0
        return round((valor * 100) / total, 1)

    return {
        "atrasados": {
            "total": atrasados_total,
            "parados": atrasados_qs.filter(progresso=0).count(),
            "em_andamento": atrasados_qs.filter(progresso__gt=0).count(),
            "percentual": _pct(atrasados_total, total_atividades),
        },
        "alertas": {
            "total": alertas_total,
            "semana_atual": alertas_qs.filter(
                data_previsao_termino__gte=inicio_semana_atual,
                data_previsao_termino__lte=fim_semana_atual,
            ).count(),
            "proxima_semana": alertas_qs.filter(
                data_previsao_termino__gte=inicio_proxima_semana,
                data_previsao_termino__lte=fim_proxima_semana,
            ).count(),
            "percentual": _pct(alertas_total, total_atividades),
        },
        "concluidos": {
            "total": concluidos_total,
            "no_prazo": concluidos_no_prazo,
            "fora_do_prazo": concluidos_fora_prazo,
            "percentual": _pct(concluidos_total, total_atividades),
        },
        "a_fazer": {
            "total": a_fazer_total,
            "parados": a_fazer_qs.filter(progresso=0).count(),
            "em_andamento": a_fazer_qs.filter(progresso__gt=0).count(),
            "percentual": _pct(a_fazer_total, total_atividades),
        },
        "total_atividades": total_atividades,
    }


def usuarios_com_permissoes_ids(usuarios_qs):
    usuarios = list(usuarios_qs)
    for usuario in usuarios:
        usuario.permissoes_ids = set(usuario.permissoes.values_list("id", flat=True))
    return usuarios


def criar_empresa_por_nome(nome):
    nome = (nome or "").strip()
    if not nome:
        return "O nome da empresa e obrigatorio."
    Empresa.criar_empresa(nome=nome)
    return ""


def atualizar_empresa_por_nome(empresa, novo_nome):
    novo_nome = (novo_nome or "").strip()
    if not novo_nome:
        return "O nome da empresa e obrigatorio."
    empresa.atualizar_nome(novo_nome=novo_nome)
    return ""


def excluir_empresa_por_id(empresa_id):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist as exc:
        return False, f"Empresa nao encontrada. {exc}"
    empresa.excluir_empresa()
    return True, "Empresa excluida com sucesso!"


def criar_usuario_por_post(empresa, post_data, permissoes):
    nome = post_data.get("nome")
    senha = post_data.get("senha")
    Usuario.criar_usuario(
        empresa=empresa,
        username=nome,
        password=senha,
        permissoes=permissoes,
    )


def atualizar_usuario_por_post(usuario, post_data, permissoes):
    usuario.atualizar_usuario(
        username=post_data.get("nome"),
        password=post_data.get("senha"),
        permissoes=permissoes,
    )


def excluir_usuario_por_id(usuario_id):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist as exc:
        return False, None, f"Usuario nao encontrado. {exc}"
    empresa_id = usuario.empresa.id
    usuario.excluir_usuario()
    return True, empresa_id, "Usuario excluido com sucesso!"


def criar_colaborador_por_nome(empresa, nome):
    nome = (nome or "").strip()
    if not nome:
        return "Nome do colaborador e obrigatorio."
    Colaborador.criar_colaborador(nome=nome, empresa=empresa)
    return ""


def atualizar_colaborador_por_nome(colaborador, nome):
    nome = (nome or "").strip()
    if not nome:
        return "Nome do colaborador e obrigatorio."
    colaborador.atualizar_colaborador(novo_nome=nome)
    return ""


def criar_projeto_por_dados(empresa, nome, codigo):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome do projeto e obrigatorio."
    Projeto.criar_projeto(nome=nome, empresa=empresa, codigo=codigo)
    return ""


def atualizar_projeto_por_dados(projeto, nome, codigo):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome do projeto e obrigatorio."
    projeto.atualizar_projeto(novo_nome=nome, novo_codigo=codigo)
    return ""


def criar_cidade_por_dados(empresa, nome, codigo):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome da cidade e obrigatorio."
    if not codigo:
        return "Codigo da cidade e obrigatorio."
    if Cidade.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Ja existe cidade com este codigo em outra empresa."
    if Cidade.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Ja existe cidade com este codigo nesta empresa."
    Cidade.criar_cidade(nome=nome, empresa=empresa, codigo=codigo)
    return ""


def atualizar_cidade_por_dados(cidade, nome, codigo, empresa):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome da cidade e obrigatorio."
    if not codigo:
        return "Codigo da cidade e obrigatorio."
    if Cidade.objects.filter(codigo=codigo).exclude(id=cidade.id).exclude(empresa=empresa).exists():
        return "Ja existe cidade com este codigo em outra empresa."
    if Cidade.objects.filter(empresa=empresa, codigo=codigo).exclude(id=cidade.id).exists():
        return "Ja existe cidade com este codigo nesta empresa."
    cidade.atualizar_cidade(novo_nome=nome, novo_codigo=codigo)
    return ""


def criar_regiao_por_dados(empresa, nome, codigo):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome da regiao e obrigatorio."
    if not codigo:
        return "Codigo da regiao e obrigatorio."
    if Regiao.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Ja existe regiao com este codigo em outra empresa."
    if Regiao.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Ja existe regiao com este codigo nesta empresa."
    Regiao.criar_regiao(nome=nome, empresa=empresa, codigo=codigo)
    return ""


def atualizar_regiao_por_dados(regiao, nome, codigo, empresa):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome da regiao e obrigatorio."
    if not codigo:
        return "Codigo da regiao e obrigatorio."
    if Regiao.objects.filter(codigo=codigo).exclude(id=regiao.id).exclude(empresa=empresa).exists():
        return "Ja existe regiao com este codigo em outra empresa."
    if Regiao.objects.filter(empresa=empresa, codigo=codigo).exclude(id=regiao.id).exists():
        return "Ja existe regiao com este codigo nesta empresa."
    regiao.atualizar_regiao(novo_nome=nome, novo_codigo=codigo)
    return ""

def criar_parceiro_por_dados(empresa, nome, codigo):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome do parceiro e obrigatorio."
    if not codigo:
        return "Codigo do parceiro e obrigatorio."
    if Parceiro.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Ja existe parceiro com este codigo em outra empresa."
    if Parceiro.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Ja existe parceiro com este codigo nesta empresa."
    Parceiro.criar_parceiro(nome=nome, codigo=codigo, empresa=empresa)
    return ""


def atualizar_parceiro_por_dados(parceiro, nome, codigo, empresa):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome do parceiro e obrigatorio."
    if not codigo:
        return "Codigo do parceiro e obrigatorio."
    if Parceiro.objects.filter(codigo=codigo).exclude(id=parceiro.id).exclude(empresa=empresa).exists():
        return "Ja existe parceiro com este codigo em outra empresa."
    if Parceiro.objects.filter(empresa=empresa, codigo=codigo).exclude(id=parceiro.id).exists():
        return "Ja existe parceiro com este codigo nesta empresa."
    parceiro.atualizar_parceiro(novo_nome=nome, novo_codigo=codigo)
    return ""

def criar_titulo_por_dados(empresa, tipo_titulo_codigo, descricao):
    tipo_titulo_codigo = (tipo_titulo_codigo or "").strip()
    descricao = (descricao or "").strip()
    if not tipo_titulo_codigo:
        return "Codigo do titulo e obrigatorio."
    if Titulo.objects.filter(tipo_titulo_codigo=tipo_titulo_codigo).exclude(empresa=empresa).exists():
        return "Ja existe titulo com este codigo em outra empresa."
    if Titulo.objects.filter(empresa=empresa, tipo_titulo_codigo=tipo_titulo_codigo).exists():
        return "Ja existe titulo com este codigo nesta empresa."
    Titulo.criar_titulo(empresa=empresa, tipo_titulo_codigo=tipo_titulo_codigo, descricao=descricao)
    return ""


def atualizar_titulo_por_dados(titulo, tipo_titulo_codigo, descricao, empresa):
    tipo_titulo_codigo = (tipo_titulo_codigo or "").strip()
    descricao = (descricao or "").strip()
    if not tipo_titulo_codigo:
        return "Codigo do titulo e obrigatorio."
    if Titulo.objects.filter(tipo_titulo_codigo=tipo_titulo_codigo).exclude(id=titulo.id).exclude(empresa=empresa).exists():
        return "Ja existe titulo com este codigo em outra empresa."
    if Titulo.objects.filter(empresa=empresa, tipo_titulo_codigo=tipo_titulo_codigo).exclude(id=titulo.id).exists():
        return "Ja existe titulo com este codigo nesta empresa."
    titulo.atualizar_titulo(tipo_titulo_codigo=tipo_titulo_codigo, descricao=descricao)
    return ""


def criar_natureza_por_dados(empresa, codigo, descricao):
    codigo = (codigo or "").strip()
    descricao = (descricao or "").strip()
    if not codigo:
        return "Codigo da natureza e obrigatorio."
    if Natureza.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Ja existe natureza com este codigo em outra empresa."
    if Natureza.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Ja existe natureza com este codigo nesta empresa."
    Natureza.criar_natureza(empresa=empresa, codigo=codigo, descricao=descricao)
    return ""


def atualizar_natureza_por_dados(natureza, codigo, descricao, empresa):
    codigo = (codigo or "").strip()
    descricao = (descricao or "").strip()
    if not codigo:
        return "Codigo da natureza e obrigatorio."
    if Natureza.objects.filter(codigo=codigo).exclude(id=natureza.id).exclude(empresa=empresa).exists():
        return "Ja existe natureza com este codigo em outra empresa."
    if Natureza.objects.filter(empresa=empresa, codigo=codigo).exclude(id=natureza.id).exists():
        return "Ja existe natureza com este codigo nesta empresa."
    natureza.atualizar_natureza(codigo=codigo, descricao=descricao)
    return ""


def criar_operacao_por_dados(empresa, tipo_operacao_codigo, descricao_receita_despesa):
    tipo_operacao_codigo = (tipo_operacao_codigo or "").strip()
    descricao_receita_despesa = (descricao_receita_despesa or "").strip()
    if not tipo_operacao_codigo:
        return "Codigo da operacao e obrigatorio."
    if Operacao.objects.filter(tipo_operacao_codigo=tipo_operacao_codigo).exclude(empresa=empresa).exists():
        return "Ja existe operacao com este codigo em outra empresa."
    if Operacao.objects.filter(empresa=empresa, tipo_operacao_codigo=tipo_operacao_codigo).exists():
        return "Ja existe operacao com este codigo nesta empresa."
    Operacao.criar_operacao(
        empresa=empresa,
        tipo_operacao_codigo=tipo_operacao_codigo,
        descricao_receita_despesa=descricao_receita_despesa,
    )
    return ""


def atualizar_operacao_por_dados(operacao, tipo_operacao_codigo, descricao_receita_despesa, empresa):
    tipo_operacao_codigo = (tipo_operacao_codigo or "").strip()
    descricao_receita_despesa = (descricao_receita_despesa or "").strip()
    if not tipo_operacao_codigo:
        return "Codigo da operacao e obrigatorio."
    if Operacao.objects.filter(tipo_operacao_codigo=tipo_operacao_codigo).exclude(id=operacao.id).exclude(empresa=empresa).exists():
        return "Ja existe operacao com este codigo em outra empresa."
    if Operacao.objects.filter(empresa=empresa, tipo_operacao_codigo=tipo_operacao_codigo).exclude(id=operacao.id).exists():
        return "Ja existe operacao com este codigo nesta empresa."
    operacao.atualizar_operacao(
        tipo_operacao_codigo=tipo_operacao_codigo,
        descricao_receita_despesa=descricao_receita_despesa,
    )
    return ""


def _parse_decimal_ou_zero(valor):
    texto = (valor or "").strip()
    if not texto:
        return Decimal("0")

    texto = texto.replace("R$", "").replace(" ", "")
    texto_lower = texto.lower()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1 and "e" not in texto_lower:
        texto = texto.replace(".", "")

    try:
        return Decimal(texto)
    except InvalidOperation:
        return Decimal("0")


def _parse_date_ou_none(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_int_ou_zero(valor):
    if valor in (None, ""):
        return 0
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _parse_bool_checkbox(post_data, campo):
    return post_data.get(campo) == "on"


def _dados_carteira_from_post(post_data, empresa):
    regiao = Regiao.objects.filter(id=post_data.get("regiao_id"), empresa=empresa).first()
    cidade = Cidade.objects.filter(id=post_data.get("cidade_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()

    data_cadastro_raw = post_data.get("data_cadastro")
    data_cadastro = _parse_date_ou_none(data_cadastro_raw)

    return {
        "data_cadastro_raw": data_cadastro_raw,
        "regiao": regiao,
        "cidade": cidade,
        "parceiro": parceiro,
        "valor_faturado": _parse_decimal_ou_zero(post_data.get("valor_faturado")),
        "limite_credito": _parse_decimal_ou_zero(post_data.get("limite_credito")),
        "ultima_venda": _parse_date_ou_none(post_data.get("ultima_venda")),
        "qtd_dias_sem_venda": _parse_int_ou_zero(post_data.get("qtd_dias_sem_venda")),
        "intervalo": (post_data.get("intervalo") or "").strip(),
        "data_cadastro": data_cadastro,
        "gerente": (post_data.get("gerente") or "").strip(),
        "vendedor": (post_data.get("vendedor") or "").strip(),
        "descricao_perfil": (post_data.get("descricao_perfil") or "").strip(),
        "ativo_indicador": _parse_bool_checkbox(post_data, "ativo_indicador"),
        "cliente_indicador": _parse_bool_checkbox(post_data, "cliente_indicador"),
        "fornecedor_indicador": _parse_bool_checkbox(post_data, "fornecedor_indicador"),
        "transporte_indicador": _parse_bool_checkbox(post_data, "transporte_indicador"),
    }


def criar_carteira_por_post(empresa, post_data):
    dados = _dados_carteira_from_post(post_data, empresa)
    if not dados["parceiro"]:
        return "Parceiro e obrigatorio."
    if not dados["data_cadastro_raw"]:
        return "Data de cadastramento e obrigatoria."
    if not dados["data_cadastro"]:
        return "Data de cadastramento invalida."
    dados.pop("data_cadastro_raw", None)
    Carteira.criar_carteira(empresa=empresa, **dados)
    return ""


def atualizar_carteira_por_post(carteira, empresa, post_data):
    dados = _dados_carteira_from_post(post_data, empresa)
    if not dados["parceiro"]:
        return "Parceiro e obrigatorio."
    if not dados["data_cadastro_raw"]:
        return "Data de cadastramento e obrigatoria."
    if not dados["data_cadastro"]:
        return "Data de cadastramento invalida."
    dados.pop("data_cadastro_raw", None)
    carteira.atualizar_carteira(**dados)
    return ""


def _dados_venda_from_post(post_data):
    data_venda_raw = post_data.get("data_venda")
    data_venda = _parse_date_ou_none(data_venda_raw)

    return {
        "codigo": (post_data.get("codigo") or "").strip(),
        "descricao": (post_data.get("descricao") or "").strip(),
        "valor_venda": _parse_decimal_ou_zero(post_data.get("valor_venda")),
        "qtd_notas": max(0, _parse_int_ou_zero(post_data.get("qtd_notas"))),
        "custo_medio_icms_cmv": _parse_decimal_ou_zero(post_data.get("custo_medio_icms_cmv")),
        "peso_bruto": _parse_decimal_ou_zero(post_data.get("peso_bruto")),
        "peso_liquido": _parse_decimal_ou_zero(post_data.get("peso_liquido")),
        "data_venda_raw": data_venda_raw,
        "data_venda": data_venda,
    }


def criar_venda_por_post(empresa, post_data):
    dados = _dados_venda_from_post(post_data)
    if not dados["codigo"]:
        return "Codigo da venda e obrigatorio."
    if not dados["data_venda_raw"]:
        return "Data da venda e obrigatoria."
    if not dados["data_venda"]:
        return "Data da venda invalida."

    dados.pop("data_venda_raw", None)
    Venda.criar_venda(empresa=empresa, **dados)
    return ""


def atualizar_venda_por_post(venda, empresa, post_data):
    dados = _dados_venda_from_post(post_data)
    if not dados["codigo"]:
        return "Codigo da venda e obrigatorio."
    if not dados["data_venda_raw"]:
        return "Data da venda e obrigatoria."
    if not dados["data_venda"]:
        return "Data da venda invalida."

    dados.pop("data_venda_raw", None)
    venda.atualizar_venda(**dados)
    return ""


def _dados_dfc_from_post(post_data, empresa):
    titulo = Titulo.objects.filter(id=post_data.get("titulo_id"), empresa=empresa).first()
    natureza = Natureza.objects.filter(id=post_data.get("natureza_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()
    operacao = Operacao.objects.filter(id=post_data.get("operacao_id"), empresa=empresa).first()
    data_negociacao_raw = post_data.get("data_negociacao")
    data_vencimento_raw = post_data.get("data_vencimento")

    return {
        "data_negociacao_raw": data_negociacao_raw,
        "data_vencimento_raw": data_vencimento_raw,
        "data_negociacao": _parse_date_ou_none(data_negociacao_raw),
        "data_vencimento": _parse_date_ou_none(data_vencimento_raw),
        "valor_liquido": _parse_decimal_ou_zero(post_data.get("valor_liquido")),
        "numero_nota": (post_data.get("numero_nota") or "").strip(),
        "titulo": titulo,
        "descricao_centro_resultado": (post_data.get("descricao_centro_resultado") or "").strip(),
        "descricao_tipo_operacao": (post_data.get("descricao_tipo_operacao") or "").strip(),
        "natureza": natureza,
        "historico": (post_data.get("historico") or "").strip(),
        "parceiro": parceiro,
        "operacao": operacao,
        "tipo_movimento": (post_data.get("tipo_movimento") or "").strip(),
    }


def criar_dfc_por_post(empresa, post_data):
    dados = _dados_dfc_from_post(post_data, empresa)
    if not dados["data_negociacao_raw"]:
        return "Data de negociacao e obrigatoria."
    if not dados["data_negociacao"]:
        return "Data de negociacao invalida."
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    FluxoDeCaixaDFC.criar_fluxo_de_caixa_dfc(empresa=empresa, **dados)
    return ""


def atualizar_dfc_por_post(dfc_item, empresa, post_data):
    dados = _dados_dfc_from_post(post_data, empresa)
    if not dados["data_negociacao_raw"]:
        return "Data de negociacao e obrigatoria."
    if not dados["data_negociacao"]:
        return "Data de negociacao invalida."
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    dfc_item.atualizar_fluxo_de_caixa_dfc(**dados)
    return ""


def _dados_carga_from_post(post_data, empresa):
    regiao = Regiao.objects.filter(id=post_data.get("regiao_id"), empresa=empresa).first()
    data_inicio_raw = post_data.get("data_inicio")
    data_prevista_saida_raw = post_data.get("data_prevista_saida")
    prazo_maximo_dias_raw = (post_data.get("prazo_maximo_dias") or "").strip()

    return {
        "situacao": (post_data.get("situacao") or "").strip(),
        "ordem_de_carga_codigo": (post_data.get("ordem_de_carga_codigo") or "").strip(),
        "data_inicio_raw": data_inicio_raw,
        "data_prevista_saida_raw": data_prevista_saida_raw,
        "data_inicio": _parse_date_ou_none(data_inicio_raw),
        "data_prevista_saida": _parse_date_ou_none(data_prevista_saida_raw),
        "data_chegada": _parse_date_ou_none(post_data.get("data_chegada")),
        "data_finalizacao": _parse_date_ou_none(post_data.get("data_finalizacao")),
        "nome_motorista": (post_data.get("nome_motorista") or "").strip(),
        "nome_fantasia_empresa": (post_data.get("nome_fantasia_empresa") or "").strip(),
        "regiao": regiao,
        "prazo_maximo_dias_raw": prazo_maximo_dias_raw,
        "prazo_maximo_dias": 10 if prazo_maximo_dias_raw == "" else max(0, _parse_int_ou_zero(prazo_maximo_dias_raw)),
    }


def criar_carga_por_post(empresa, post_data):
    dados = _dados_carga_from_post(post_data, empresa)
    if not dados["situacao"]:
        return "Situacao da carga e obrigatoria."
    if not dados["ordem_de_carga_codigo"]:
        return "Ordem de carga e obrigatoria."
    if not dados["nome_fantasia_empresa"]:
        return "Nome fantasia da empresa e obrigatorio."
    if not dados["data_inicio_raw"]:
        return "Data de inicio e obrigatoria."
    if not dados["data_inicio"]:
        return "Data de inicio invalida."
    if not dados["data_prevista_saida_raw"]:
        return "Data prevista para saida e obrigatoria."
    if not dados["data_prevista_saida"]:
        return "Data prevista para saida invalida."
    if dados["data_finalizacao"] and not dados["data_chegada"]:
        return "Data de finalizacao so pode ser preenchida quando data de chegada estiver preenchida."

    dados.pop("data_inicio_raw", None)
    dados.pop("data_prevista_saida_raw", None)
    dados.pop("prazo_maximo_dias_raw", None)
    Cargas.criar_carga(empresa=empresa, **dados)
    return ""


def atualizar_carga_por_post(carga, empresa, post_data):
    dados = _dados_carga_from_post(post_data, empresa)
    if not dados["situacao"]:
        return "Situacao da carga e obrigatoria."
    if not dados["ordem_de_carga_codigo"]:
        return "Ordem de carga e obrigatoria."
    if not dados["nome_fantasia_empresa"]:
        return "Nome fantasia da empresa e obrigatorio."
    if not dados["data_inicio_raw"]:
        return "Data de inicio e obrigatoria."
    if not dados["data_inicio"]:
        return "Data de inicio invalida."
    if not dados["data_prevista_saida_raw"]:
        return "Data prevista para saida e obrigatoria."
    if not dados["data_prevista_saida"]:
        return "Data prevista para saida invalida."
    if dados["data_finalizacao"] and not dados["data_chegada"]:
        return "Data de finalizacao so pode ser preenchida quando data de chegada estiver preenchida."

    dados.pop("data_inicio_raw", None)
    dados.pop("data_prevista_saida_raw", None)
    dados.pop("prazo_maximo_dias_raw", None)
    carga.atualizar_carga(**dados)
    return ""


def _dados_atividade_from_post(post_data, empresa):
    projeto = Projeto.objects.filter(id=post_data.get("projeto_id"), empresa=empresa).first()
    if not projeto:
        return None, "Projeto invalido para esta empresa."

    gestor = Colaborador.objects.filter(
        id=_transformar_int_ou_none(post_data.get("gestor_id")),
        empresa=empresa,
    ).first()
    responsavel = Colaborador.objects.filter(
        id=_transformar_int_ou_none(post_data.get("responsavel_id")),
        empresa=empresa,
    ).first()

    semana_info = _transformar_iso_week_parts_ou_none(post_data.get("semana_de_prazo"))
    if semana_info:
        ano, semana = semana_info
        data_previsao_inicio, data_previsao_termino = _set_prazo_inicio_e_prazo_termino(ano, semana)
        semana_de_prazo = semana
    else:
        data_previsao_inicio = None
        data_previsao_termino = None
        semana_de_prazo = None

    dados = {
        "projeto": projeto,
        "gestor": gestor,
        "responsavel": responsavel,
        "interlocutor": post_data.get("interlocutor", ""),
        "semana_de_prazo": semana_de_prazo,
        "data_previsao_inicio": data_previsao_inicio,
        "data_previsao_termino": data_previsao_termino,
        "data_finalizada": _transformar_date_ou_none(post_data.get("data_finalizada")),
        "historico": post_data.get("historico", ""),
        "tarefa": post_data.get("tarefa", ""),
        "progresso": _transformar_int_ou_none(post_data.get("progresso")) or 0,
    }
    return dados, ""


def criar_atividade_por_post(post_data, empresa):
    dados, erro = _dados_atividade_from_post(post_data, empresa)
    if erro:
        return erro
    try:
        Atividade.criar_atividade(**dados)
    except ValidationError as exc:
        return "; ".join(exc.messages)
    return ""


def atualizar_atividade_por_post(atividade, post_data, empresa):
    dados, erro = _dados_atividade_from_post(post_data, empresa)
    if erro:
        return erro
    try:
        atividade.atualizar_atividade(**dados)
    except ValidationError as exc:
        return "; ".join(exc.messages)
    return ""


def semana_iso_input_atividade(atividade):
    if not atividade.data_previsao_inicio:
        return ""
    iso = atividade.data_previsao_inicio.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def preparar_diretorios_carteira():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "comercial" / "carteira"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def importar_upload_carteira(*, empresa, arquivo, confirmar_substituicao, diretorio_importacao, diretorio_subscritos):
    if not arquivo:
        return False, "Selecione um arquivo .xlsx para importar."

    nome_arquivo = Path(arquivo.name).name
    if not nome_arquivo.lower().endswith(".xlsx"):
        return False, "Formato invalido. Envie apenas arquivo .xlsx."

    arquivos_existentes = [f for f in diretorio_importacao.iterdir() if f.is_file()]
    if arquivos_existentes and not confirmar_substituicao:
        return False, "Ja existe arquivo na pasta. Confirme a substituicao para continuar."

    for arquivo_antigo in arquivos_existentes:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        arquivo_antigo.rename(destino_subscrito)

    destino = diretorio_importacao / nome_arquivo
    with destino.open("wb+") as file_out:
        for chunk in arquivo.chunks():
            file_out.write(chunk)

    try:
        resultado = importar_carteira_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar carteira: {exc}"

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, carteiras: {resultado['carteiras']}."
        ),
    )


def preparar_diretorios_vendas():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "comercial" / "vendas"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_dfc():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "financeiro" / "dfc"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def importar_upload_vendas(*, empresa, arquivos, diretorio_importacao, diretorio_subscritos):
    arquivos_xls = []
    for arquivo in arquivos or []:
        nome_arquivo = Path(arquivo.name).name
        if nome_arquivo.lower().endswith(".xls"):
            arquivos_xls.append((arquivo, nome_arquivo))

    if not arquivos_xls:
        return False, "Selecione ao menos um arquivo .xls para importar."

    for arquivo_antigo in [f for f in diretorio_importacao.iterdir() if f.is_file()]:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        shutil.move(str(arquivo_antigo), str(destino_subscrito))

    for arquivo_upload, nome_arquivo in arquivos_xls:
        destino = diretorio_importacao / nome_arquivo
        with destino.open("wb+") as file_out:
            for chunk in arquivo_upload.chunks():
                file_out.write(chunk)

    try:
        resultado = importar_vendas_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar vendas: {exc}"

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, vendas: {resultado['vendas']}."
        ),
    )


def importar_upload_dfc(*, empresa, arquivo, confirmar_substituicao, diretorio_importacao, diretorio_subscritos):
    if not arquivo:
        return False, "Selecione um arquivo .xls para importar."

    nome_arquivo = Path(arquivo.name).name
    if not nome_arquivo.lower().endswith(".xls"):
        return False, "Formato invalido. Envie apenas arquivo .xls."

    arquivos_existentes = [f for f in diretorio_importacao.iterdir() if f.is_file()]
    if arquivos_existentes and not confirmar_substituicao:
        return False, "Ja existe arquivo na pasta. Confirme a substituicao para continuar."

    for arquivo_antigo in arquivos_existentes:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        arquivo_antigo.rename(destino_subscrito)

    destino = diretorio_importacao / nome_arquivo
    with destino.open("wb+") as file_out:
        for chunk in arquivo.chunks():
            file_out.write(chunk)

    try:
        resultado = importar_dfc_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar DFC: {exc}"

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, dfc: {resultado['dfc']}."
        ),
    )


def preparar_diretorios_cargas():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "operacional" / "cargas_em_aberto"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def importar_upload_cargas(*, empresa, arquivo, confirmar_substituicao, diretorio_importacao, diretorio_subscritos):
    if not arquivo:
        return False, "Selecione um arquivo .xls para importar."

    nome_arquivo = Path(arquivo.name).name
    if not nome_arquivo.lower().endswith(".xls"):
        return False, "Formato invalido. Envie apenas arquivo .xls."

    arquivos_existentes = [f for f in diretorio_importacao.iterdir() if f.is_file()]
    if arquivos_existentes and not confirmar_substituicao:
        return False, "Ja existe arquivo na pasta. Confirme a substituicao para continuar."

    for arquivo_antigo in arquivos_existentes:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        arquivo_antigo.rename(destino_subscrito)

    destino = diretorio_importacao / nome_arquivo
    with destino.open("wb+") as file_out:
        for chunk in arquivo.chunks():
            file_out.write(chunk)

    try:
        resultado = importar_cargas_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar cargas: {exc}"

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, cargas: {resultado['cargas']}."
        ),
    )
