from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import json
import shutil
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from .models import (
    Adiantamento,
    Agenda,
    Atividade,
    CentroResultado,
    Cargas,
    Carteira,
    Cidade,
    Colaborador,
    ControleMargem,
    ContasAReceber,
    Empresa,
    FluxoDeCaixaDFC,
    Estoque,
    Frete,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
    Parceiro,
    Permissao,
    ParametroMargemAdministracao,
    ParametroMargemFinanceiro,
    ParametroMargemLogistica,
    ParametroMargemVendas,
    PedidoPendente,
    Motorista,
    Producao,
    Produto,
    Projeto,
    Rota,
    Regiao,
    Titulo,
    Transportadora,
    UnidadeFederativa,
    Usuario,
    Venda,
)
from .utils.administrativo_utils import (
    _set_prazo_inicio_e_prazo_termino,
    _transformar_date_ou_none,
    _transformar_int_ou_none,
    _transformar_iso_week_parts_ou_none,
)
from .utils.controle_margem_regras import (
    calcular_campos_controle_margem_legado,
    obter_parametros_controle_margem,
)
from .utils.comercial_importacao import (
    importar_carteira_do_diretorio,
    importar_controle_margem_do_diretorio,
    importar_pedidos_pendentes_do_diretorio,
    importar_vendas_do_diretorio,
)
from .utils.financeiro_importacao import (
    importar_adiantamentos_do_diretorio,
    importar_contas_a_receber_do_diretorio,
    importar_dfc_do_diretorio,
    importar_orcamento_do_diretorio,
)
from .utils.operacional_importacao import (
    importar_cargas_do_diretorio,
    importar_estoque_do_diretorio,
    importar_fretes_do_diretorio,
    importar_producao_do_diretorio,
)

IMPORTACAO_METADATA_FILE = "_ultimo_import.json"


def _registrar_metadados_importacao(
    *,
    diretorio_subscritos,
    modulo,
    usuario,
    arquivos,
):
    caminho_metadados = Path(diretorio_subscritos) / IMPORTACAO_METADATA_FILE
    nomes_arquivos = [
        Path(nome_arquivo).name
        for nome_arquivo in (arquivos or [])
        if str(nome_arquivo or "").strip()
    ]
    payload = {
        "modulo": str(modulo or "").strip(),
        "usuario": getattr(usuario, "username", "") if usuario else "",
        "registrado_em_iso": timezone.localtime().isoformat(timespec="seconds"),
        "quantidade_arquivos": len(nomes_arquivos),
        "arquivos": nomes_arquivos,
    }
    caminho_metadados.parent.mkdir(parents=True, exist_ok=True)
    caminho_metadados.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _detalhe_erro_importacao(resultado, chave, descricao, valor=None):
    if not isinstance(resultado, dict):
        return None
    if valor is None:
        valor = resultado.get(chave, 0)
    try:
        numeric = int(valor)
    except (TypeError, ValueError):
        numeric = valor if isinstance(valor, int) else 0
    if numeric and numeric > 0:
        return None
    avisos = resultado.get("avisos") or []
    detalhe = avisos[0] if avisos else "nenhum registro compatível encontrado"
    return f"Importacao nao trouxe {descricao}. Motivo: {detalhe}"


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


def criar_empresa_por_nome(nome, possui_sistema=False):
    nome = (nome or "").strip()
    if not nome:
        return "O nome da empresa e obrigatorio."
    Empresa.criar_empresa(nome=nome, possui_sistema=possui_sistema)
    return ""


def atualizar_empresa_por_nome(empresa, novo_nome, possui_sistema=False):
    novo_nome = (novo_nome or "").strip()
    if not novo_nome:
        return "O nome da empresa e obrigatorio."
    empresa.atualizar_nome(novo_nome=novo_nome, possui_sistema=possui_sistema)
    return ""


def excluir_empresa_por_id(empresa_id):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist as exc:
        return False, f"Empresa nao encontrada. {exc}"
    empresa.excluir_empresa()
    return True, "Empresa excluida com sucesso!"


def _valor_checkbox_ativo(post_data, campo):
    return str(post_data.get(campo, "")).strip().lower() in {"1", "true", "on", "sim", "yes"}


def criar_usuario_por_post(empresa, post_data, permissoes):
    nome = post_data.get("nome")
    senha = post_data.get("senha")
    is_staff = _valor_checkbox_ativo(post_data, "is_staff")
    permissoes_usuario = list(Permissao.objects.all()) if is_staff else permissoes
    Usuario.criar_usuario(
        empresa=empresa,
        username=nome,
        password=senha,
        permissoes=permissoes_usuario,
        is_staff=is_staff,
    )


def atualizar_usuario_por_post(usuario, post_data, permissoes, usuario_logado=None):
    is_staff = _valor_checkbox_ativo(post_data, "is_staff")
    if (
        usuario_logado
        and usuario_logado.id == usuario.id
        and usuario_logado.is_staff
        and not usuario_logado.is_superuser
        and not is_staff
    ):
        return "Usuario staff nao pode remover o proprio acesso staff."

    permissoes_usuario = list(Permissao.objects.all()) if is_staff else permissoes
    usuario.atualizar_usuario(
        username=post_data.get("nome"),
        password=post_data.get("senha"),
        permissoes=permissoes_usuario,
        is_staff=is_staff,
    )
    return ""


def excluir_usuario_por_id(usuario_id):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist as exc:
        return False, None, f"Usuario nao encontrado. {exc}"
    empresa_id = usuario.empresa_id
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
        return "Nome da região é obrigatório."
    if not codigo:
        return "Código da região é obrigatório."
    if Regiao.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Já existe região com este código em outra empresa."
    if Regiao.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Já existe região com este código nesta empresa."
    Regiao.criar_regiao(nome=nome, empresa=empresa, codigo=codigo)
    return ""


def atualizar_regiao_por_dados(regiao, nome, codigo, empresa):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    if not nome:
        return "Nome da região é obrigatório."
    if not codigo:
        return "Código da região é obrigatório."
    if Regiao.objects.filter(codigo=codigo).exclude(id=regiao.id).exclude(empresa=empresa).exists():
        return "Já existe região com este código em outra empresa."
    if Regiao.objects.filter(empresa=empresa, codigo=codigo).exclude(id=regiao.id).exists():
        return "Já existe região com este código nesta empresa."
    regiao.atualizar_regiao(novo_nome=nome, novo_codigo=codigo)
    return ""


def criar_rota_por_dados(empresa, codigo_rota, nome, uf_id=None):
    codigo_rota = (codigo_rota or "").strip()
    nome = (nome or "").strip()
    uf = UnidadeFederativa.objects.filter(id=uf_id, empresa=empresa).first() if uf_id else None
    if not codigo_rota:
        return "Código da rota é obrigatório."
    if not nome:
        return "Nome da rota é obrigatório."
    if uf_id and not uf:
        return "UF inválida para a rota."
    if Rota.objects.filter(codigo_rota=codigo_rota).exclude(empresa=empresa).exists():
        return "Já existe rota com este código em outra empresa."
    if Rota.objects.filter(empresa=empresa, codigo_rota=codigo_rota).exists():
        return "Já existe rota com este código nesta empresa."
    Rota.criar_rota(empresa=empresa, codigo_rota=codigo_rota, nome=nome, uf=uf)
    return ""


def atualizar_rota_por_dados(rota, codigo_rota, nome, empresa, uf_id=None):
    codigo_rota = (codigo_rota or "").strip()
    nome = (nome or "").strip()
    uf = UnidadeFederativa.objects.filter(id=uf_id, empresa=empresa).first() if uf_id else None
    if not codigo_rota:
        return "Código da rota é obrigatório."
    if not nome:
        return "Nome da rota é obrigatório."
    if uf_id and not uf:
        return "UF inválida para a rota."
    if Rota.objects.filter(codigo_rota=codigo_rota).exclude(id=rota.id).exclude(empresa=empresa).exists():
        return "Já existe rota com este código em outra empresa."
    if Rota.objects.filter(empresa=empresa, codigo_rota=codigo_rota).exclude(id=rota.id).exists():
        return "Já existe rota com este código nesta empresa."
    rota.atualizar_rota(codigo_rota=codigo_rota, nome=nome, uf=uf)
    return ""


def criar_unidade_federativa_por_dados(empresa, codigo, sigla):
    codigo = (codigo or "").strip()
    sigla = (sigla or "").strip().upper()
    if not codigo:
        return "Codigo da unidade federativa e obrigatorio."
    if not sigla:
        return "Sigla da unidade federativa e obrigatoria."
    if UnidadeFederativa.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Ja existe unidade federativa com este codigo em outra empresa."
    if UnidadeFederativa.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Ja existe unidade federativa com este codigo nesta empresa."
    UnidadeFederativa.criar_unidade_federativa(empresa=empresa, codigo=codigo, sigla=sigla)
    return ""


def atualizar_unidade_federativa_por_dados(unidade_federativa, codigo, sigla, empresa):
    codigo = (codigo or "").strip()
    sigla = (sigla or "").strip().upper()
    if not codigo:
        return "Codigo da unidade federativa e obrigatorio."
    if not sigla:
        return "Sigla da unidade federativa e obrigatoria."
    if UnidadeFederativa.objects.filter(codigo=codigo).exclude(id=unidade_federativa.id).exclude(empresa=empresa).exists():
        return "Ja existe unidade federativa com este codigo em outra empresa."
    if UnidadeFederativa.objects.filter(empresa=empresa, codigo=codigo).exclude(id=unidade_federativa.id).exists():
        return "Ja existe unidade federativa com este codigo nesta empresa."
    unidade_federativa.atualizar_unidade_federativa(codigo=codigo, sigla=sigla)
    return ""


def criar_parceiro_por_dados(empresa, nome, codigo, cidade_id=None):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    cidade = Cidade.objects.filter(id=cidade_id, empresa=empresa).first() if cidade_id else None
    if not nome:
        return "Nome do parceiro é obrigatório."
    if not codigo:
        return "Código do parceiro é obrigatório."
    if cidade_id and not cidade:
        return "Cidade inválida para o parceiro."
    if Parceiro.objects.filter(codigo=codigo).exclude(empresa=empresa).exists():
        return "Já existe parceiro com este código em outra empresa."
    if Parceiro.objects.filter(empresa=empresa, codigo=codigo).exists():
        return "Já existe parceiro com este código nesta empresa."
    Parceiro.criar_parceiro(nome=nome, codigo=codigo, empresa=empresa, cidade=cidade)
    return ""


def atualizar_parceiro_por_dados(parceiro, nome, codigo, empresa, cidade_id=None):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    cidade = Cidade.objects.filter(id=cidade_id, empresa=empresa).first() if cidade_id else None
    if not nome:
        return "Nome do parceiro é obrigatório."
    if not codigo:
        return "Código do parceiro é obrigatório."
    if cidade_id and not cidade:
        return "Cidade inválida para o parceiro."
    if Parceiro.objects.filter(codigo=codigo).exclude(id=parceiro.id).exclude(empresa=empresa).exists():
        return "Já existe parceiro com este código em outra empresa."
    if Parceiro.objects.filter(empresa=empresa, codigo=codigo).exclude(id=parceiro.id).exists():
        return "Já existe parceiro com este código nesta empresa."
    parceiro.atualizar_parceiro(novo_nome=nome, novo_codigo=codigo, cidade=cidade)
    return ""


def criar_motorista_por_dados(empresa, codigo_motorista, nome):
    codigo_motorista = (codigo_motorista or "").strip()
    nome = (nome or "").strip()
    if not codigo_motorista:
        return "Código do motorista é obrigatório."
    if not nome:
        return "Nome do motorista é obrigatório."
    if Motorista.objects.filter(codigo_motorista=codigo_motorista).exclude(empresa=empresa).exists():
        return "Já existe motorista com este código em outra empresa."
    if Motorista.objects.filter(empresa=empresa, codigo_motorista=codigo_motorista).exists():
        return "Já existe motorista com este código nesta empresa."
    Motorista.criar_motorista(empresa=empresa, codigo_motorista=codigo_motorista, nome=nome)
    return ""


def atualizar_motorista_por_dados(motorista, codigo_motorista, nome, empresa):
    codigo_motorista = (codigo_motorista or "").strip()
    nome = (nome or "").strip()
    if not codigo_motorista:
        return "Código do motorista é obrigatório."
    if not nome:
        return "Nome do motorista é obrigatório."
    if Motorista.objects.filter(codigo_motorista=codigo_motorista).exclude(id=motorista.id).exclude(empresa=empresa).exists():
        return "Já existe motorista com este código em outra empresa."
    if Motorista.objects.filter(empresa=empresa, codigo_motorista=codigo_motorista).exclude(id=motorista.id).exists():
        return "Já existe motorista com este código nesta empresa."
    motorista.atualizar_motorista(codigo_motorista=codigo_motorista, nome=nome)
    return ""


def criar_transportadora_por_dados(empresa, codigo_transportadora, nome):
    codigo_transportadora = (codigo_transportadora or "").strip()
    nome = (nome or "").strip()
    if not codigo_transportadora:
        return "Código da transportadora é obrigatório."
    if not nome:
        return "Nome da transportadora é obrigatório."
    if Transportadora.objects.filter(codigo_transportadora=codigo_transportadora).exclude(empresa=empresa).exists():
        return "Já existe transportadora com este código em outra empresa."
    if Transportadora.objects.filter(empresa=empresa, codigo_transportadora=codigo_transportadora).exists():
        return "Já existe transportadora com este código nesta empresa."
    Transportadora.criar_transportadora(
        empresa=empresa,
        codigo_transportadora=codigo_transportadora,
        nome=nome,
    )
    return ""


def atualizar_transportadora_por_dados(transportadora, codigo_transportadora, nome, empresa):
    codigo_transportadora = (codigo_transportadora or "").strip()
    nome = (nome or "").strip()
    if not codigo_transportadora:
        return "Código da transportadora é obrigatório."
    if not nome:
        return "Nome da transportadora é obrigatório."
    if Transportadora.objects.filter(codigo_transportadora=codigo_transportadora).exclude(id=transportadora.id).exclude(empresa=empresa).exists():
        return "Já existe transportadora com este código em outra empresa."
    if Transportadora.objects.filter(empresa=empresa, codigo_transportadora=codigo_transportadora).exclude(id=transportadora.id).exists():
        return "Já existe transportadora com este código nesta empresa."
    transportadora.atualizar_transportadora(codigo_transportadora=codigo_transportadora, nome=nome)
    return ""

def _dados_produto_from_post(post_data):
    horas = _parse_decimal_ou_zero(post_data.get("horas"))
    setup = _parse_decimal_ou_zero(post_data.get("setup"))
    ppm = _parse_decimal_ou_zero(post_data.get("ppm"))
    pacote_por_fardo = _parse_decimal_ou_zero(post_data.get("pacote_por_fardo"))
    empacotadeiras = _parse_decimal_ou_zero(post_data.get("empacotadeiras"))

    horas_uteis = horas - setup
    if horas_uteis < 0:
        horas_uteis = Decimal("0")

    producao_por_dia_fd = Decimal("0")
    if pacote_por_fardo > 0 and horas_uteis > 0 and empacotadeiras > 0 and ppm > 0:
        producao_por_dia_fd = (ppm / pacote_por_fardo) * Decimal("60") * horas_uteis * empacotadeiras

    return {
        "codigo_produto": (post_data.get("codigo_produto") or "").strip(),
        "descricao_produto": (post_data.get("descricao_produto") or "").strip(),
        "status": (post_data.get("status") or "Ativo").strip() or "Ativo",
        "kg": _parse_decimal_ou_zero(post_data.get("kg")),
        "remuneracao_por_fardo": _parse_decimal_ou_zero(post_data.get("remuneracao_por_fardo")),
        "ppm": ppm,
        "peso_kg": _parse_decimal_ou_zero(post_data.get("peso_kg")),
        "pacote_por_fardo": pacote_por_fardo,
        "turno": _parse_decimal_ou_zero(post_data.get("turno")),
        "horas": horas,
        "setup": setup,
        "horas_uteis": horas_uteis,
        "empacotadeiras": empacotadeiras,
        "producao_por_dia_fd": producao_por_dia_fd,
        "estoque_minimo_pacote": _parse_decimal_ou_zero(post_data.get("estoque_minimo_pacote")),
    }


def criar_produto_por_dados(empresa, post_data):
    dados = _dados_produto_from_post(post_data)
    codigo_produto = dados["codigo_produto"]
    if not codigo_produto:
        return "Codigo do produto e obrigatorio."
    if Produto.objects.filter(codigo_produto=codigo_produto).exclude(empresa=empresa).exists():
        return "Ja existe produto com este codigo em outra empresa."
    if Produto.objects.filter(empresa=empresa, codigo_produto=codigo_produto).exists():
        return "Ja existe produto com este codigo nesta empresa."
    Produto.criar_produto(empresa=empresa, **dados)
    return ""


def atualizar_produto_por_dados(produto, post_data, empresa):
    dados = _dados_produto_from_post(post_data)
    codigo_produto = dados["codigo_produto"]
    if not codigo_produto:
        return "Codigo do produto e obrigatorio."
    if Produto.objects.filter(codigo_produto=codigo_produto).exclude(id=produto.id).exclude(empresa=empresa).exists():
        return "Ja existe produto com este codigo em outra empresa."
    if Produto.objects.filter(empresa=empresa, codigo_produto=codigo_produto).exclude(id=produto.id).exists():
        return "Ja existe produto com este codigo nesta empresa."
    produto.atualizar_produto(**dados)
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

def criar_centro_resultado_por_dados(empresa, descricao):
    descricao = (descricao or "").strip()
    if not descricao:
        return "Descricao do centro resultado e obrigatoria."
    if not any(ch.isalpha() for ch in descricao):
        return "Descricao do centro resultado deve conter texto (nao apenas numeros)."
    if CentroResultado.objects.filter(descricao=descricao).exclude(empresa=empresa).exists():
        return "Ja existe centro resultado com esta descricao em outra empresa."
    if CentroResultado.objects.filter(empresa=empresa, descricao=descricao).exists():
        return "Ja existe centro resultado com esta descricao nesta empresa."
    CentroResultado.criar_centro_resultado(empresa=empresa, descricao=descricao)
    return ""


def atualizar_centro_resultado_por_dados(centro_resultado, descricao, empresa):
    descricao = (descricao or "").strip()
    if not descricao:
        return "Descricao do centro resultado e obrigatoria."
    if not any(ch.isalpha() for ch in descricao):
        return "Descricao do centro resultado deve conter texto (nao apenas numeros)."
    if CentroResultado.objects.filter(descricao=descricao).exclude(id=centro_resultado.id).exclude(empresa=empresa).exists():
        return "Ja existe centro resultado com esta descricao em outra empresa."
    if CentroResultado.objects.filter(empresa=empresa, descricao=descricao).exclude(id=centro_resultado.id).exists():
        return "Ja existe centro resultado com esta descricao nesta empresa."
    centro_resultado.atualizar_centro_resultado(descricao=descricao)
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


def _parse_percentual_ratio_ou_zero(valor):
    texto = (valor or "").strip()
    if not texto:
        return Decimal("0")
    tem_percentual = "%" in texto
    numero = _parse_decimal_ou_zero(texto.replace("%", ""))
    if tem_percentual:
        return numero / Decimal("100")
    return numero


def _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(valor):
    texto = (valor or "").strip()
    if not texto:
        return Decimal("0")

    tem_percentual = "%" in texto
    numero = _parse_decimal_ou_zero(texto.replace("%", ""))
    if tem_percentual:
        return numero / Decimal("100")
    if numero.copy_abs() > Decimal("1"):
        return numero / Decimal("100")
    if numero.copy_abs() >= Decimal("0.1"):
        return numero / Decimal("100")
    return numero


def _parse_date_ou_none(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_datetime_ou_none(valor):
    if not valor:
        return None
    texto = (valor or "").strip()
    formatos = (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato)
        except (TypeError, ValueError):
            continue
    return None


def _parse_int_ou_zero(valor):
    if valor in (None, ""):
        return 0
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _parse_int64_ou_zero(valor):
    numero = _parse_decimal_ou_zero(valor)
    try:
        numero = numero.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return 0
    try:
        return int(numero)
    except (TypeError, ValueError):
        return 0


def _parse_bool_checkbox(post_data, campo):
    return post_data.get(campo) == "on"


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


def _extrair_kg_da_descricao_produto(descricao: str) -> Decimal:
    texto = (descricao or "").strip().upper()
    if not texto:
        return Decimal("0")

    match_multiplicado = re.search(r"(\d+)\s*[Xx]\s*(\d+)\s*KG", texto)
    if match_multiplicado:
        return Decimal(match_multiplicado.group(1)) * Decimal(match_multiplicado.group(2))

    match_simples = re.search(r"(\d+)\s*KG", texto)
    if match_simples:
        return Decimal(match_simples.group(1))

    return Decimal("0")


def _calcular_metricas_producao_auto(produto, tamanho_lote_texto):
    kg = Decimal("0")
    producao_por_dia = Decimal("0")
    if produto:
        if produto.kg and produto.kg > 0:
            kg = produto.kg
        if produto.producao_por_dia_fd and produto.producao_por_dia_fd > 0:
            producao_por_dia = produto.producao_por_dia_fd
    tamanho_lote = _parse_decimal_ou_zero(tamanho_lote_texto)
    kg_por_lote = (tamanho_lote / kg) if (kg > 0 and tamanho_lote > 0) else Decimal("0")
    return kg, producao_por_dia, kg_por_lote


def _dados_agenda_from_post(post_data, empresa):
    data_registro_raw = post_data.get("data_registro")
    data_registro = _parse_date_ou_none(data_registro_raw)

    previsao_carregamento_raw = post_data.get("previsao_carregamento")
    previsao_carregamento = _parse_date_ou_none(previsao_carregamento_raw)

    motorista = Motorista.objects.filter(id=post_data.get("motorista_id"), empresa=empresa).first()
    transportadora = Transportadora.objects.filter(id=post_data.get("transportadora_id"), empresa=empresa).first()

    return {
        "data_registro_raw": data_registro_raw,
        "data_registro": data_registro,
        "numero_unico": (post_data.get("numero_unico") or "").strip(),
        "previsao_carregamento_raw": previsao_carregamento_raw,
        "previsao_carregamento": previsao_carregamento,
        "motorista": motorista,
        "transportadora": transportadora,
    }


def _dados_pedido_pendente_from_post(post_data, empresa):
    rota = Rota.objects.filter(id=post_data.get("rota_id"), empresa=empresa).first()
    regiao = Regiao.objects.filter(id=post_data.get("regiao_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()
    data_para_calculo_raw = post_data.get("data_para_calculo")

    def _normalizar_pendente(valor_raw):
        texto = (valor_raw or "").strip().lower()
        if texto in {"sim", "s", "yes", "y", "1", "true"}:
            return "Sim"
        if texto in {"nao", "não", "n", "no", "0", "false"}:
            return "Não"
        return "Sim"

    dados = {
        "numero_unico": _normalizar_numero_unico_texto(post_data.get("numero_unico")),
        "rota": rota,
        "regiao": regiao,
        "parceiro": parceiro,
        "rota_texto": (post_data.get("rota_texto") or "").strip(),
        "regiao_texto": (post_data.get("regiao_texto") or "").strip(),
        "valor_tonelada_frete_safia": (post_data.get("valor_tonelada_frete_safia") or "").strip(),
        "pendente": _normalizar_pendente(post_data.get("pendente")),
        "nome_cidade_parceiro_safia": (post_data.get("nome_cidade_parceiro_safia") or "").strip(),
        "previsao_entrega": _parse_date_ou_none(post_data.get("previsao_entrega")),
        "dt_neg": _parse_date_ou_none(post_data.get("dt_neg")),
        "prazo_maximo": max(0, _parse_int_ou_zero(post_data.get("prazo_maximo"))),
        "tipo_venda": (post_data.get("tipo_venda") or "").strip(),
        "nome_empresa": (post_data.get("nome_empresa") or "").strip(),
        "cod_nome_parceiro": (post_data.get("cod_nome_parceiro") or "").strip(),
        "vlr_nota": _parse_decimal_ou_zero(post_data.get("vlr_nota")),
        "peso_bruto": _parse_decimal_ou_zero(post_data.get("peso_bruto")),
        "peso": _parse_decimal_ou_zero(post_data.get("peso")),
        "peso_liq_itens": _parse_decimal_ou_zero(post_data.get("peso_liq_itens")),
        "apelido_vendedor": (post_data.get("apelido_vendedor") or "").strip(),
        "gerente": (post_data.get("gerente") or "").strip(),
        "data_para_calculo_raw": data_para_calculo_raw,
        "data_para_calculo": _parse_date_ou_none(data_para_calculo_raw),
        "descricao_tipo_negociacao": (post_data.get("descricao_tipo_negociacao") or "").strip(),
        "nro_nota": _parse_int_ou_zero(post_data.get("nro_nota")),
    }

    if not dados["rota_texto"] and rota:
        dados["rota_texto"] = f"{rota.codigo_rota} - {rota.nome}"

    if not dados["regiao_texto"] and regiao:
        dados["regiao_texto"] = f"{regiao.codigo} - {regiao.nome}"

    if not dados["cod_nome_parceiro"] and parceiro:
        dados["cod_nome_parceiro"] = f"{parceiro.codigo} - {parceiro.nome}"

    if not dados["nome_cidade_parceiro_safia"] and parceiro and parceiro.cidade:
        dados["nome_cidade_parceiro_safia"] = parceiro.cidade.nome

    if not dados["data_para_calculo"]:
        dados["data_para_calculo"] = dados["previsao_entrega"] or dados["dt_neg"]

    return dados


def criar_agenda_por_post(empresa, post_data):
    dados = _dados_agenda_from_post(post_data, empresa)
    dados["numero_unico"] = _normalizar_numero_unico_texto(dados["numero_unico"])
    if not dados["numero_unico"]:
        return "Número único é obrigatório."
    if not dados["previsao_carregamento_raw"]:
        return "Previsão de carregamento é obrigatória."
    if not dados["previsao_carregamento"]:
        return "Previsão de carregamento inválida."
    if not dados["motorista"]:
        return "Motorista é obrigatório."
    if not dados["transportadora"]:
        return "Transportadora é obrigatória."
    if Agenda.objects.filter(numero_unico=dados["numero_unico"]).exclude(empresa=empresa).exists():
        return "Já existe agenda com este número único em outra empresa."
    if Agenda.objects.filter(empresa=empresa, numero_unico=dados["numero_unico"]).exists():
        return "Já existe agenda com este número único nesta empresa."
    data_registro = dados["data_registro"] or timezone.localdate()
    Agenda.criar_agenda(
        empresa=empresa,
        data_registro=data_registro,
        numero_unico=dados["numero_unico"],
        previsao_carregamento=dados["previsao_carregamento"],
        motorista=dados["motorista"],
        transportadora=dados["transportadora"],
    )
    return ""


def atualizar_agenda_por_post(agenda, empresa, post_data):
    dados = _dados_agenda_from_post(post_data, empresa)
    dados["numero_unico"] = _normalizar_numero_unico_texto(dados["numero_unico"])
    if not dados["numero_unico"]:
        return "Número único é obrigatório."
    if not dados["previsao_carregamento_raw"]:
        return "Previsão de carregamento é obrigatória."
    if not dados["previsao_carregamento"]:
        return "Previsão de carregamento inválida."
    if not dados["motorista"]:
        return "Motorista é obrigatório."
    if not dados["transportadora"]:
        return "Transportadora é obrigatória."
    if Agenda.objects.filter(numero_unico=dados["numero_unico"]).exclude(id=agenda.id).exclude(empresa=empresa).exists():
        return "Já existe agenda com este número único em outra empresa."
    if Agenda.objects.filter(empresa=empresa, numero_unico=dados["numero_unico"]).exclude(id=agenda.id).exists():
        return "Já existe agenda com este número único nesta empresa."
    data_registro = dados["data_registro"] or agenda.data_registro
    agenda.atualizar_agenda(
        data_registro=data_registro,
        numero_unico=dados["numero_unico"],
        previsao_carregamento=dados["previsao_carregamento"],
        motorista=dados["motorista"],
        transportadora=dados["transportadora"],
    )
    return ""


def atualizar_pedido_pendente_por_post(pedido, empresa, post_data):
    dados = _dados_pedido_pendente_from_post(post_data, empresa)
    if not dados["numero_unico"]:
        return "Número único é obrigatório."
    if PedidoPendente.objects.filter(
        empresa=empresa,
        numero_unico=dados["numero_unico"],
    ).exclude(id=pedido.id).exists():
        return "Já existe pedido pendente com este número único nesta empresa."

    data_para_calculo = dados["data_para_calculo"]
    if dados["data_para_calculo_raw"] and not data_para_calculo:
        return "Data para cálculo inválida."

    dados.pop("data_para_calculo_raw", None)
    dados["data_para_calculo"] = data_para_calculo
    pedido.atualizar_pedido_pendente(**dados)
    return ""


def criar_pedido_pendente_por_post(empresa, post_data):
    dados = _dados_pedido_pendente_from_post(post_data, empresa)
    if not dados["numero_unico"]:
        return "Numero unico e obrigatorio."
    if PedidoPendente.objects.filter(empresa=empresa, numero_unico=dados["numero_unico"]).exists():
        return "Ja existe pedido pendente com este numero unico nesta empresa."

    data_para_calculo = dados["data_para_calculo"]
    if dados["data_para_calculo_raw"] and not data_para_calculo:
        return "Data para calculo invalida."

    dados.pop("data_para_calculo_raw", None)
    dados["data_para_calculo"] = data_para_calculo
    PedidoPendente.criar_pedido_pendente(empresa=empresa, **dados)
    return ""


def _dados_controle_margem_from_post(post_data, empresa):
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()
    nro_unico_raw = (post_data.get("nro_unico") or "").strip()
    data_origem = (post_data.get("data_origem") or "").strip()
    vlr_nota = _parse_decimal_ou_zero(post_data.get("vlr_nota"))
    custo_total_produto = _parse_decimal_ou_zero(post_data.get("custo_total_produto"))
    peso_bruto = _parse_decimal_ou_zero(post_data.get("peso_bruto"))
    nome_empresa = (post_data.get("nome_empresa") or "").strip()
    gerente = (post_data.get("gerente") or "").strip() or None
    tipo_venda = (post_data.get("tipo_venda") or "").strip() or None
    valor_tonelada_frete_safia = _parse_decimal_ou_zero(post_data.get("valor_tonelada_frete_safia"))
    parametros = obter_parametros_controle_margem(empresa)
    campos_calculados = calcular_campos_controle_margem_legado(
        nome_empresa=nome_empresa,
        gerente=gerente,
        tipo_venda=tipo_venda,
        vlr_nota=vlr_nota,
        custo_total_produto=custo_total_produto,
        peso_bruto=peso_bruto,
        valor_tonelada_frete_safia=valor_tonelada_frete_safia,
        taxa_vendas_percentual=parametros["vendas"].remuneracao_percentual,
        taxa_operador_logistica_rs=parametros["logistica"].remuneracao_rs,
        taxa_administracao_percentual=parametros["administracao"].remuneracao_percentual,
        taxa_financeiro_mes=parametros["financeiro"].taxa_ao_mes,
    )
    cod_nome_parceiro = (post_data.get("cod_nome_parceiro") or "").strip()
    if not cod_nome_parceiro and parceiro:
        cod_nome_parceiro = f"{parceiro.codigo} - {parceiro.nome}"

    return {
        "nro_unico_raw": nro_unico_raw,
        "nro_unico": _parse_int_ou_zero(nro_unico_raw),
        "data_origem": data_origem,
        "nome_empresa": nome_empresa,
        "parceiro": parceiro,
        "cod_nome_parceiro": cod_nome_parceiro,
        "descricao_perfil": (post_data.get("descricao_perfil") or "").strip() or None,
        "apelido_vendedor": (post_data.get("apelido_vendedor") or "").strip() or None,
        "gerente": gerente,
        "dt_neg_raw": (post_data.get("dt_neg") or "").strip(),
        "dt_neg": _parse_date_ou_none(post_data.get("dt_neg")),
        "previsao_entrega_raw": (post_data.get("previsao_entrega") or "").strip(),
        "previsao_entrega": _parse_date_ou_none(post_data.get("previsao_entrega")),
        "tipo_venda": tipo_venda,
        "vlr_nota": vlr_nota,
        "custo_total_produto": custo_total_produto,
        "margem_bruta": campos_calculados["margem_bruta"],
        "lucro_bruto": campos_calculados["lucro_bruto"],
        "valor_tonelada_frete_safia": valor_tonelada_frete_safia,
        "peso_bruto": peso_bruto,
        "custo_por_kg": campos_calculados["custo_por_kg"],
        "vendas": campos_calculados["vendas"],
        "producao": campos_calculados["producao"],
        "operador_logistica": campos_calculados["operador_logistica"],
        "frete_distribuicao": campos_calculados["frete_distribuicao"],
        "total_logistica": campos_calculados["total_logistica"],
        "administracao": campos_calculados["administracao"],
        "financeiro": campos_calculados["financeiro"],
        "total_setores": campos_calculados["total_setores"],
        "valor_liquido": campos_calculados["valor_liquido"],
        "margem_liquida": campos_calculados["margem_liquida"],
    }


def criar_controle_margem_por_post(empresa, post_data):
    dados = _dados_controle_margem_from_post(post_data, empresa)
    if not dados["data_origem"]:
        return "Data origem e obrigatoria."
    if not dados["nro_unico_raw"]:
        return "Nro. Unico e obrigatorio."
    if dados["nro_unico"] <= 0:
        return "Nro. Unico invalido."
    if dados["dt_neg_raw"] and not dados["dt_neg"]:
        return "Dt. Neg. invalida."
    if dados["previsao_entrega_raw"] and not dados["previsao_entrega"]:
        return "Previsao de entrega invalida."
    if ControleMargem.objects.filter(empresa=empresa, nro_unico=dados["nro_unico"]).exists():
        return "Ja existe controle de margem com este Nro. Unico nesta empresa."

    dados.pop("nro_unico_raw", None)
    dados.pop("dt_neg_raw", None)
    dados.pop("previsao_entrega_raw", None)
    ControleMargem.criar_controle_margem(empresa=empresa, **dados)
    return ""


def atualizar_controle_margem_por_post(controle, empresa, post_data):
    dados = _dados_controle_margem_from_post(post_data, empresa)
    if not dados["data_origem"]:
        return "Data origem e obrigatoria."
    if not dados["nro_unico_raw"]:
        return "Nro. Unico e obrigatorio."
    if dados["nro_unico"] <= 0:
        return "Nro. Unico invalido."
    if dados["dt_neg_raw"] and not dados["dt_neg"]:
        return "Dt. Neg. invalida."
    if dados["previsao_entrega_raw"] and not dados["previsao_entrega"]:
        return "Previsao de entrega invalida."
    if ControleMargem.objects.filter(empresa=empresa, nro_unico=dados["nro_unico"]).exclude(id=controle.id).exists():
        return "Ja existe controle de margem com este Nro. Unico nesta empresa."

    dados.pop("nro_unico_raw", None)
    dados.pop("dt_neg_raw", None)
    dados.pop("previsao_entrega_raw", None)
    controle.atualizar_controle_margem(**dados)
    return ""


def recalcular_controle_margem_por_empresa(empresa):
    parametros = obter_parametros_controle_margem(empresa)
    itens = list(ControleMargem.objects.filter(empresa=empresa))
    if not itens:
        return 0

    for item in itens:
        calculados = calcular_campos_controle_margem_legado(
            nome_empresa=item.nome_empresa,
            gerente=item.gerente,
            tipo_venda=item.tipo_venda,
            vlr_nota=item.vlr_nota,
            custo_total_produto=item.custo_total_produto,
            peso_bruto=item.peso_bruto,
            valor_tonelada_frete_safia=item.valor_tonelada_frete_safia,
            taxa_vendas_percentual=parametros["vendas"].remuneracao_percentual,
            taxa_operador_logistica_rs=parametros["logistica"].remuneracao_rs,
            taxa_administracao_percentual=parametros["administracao"].remuneracao_percentual,
            taxa_financeiro_mes=parametros["financeiro"].taxa_ao_mes,
        )
        item.lucro_bruto = calculados["lucro_bruto"]
        item.margem_bruta = calculados["margem_bruta"]
        item.custo_por_kg = calculados["custo_por_kg"]
        item.vendas = calculados["vendas"]
        item.producao = calculados["producao"]
        item.operador_logistica = calculados["operador_logistica"]
        item.frete_distribuicao = calculados["frete_distribuicao"]
        item.total_logistica = calculados["total_logistica"]
        item.administracao = calculados["administracao"]
        item.financeiro = calculados["financeiro"]
        item.total_setores = calculados["total_setores"]
        item.valor_liquido = calculados["valor_liquido"]
        item.margem_liquida = calculados["margem_liquida"]

    ControleMargem.objects.bulk_update(
        itens,
        [
            "lucro_bruto",
            "margem_bruta",
            "custo_por_kg",
            "vendas",
            "producao",
            "operador_logistica",
            "frete_distribuicao",
            "total_logistica",
            "administracao",
            "financeiro",
            "total_setores",
            "valor_liquido",
            "margem_liquida",
        ],
        batch_size=1000,
    )
    return len(itens)


def criar_parametro_margem_vendas(empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    criterio = (post_data.get("criterio") or "").strip()
    remuneracao_percentual = _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(
        post_data.get("remuneracao_percentual")
    )
    if not parametro:
        return "Parametro e obrigatorio.", 0
    if not criterio:
        return "Criterio e obrigatorio.", 0
    ParametroMargemVendas.objects.create(
        empresa=empresa,
        parametro=parametro,
        criterio=criterio,
        remuneracao_percentual=remuneracao_percentual,
    )
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def atualizar_parametro_margem_vendas(item, empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    criterio = (post_data.get("criterio") or "").strip()
    remuneracao_percentual = _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(
        post_data.get("remuneracao_percentual")
    )
    if not parametro:
        return "Parametro e obrigatorio.", 0
    if not criterio:
        return "Criterio e obrigatorio.", 0
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.parametro = parametro
    item.criterio = criterio
    item.remuneracao_percentual = remuneracao_percentual
    item.save(update_fields=["parametro", "criterio", "remuneracao_percentual"])
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def excluir_parametro_margem_vendas(item, empresa):
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.delete()
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def criar_parametro_margem_logistica(empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    criterio = (post_data.get("criterio") or "").strip()
    remuneracao_rs = _parse_decimal_ou_zero(post_data.get("remuneracao_rs"))
    if not parametro:
        return "Parametro e obrigatorio.", 0
    if not criterio:
        return "Criterio e obrigatorio.", 0
    ParametroMargemLogistica.objects.create(
        empresa=empresa,
        parametro=parametro,
        criterio=criterio,
        remuneracao_rs=remuneracao_rs,
    )
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def atualizar_parametro_margem_logistica(item, empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    criterio = (post_data.get("criterio") or "").strip()
    remuneracao_rs = _parse_decimal_ou_zero(post_data.get("remuneracao_rs"))
    if not parametro:
        return "Parametro e obrigatorio.", 0
    if not criterio:
        return "Criterio e obrigatorio.", 0
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.parametro = parametro
    item.criterio = criterio
    item.remuneracao_rs = remuneracao_rs
    item.save(update_fields=["parametro", "criterio", "remuneracao_rs"])
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def excluir_parametro_margem_logistica(item, empresa):
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.delete()
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def salvar_parametro_margem_administracao(empresa, post_data):
    parametro, _ = ParametroMargemAdministracao.objects.get_or_create(empresa=empresa)
    parametro.parametro = (post_data.get("parametro") or "Administracao").strip() or "Administracao"
    parametro.remuneracao_percentual = _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(
        post_data.get("remuneracao_percentual")
    )
    parametro.save(update_fields=["parametro", "remuneracao_percentual"])
    return recalcular_controle_margem_por_empresa(empresa)


def criar_parametro_margem_financeiro(empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    taxa_ao_mes = _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(post_data.get("taxa_ao_mes"))
    remuneracao_percentual = taxa_ao_mes / Decimal("30")
    if not parametro:
        return "Parametro e obrigatorio.", 0
    ParametroMargemFinanceiro.objects.create(
        empresa=empresa,
        parametro=parametro,
        taxa_ao_mes=taxa_ao_mes,
        remuneracao_percentual=remuneracao_percentual,
    )
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def atualizar_parametro_margem_financeiro(item, empresa, post_data):
    parametro = (post_data.get("parametro") or "").strip()
    taxa_ao_mes = _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(post_data.get("taxa_ao_mes"))
    remuneracao_percentual = taxa_ao_mes / Decimal("30")
    if not parametro:
        return "Parametro e obrigatorio.", 0
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.parametro = parametro
    item.taxa_ao_mes = taxa_ao_mes
    item.remuneracao_percentual = remuneracao_percentual
    item.save(update_fields=["parametro", "taxa_ao_mes", "remuneracao_percentual"])
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


def excluir_parametro_margem_financeiro(item, empresa):
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa.", 0
    item.delete()
    total = recalcular_controle_margem_por_empresa(empresa)
    return "", total


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
    centro_resultado = CentroResultado.objects.filter(id=post_data.get("centro_resultado_id"), empresa=empresa).first()
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
        "centro_resultado": centro_resultado,
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


def _dados_adiantamento_from_post(post_data):
    return {
        "moeda": (post_data.get("moeda") or "").strip(),
        "saldo_banco_em_reais": _parse_decimal_ou_zero(post_data.get("saldo_banco_em_reais")),
        "saldo_real_em_reais": _parse_decimal_ou_zero(post_data.get("saldo_real_em_reais")),
        "saldo_real": _parse_decimal_ou_zero(post_data.get("saldo_real")),
        "conta_descricao": (post_data.get("conta_descricao") or "").strip(),
        "saldo_banco": _parse_int64_ou_zero(post_data.get("saldo_banco")),
        "banco": (post_data.get("banco") or "").strip(),
        "agencia": (post_data.get("agencia") or "").strip(),
        "conta_bancaria": (post_data.get("conta_bancaria") or "").strip(),
        "empresa_descricao": (post_data.get("empresa_descricao") or "").strip(),
    }


def criar_adiantamento_por_post(empresa, post_data):
    dados = _dados_adiantamento_from_post(post_data)
    if not dados["conta_descricao"]:
        return "Conta Descricao e obrigatoria."
    Adiantamento.criar_adiantamento(empresa=empresa, **dados)
    return ""


def atualizar_adiantamento_por_post(adiantamento_item, post_data):
    dados = _dados_adiantamento_from_post(post_data)
    if not dados["conta_descricao"]:
        return "Conta Descricao e obrigatoria."
    adiantamento_item.atualizar_adiantamento(**dados)
    return ""


def _dados_contas_a_receber_from_post(post_data, empresa):
    titulo = Titulo.objects.filter(id=post_data.get("titulo_id"), empresa=empresa).first()
    natureza = Natureza.objects.filter(id=post_data.get("natureza_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()
    operacao = Operacao.objects.filter(id=post_data.get("operacao_id"), empresa=empresa).first()
    centro_resultado = CentroResultado.objects.filter(id=post_data.get("centro_resultado_id"), empresa=empresa).first()
    data_negociacao_raw = post_data.get("data_negociacao")
    data_vencimento_raw = post_data.get("data_vencimento")
    data_arquivo_raw = post_data.get("data_arquivo")

    return {
        "data_negociacao_raw": data_negociacao_raw,
        "data_vencimento_raw": data_vencimento_raw,
        "data_arquivo_raw": data_arquivo_raw,
        "data_negociacao": _parse_date_ou_none(data_negociacao_raw),
        "data_vencimento": _parse_date_ou_none(data_vencimento_raw),
        "data_arquivo": _parse_date_ou_none(data_arquivo_raw),
        "nome_fantasia_empresa": (post_data.get("nome_fantasia_empresa") or "").strip(),
        "parceiro": parceiro,
        "numero_nota": (post_data.get("numero_nota") or "").strip(),
        "vendedor": (post_data.get("vendedor") or "").strip(),
        "valor_desdobramento": _parse_decimal_ou_zero(post_data.get("valor_desdobramento")),
        "valor_liquido": _parse_decimal_ou_zero(post_data.get("valor_liquido")),
        "titulo": titulo,
        "natureza": natureza,
        "centro_resultado": centro_resultado,
        "operacao": operacao,
    }


def criar_contas_a_receber_por_post(empresa, post_data):
    dados = _dados_contas_a_receber_from_post(post_data, empresa)
    if not dados["data_negociacao_raw"]:
        return "Data de negociacao e obrigatoria."
    if not dados["data_negociacao"]:
        return "Data de negociacao invalida."
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    if dados["data_arquivo_raw"] and not dados["data_arquivo"]:
        return "Data arquivo invalida."
    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    dados.pop("data_arquivo_raw", None)
    ContasAReceber.criar_conta_a_receber(empresa=empresa, **dados)
    return ""


def atualizar_contas_a_receber_por_post(conta_item, empresa, post_data):
    dados = _dados_contas_a_receber_from_post(post_data, empresa)
    if not dados["data_negociacao_raw"]:
        return "Data de negociacao e obrigatoria."
    if not dados["data_negociacao"]:
        return "Data de negociacao invalida."
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    if dados["data_arquivo_raw"] and not dados["data_arquivo"]:
        return "Data arquivo invalida."
    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    dados.pop("data_arquivo_raw", None)
    conta_item.atualizar_conta_a_receber(**dados)
    return ""


def _dados_orcamento_from_post(post_data, empresa):
    titulo = Titulo.objects.filter(id=post_data.get("titulo_id"), empresa=empresa).first()
    natureza = Natureza.objects.filter(id=post_data.get("natureza_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()
    operacao = Operacao.objects.filter(id=post_data.get("operacao_id"), empresa=empresa).first()
    centro_resultado = CentroResultado.objects.filter(id=post_data.get("centro_resultado_id"), empresa=empresa).first()
    centro_resultado_id_raw = (post_data.get("centro_resultado_id") or "").strip()
    data_vencimento_raw = post_data.get("data_vencimento")
    data_baixa_raw = post_data.get("data_baixa")

    return {
        "nome_empresa": (post_data.get("nome_empresa") or "").strip(),
        "data_vencimento_raw": data_vencimento_raw,
        "data_baixa_raw": data_baixa_raw,
        "data_vencimento": _parse_date_ou_none(data_vencimento_raw),
        "data_baixa": _parse_date_ou_none(data_baixa_raw),
        "valor_baixa": _parse_decimal_ou_zero(post_data.get("valor_baixa")),
        "valor_liquido": _parse_decimal_ou_zero(post_data.get("valor_liquido")),
        "valor_desdobramento": _parse_decimal_ou_zero(post_data.get("valor_desdobramento")),
        "titulo": titulo,
        "natureza": natureza,
        "centro_resultado": centro_resultado,
        "centro_resultado_id_raw": centro_resultado_id_raw,
        "operacao": operacao,
        "parceiro": parceiro,
    }


def criar_orcamento_por_post(empresa, post_data):
    dados = _dados_orcamento_from_post(post_data, empresa)
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    if not dados["data_baixa_raw"]:
        return "Data de baixa e obrigatoria."
    if not dados["data_baixa"]:
        return "Data de baixa invalida."
    if not dados["centro_resultado_id_raw"]:
        return "Centro de resultado e obrigatorio."
    if not dados["centro_resultado"]:
        return "Centro de resultado invalido."
    dados.pop("data_vencimento_raw", None)
    dados.pop("data_baixa_raw", None)
    dados.pop("centro_resultado_id_raw", None)
    Orcamento.criar_orcamento(empresa=empresa, **dados)
    return ""


def atualizar_orcamento_por_post(orcamento_item, empresa, post_data):
    dados = _dados_orcamento_from_post(post_data, empresa)
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    if not dados["data_baixa_raw"]:
        return "Data de baixa e obrigatoria."
    if not dados["data_baixa"]:
        return "Data de baixa invalida."
    if not dados["centro_resultado_id_raw"]:
        return "Centro de resultado e obrigatorio."
    if not dados["centro_resultado"]:
        return "Centro de resultado invalido."
    dados.pop("data_vencimento_raw", None)
    dados.pop("data_baixa_raw", None)
    dados.pop("centro_resultado_id_raw", None)
    orcamento_item.atualizar_orcamento(**dados)
    return ""


def _dados_orcamento_planejado_from_post(post_data, empresa):
    natureza = Natureza.objects.filter(id=post_data.get("natureza_id"), empresa=empresa).first()
    centro_resultado = CentroResultado.objects.filter(id=post_data.get("centro_resultado_id"), empresa=empresa).first()
    ano_raw = (post_data.get("ano") or "").strip()
    return {
        "nome_empresa": (post_data.get("nome_empresa") or "").strip(),
        "ano_raw": ano_raw,
        "ano": _parse_int_ou_zero(ano_raw),
        "natureza": natureza,
        "centro_resultado": centro_resultado,
        "janeiro": _parse_decimal_ou_zero(post_data.get("janeiro")),
        "fevereiro": _parse_decimal_ou_zero(post_data.get("fevereiro")),
        "marco": _parse_decimal_ou_zero(post_data.get("marco")),
        "abril": _parse_decimal_ou_zero(post_data.get("abril")),
        "maio": _parse_decimal_ou_zero(post_data.get("maio")),
        "junho": _parse_decimal_ou_zero(post_data.get("junho")),
        "julho": _parse_decimal_ou_zero(post_data.get("julho")),
        "agosto": _parse_decimal_ou_zero(post_data.get("agosto")),
        "setembro": _parse_decimal_ou_zero(post_data.get("setembro")),
        "outubro": _parse_decimal_ou_zero(post_data.get("outubro")),
        "novembro": _parse_decimal_ou_zero(post_data.get("novembro")),
        "dezembro": _parse_decimal_ou_zero(post_data.get("dezembro")),
    }


def criar_orcamento_planejado_por_post(empresa, post_data):
    dados = _dados_orcamento_planejado_from_post(post_data, empresa)
    if not dados["ano_raw"]:
        return "Ano e obrigatorio."
    if dados["ano"] <= 0:
        return "Ano invalido."
    dados.pop("ano_raw", None)
    OrcamentoPlanejado.criar_orcamento_planejado(empresa=empresa, **dados)
    return ""


def atualizar_orcamento_planejado_por_post(orcamento_planejado_item, empresa, post_data):
    dados = _dados_orcamento_planejado_from_post(post_data, empresa)
    if not dados["ano_raw"]:
        return "Ano e obrigatorio."
    if dados["ano"] <= 0:
        return "Ano invalido."
    dados.pop("ano_raw", None)
    orcamento_planejado_item.atualizar_orcamento_planejado(**dados)
    return ""


def _dados_frete_from_post(post_data, empresa):
    cidade = Cidade.objects.filter(id=post_data.get("cidade_id"), empresa=empresa).first()
    unidade_federativa = UnidadeFederativa.objects.filter(
        id=post_data.get("unidade_federativa_id"),
        empresa=empresa,
    ).first()
    regiao = Regiao.objects.filter(id=post_data.get("regiao_id"), empresa=empresa).first()
    data_hora_alteracao_raw = (post_data.get("data_hora_alteracao") or "").strip()

    return {
        "cidade": cidade,
        "unidade_federativa": unidade_federativa,
        "regiao": regiao,
        "valor_frete_comercial": _parse_decimal_ou_zero(post_data.get("valor_frete_comercial")),
        "data_hora_alteracao_raw": data_hora_alteracao_raw,
        "data_hora_alteracao": _parse_datetime_ou_none(data_hora_alteracao_raw),
        "valor_frete_minimo": _parse_decimal_ou_zero(post_data.get("valor_frete_minimo")),
        "valor_frete_tonelada": _parse_decimal_ou_zero(post_data.get("valor_frete_tonelada")),
        "tipo_frete": (post_data.get("tipo_frete") or "").strip(),
        "valor_frete_por_km": _parse_decimal_ou_zero(post_data.get("valor_frete_por_km")),
        "valor_taxa_entrada": _parse_decimal_ou_zero(post_data.get("valor_taxa_entrada")),
        "venda_minima": _parse_decimal_ou_zero(post_data.get("venda_minima")),
    }


def criar_frete_por_post(empresa, post_data):
    dados = _dados_frete_from_post(post_data, empresa)
    if not dados["cidade"]:
        return "Cidade e obrigatoria."
    if not dados["unidade_federativa"]:
        return "Unidade federativa e obrigatoria."
    if not dados["regiao"]:
        return "Regiao e obrigatoria."
    if dados["data_hora_alteracao_raw"] and not dados["data_hora_alteracao"]:
        return "Data/hora de alteracao invalida."
    if Frete.objects.filter(empresa=empresa, cidade=dados["cidade"]).exists():
        return "Ja existe frete cadastrado para esta cidade."

    dados.pop("data_hora_alteracao_raw", None)
    Frete.criar_frete(empresa=empresa, **dados)
    return ""


def atualizar_frete_por_post(frete, empresa, post_data):
    dados = _dados_frete_from_post(post_data, empresa)
    if not dados["cidade"]:
        return "Cidade e obrigatoria."
    if not dados["unidade_federativa"]:
        return "Unidade federativa e obrigatoria."
    if not dados["regiao"]:
        return "Regiao e obrigatoria."
    if dados["data_hora_alteracao_raw"] and not dados["data_hora_alteracao"]:
        return "Data/hora de alteracao invalida."
    if Frete.objects.filter(empresa=empresa, cidade=dados["cidade"]).exclude(id=frete.id).exists():
        return "Ja existe frete cadastrado para esta cidade."

    dados.pop("data_hora_alteracao_raw", None)
    frete.atualizar_frete(**dados)
    return ""


def _dados_estoque_from_post(post_data, empresa):
    produto = Produto.objects.filter(id=post_data.get("produto_id"), empresa=empresa).first()
    nome_origem_raw = (post_data.get("nome_origem") or "").strip()
    data_contagem_raw = (post_data.get("data_contagem") or "").strip()

    qtd_estoque = _parse_decimal_ou_zero(post_data.get("qtd_estoque"))
    reservado = _parse_decimal_ou_zero(post_data.get("reservado"))

    # Estoque deve refletir os parametros atuais do cadastro de produtos.
    if produto:
        pacote_por_fardo = _parse_decimal_ou_zero(produto.pacote_por_fardo)
        producao_por_dia_fd = _parse_decimal_ou_zero(produto.producao_por_dia_fd)
        estoque_minimo_parametro = _parse_decimal_ou_zero(produto.estoque_minimo_pacote)

        produto_tem_parametro = bool(
            pacote_por_fardo > 0
            or producao_por_dia_fd > 0
            or estoque_minimo_parametro > 0
        )
        estoque_minimo = (
            estoque_minimo_parametro
            if produto_tem_parametro
            else Decimal("12000")
        )
    else:
        pacote_por_fardo = _parse_decimal_ou_zero(post_data.get("pacote_por_fardo"))
        estoque_minimo = _parse_decimal_ou_zero(post_data.get("estoque_minimo"))
        producao_por_dia_fd = _parse_decimal_ou_zero(post_data.get("producao_por_dia_fd"))

    sub_total_est_pen = qtd_estoque - reservado
    total_pcp_pacote = sub_total_est_pen - estoque_minimo
    total_pcp_fardo = (total_pcp_pacote / pacote_por_fardo) if pacote_por_fardo > 0 else Decimal("0")
    dia_de_producao = (total_pcp_fardo / producao_por_dia_fd) if producao_por_dia_fd > 0 else Decimal("0")

    return {
        "nome_origem_raw": nome_origem_raw,
        "data_contagem_raw": data_contagem_raw,
        "nome_origem": _parse_date_ou_none(nome_origem_raw),
        "data_contagem": _parse_date_ou_none(data_contagem_raw),
        "status": (post_data.get("status") or "Ativo").strip() or "Ativo",
        "codigo_empresa": (post_data.get("codigo_empresa") or "").strip(),
        "produto": produto,
        "qtd_estoque": qtd_estoque,
        "giro_mensal": _parse_decimal_ou_zero(post_data.get("giro_mensal")),
        "lead_time_fornecimento": _parse_decimal_ou_zero(post_data.get("lead_time_fornecimento")),
        "codigo_volume": (post_data.get("codigo_volume") or "").strip(),
        "custo_total": _parse_decimal_ou_zero(post_data.get("custo_total")),
        "reservado": reservado,
        "pacote_por_fardo": pacote_por_fardo,
        "sub_total_est_pen": sub_total_est_pen,
        "estoque_minimo": estoque_minimo,
        "producao_por_dia_fd": producao_por_dia_fd,
        "total_pcp_pacote": total_pcp_pacote,
        "total_pcp_fardo": total_pcp_fardo,
        "dia_de_producao": dia_de_producao,
        "codigo_local": (post_data.get("codigo_local") or "").strip(),
    }


def criar_estoque_por_post(empresa, post_data):
    dados = _dados_estoque_from_post(post_data, empresa)
    if not dados["nome_origem_raw"]:
        return "Nome origem e obrigatorio."
    if not dados["nome_origem"]:
        return "Nome origem invalido. Use uma data valida."
    if not dados["data_contagem_raw"]:
        return "Data contagem e obrigatoria."
    if not dados["data_contagem"]:
        return "Data contagem invalida."
    if not dados["produto"]:
        return "Produto e obrigatorio."
    if not dados["codigo_empresa"]:
        return "Codigo empresa e obrigatorio."
    if not dados["codigo_local"]:
        return "Codigo local e obrigatorio."

    if Estoque.objects.filter(
        empresa=empresa,
        nome_origem=dados["nome_origem"],
        data_contagem=dados["data_contagem"],
        codigo_empresa=dados["codigo_empresa"],
        codigo_local=dados["codigo_local"],
        produto=dados["produto"],
    ).exists():
        return "Ja existe estoque para essa combinacao de origem, data, empresa, local e produto."

    dados.pop("nome_origem_raw", None)
    dados.pop("data_contagem_raw", None)
    Estoque.criar_estoque(empresa=empresa, **dados)
    return ""


def atualizar_estoque_por_post(estoque, empresa, post_data):
    dados = _dados_estoque_from_post(post_data, empresa)
    if not dados["nome_origem_raw"]:
        return "Nome origem e obrigatorio."
    if not dados["nome_origem"]:
        return "Nome origem invalido. Use uma data valida."
    if not dados["data_contagem_raw"]:
        return "Data contagem e obrigatoria."
    if not dados["data_contagem"]:
        return "Data contagem invalida."
    if not dados["produto"]:
        return "Produto e obrigatorio."
    if not dados["codigo_empresa"]:
        return "Codigo empresa e obrigatorio."
    if not dados["codigo_local"]:
        return "Codigo local e obrigatorio."

    if Estoque.objects.filter(
        empresa=empresa,
        nome_origem=dados["nome_origem"],
        data_contagem=dados["data_contagem"],
        codigo_empresa=dados["codigo_empresa"],
        codigo_local=dados["codigo_local"],
        produto=dados["produto"],
    ).exclude(id=estoque.id).exists():
        return "Ja existe estoque para essa combinacao de origem, data, empresa, local e produto."

    dados.pop("nome_origem_raw", None)
    dados.pop("data_contagem_raw", None)
    estoque.atualizar_estoque(**dados)
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


def _dados_producao_from_post(post_data, empresa):
    produto = Produto.objects.filter(id=post_data.get("produto_id"), empresa=empresa).first()
    numero_operacao_raw = (post_data.get("numero_operacao") or "").strip()
    tamanho_lote_texto = (post_data.get("tamanho_lote") or "").strip()
    kg_auto, producao_por_dia_auto, kg_por_lote_auto = _calcular_metricas_producao_auto(produto, tamanho_lote_texto)

    return {
        "data_origem": (post_data.get("data_origem") or "").strip(),
        "numero_operacao_raw": numero_operacao_raw,
        "numero_operacao": max(0, _parse_int_ou_zero(numero_operacao_raw)),
        "situacao": (post_data.get("situacao") or "").strip(),
        "produto": produto,
        "tamanho_lote": tamanho_lote_texto,
        "numero_lote": (post_data.get("numero_lote") or "").strip(),
        "data_hora_entrada_atividade": _parse_datetime_ou_none(post_data.get("data_hora_entrada_atividade")),
        "data_hora_aceite_atividade": _parse_datetime_ou_none(post_data.get("data_hora_aceite_atividade")),
        "data_hora_inicio_atividade": _parse_datetime_ou_none(post_data.get("data_hora_inicio_atividade")),
        "data_hora_fim_atividade": _parse_datetime_ou_none(post_data.get("data_hora_fim_atividade")),
        "kg": kg_auto,
        "producao_por_dia": producao_por_dia_auto,
        "kg_por_lote": kg_por_lote_auto,
        "estoque_minimo_pacote": _parse_decimal_ou_zero(post_data.get("estoque_minimo_pacote")),
    }


def criar_producao_por_post(empresa, post_data):
    dados = _dados_producao_from_post(post_data, empresa)
    if not dados["data_origem"]:
        return "Data origem e obrigatoria."
    if not dados["numero_operacao_raw"]:
        return "Numero da operacao e obrigatorio."
    if dados["numero_operacao"] <= 0:
        return "Numero da operacao invalido."
    if not dados["situacao"]:
        return "Situacao e obrigatoria."
    if not dados["produto"]:
        return "Produto e obrigatorio."
    dados.pop("numero_operacao_raw", None)
    Producao.criar_producao(empresa=empresa, **dados)
    return ""


def atualizar_producao_por_post(producao_item, empresa, post_data):
    dados = _dados_producao_from_post(post_data, empresa)
    if not dados["data_origem"]:
        return "Data origem e obrigatoria."
    if not dados["numero_operacao_raw"]:
        return "Numero da operacao e obrigatorio."
    if dados["numero_operacao"] <= 0:
        return "Numero da operacao invalido."
    if not dados["situacao"]:
        return "Situacao e obrigatoria."
    if not dados["produto"]:
        return "Produto e obrigatorio."
    dados.pop("numero_operacao_raw", None)
    producao_item.atualizar_producao(**dados)
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


def criar_atividade_por_post(post_data, empresa, usuario=None):
    dados, erro = _dados_atividade_from_post(post_data, empresa)
    if erro:
        return erro
    if usuario is not None:
        dados["usuario"] = usuario
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


def importar_upload_carteira(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="carteira",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "carteiras", "carteiras importadas")
    if detalhe:
        return False, detalhe

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


def preparar_diretorios_pedidos_pendentes():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "comercial" / "pedidos_pendentes"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_controle_margem():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "comercial" / "controle_de_margem"
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


def preparar_diretorios_adiantamentos():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "financeiro" / "adiantamentos"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_contas_a_receber():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "financeiro" / "contas_a_receber"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_orcamento():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "financeiro" / "orcamento"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def importar_upload_vendas(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="vendas_por_categoria",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        # Falha de metadado nao deve invalidar importacao ja concluida.
        pass

    detalhe = _detalhe_erro_importacao(resultado, "vendas", "vendas importadas")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, vendas: {resultado['vendas']}."
        ),
    )


def importar_upload_pedidos_pendentes(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado = importar_pedidos_pendentes_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Pedidos Pendentes: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="pedidos_pendentes",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "pedidos_pendentes", "pedidos pendentes importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, pedidos: {resultado['pedidos_pendentes']}, "
            f"rotas criadas: {resultado['rotas']}, regioes criadas: {resultado['regioes']}, "
            f"parceiros criados: {resultado['parceiros']}."
        ),
    )


def importar_upload_controle_margem(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    if not arquivo:
        return False, "Selecione um arquivo .xls ou .xlsx para importar."

    nome_arquivo = Path(arquivo.name).name
    nome_arquivo_lower = nome_arquivo.lower()
    if not (nome_arquivo_lower.endswith(".xlsx") or nome_arquivo_lower.endswith(".xls")):
        return False, "Formato invalido. Envie apenas arquivo .xls ou .xlsx."

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
        resultado = importar_controle_margem_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Controle de Margem: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="controle_de_margem",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    total_controle = resultado.get("criados", 0) + resultado.get("atualizados", 0)
    detalhe = _detalhe_erro_importacao(
        resultado,
        "linhas",
        "registros de controle de margem importados",
        valor=total_controle,
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas processadas: {resultado['linhas']}, criados: {resultado['criados']}, "
            f"atualizados: {resultado['atualizados']}, parceiros criados: {resultado['parceiros_criados']}, "
            f"erros: {resultado['erros']}."
        ),
    )


def importar_upload_dfc(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="dfc",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "dfc", "entradas de DFC importadas")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, dfc: {resultado['dfc']}."
        ),
    )


def importar_upload_adiantamentos(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado = importar_adiantamentos_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Adiantamentos: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="adiantamentos",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "adiantamentos", "registros de Adiantamentos importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, adiantamentos: {resultado['adiantamentos']}."
        ),
    )


def importar_upload_contas_a_receber(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado = importar_contas_a_receber_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Contas a Receber: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="contas_a_receber",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(
        resultado,
        "contas_a_receber",
        "contas a receber importadas",
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, contas: {resultado['contas_a_receber']}."
        ),
    )


def importar_upload_orcamento(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado_realizados = importar_orcamento_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Orcamento: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="orcamento",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(
        resultado_realizados,
        "orcamentos",
        "orcamentos importados",
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado_realizados['arquivos']}, "
            f"linhas realizados: {resultado_realizados['linhas']}, "
            f"orcamentos realizados: {resultado_realizados['orcamentos']}."
        ),
    )


def preparar_diretorios_cargas():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "operacional" / "cargas_em_aberto"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_producao():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "operacional" / "producao"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_fretes():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "operacional" / "tabela_de_fretes"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def preparar_diretorios_estoque():
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / "operacional" / "estoque_pcp"
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def importar_upload_cargas(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="cargas_em_aberto",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "cargas", "cargas importadas")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, cargas: {resultado['cargas']}."
        ),
    )


def importar_upload_fretes(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado = importar_fretes_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar fretes: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="tabela_de_fretes",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "fretes", "fretes importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, fretes: {resultado['fretes']}, "
            f"cidades: {resultado['cidades']}, regioes: {resultado['regioes']}, "
            f"ufs: {resultado['unidades_federativas']}."
        ),
    )


def _normalizar_relpath_upload_estoque(nome_arquivo: str):
    caminho_bruto = str(nome_arquivo or "").replace("\\", "/")
    partes = []
    for parte in caminho_bruto.split("/"):
        token = parte.strip()
        if not token or token == ".":
            continue
        if token == "..":
            return None
        partes.append(token.replace(":", "_"))

    if not partes:
        return None

    if len(partes) > 1 and partes[0].lower() == "estoque":
        partes = partes[1:]

    if not partes:
        return None

    if partes[0].lower() == "subscritos":
        partes = ["upload"] + partes

    caminho_relativo = Path(*partes)
    if caminho_relativo.suffix.lower() != ".xls":
        return None
    return caminho_relativo


def _listar_arquivos_xls_estoque(diretorio_importacao, diretorio_subscritos):
    return sorted(
        [
            arquivo
            for arquivo in diretorio_importacao.rglob("*.xls")
            if arquivo.is_file() and diretorio_subscritos not in arquivo.parents
        ]
    )


def _arquivar_arquivos_estoque(diretorio_importacao, diretorio_subscritos):
    arquivos_atuais = _listar_arquivos_xls_estoque(diretorio_importacao, diretorio_subscritos)
    if not arquivos_atuais:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino_base = diretorio_subscritos / timestamp

    for arquivo_antigo in arquivos_atuais:
        rel_path = arquivo_antigo.relative_to(diretorio_importacao)
        destino_subscrito = destino_base / rel_path
        destino_subscrito.parent.mkdir(parents=True, exist_ok=True)
        if destino_subscrito.exists():
            destino_subscrito = destino_subscrito.with_name(
                f"{destino_subscrito.stem}_{timestamp}{destino_subscrito.suffix}"
            )
        shutil.move(str(arquivo_antigo), str(destino_subscrito))

    diretorios = sorted(
        [
            pasta
            for pasta in diretorio_importacao.rglob("*")
            if pasta.is_dir() and pasta != diretorio_subscritos and diretorio_subscritos not in pasta.parents
        ],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for pasta in diretorios:
        try:
            next(pasta.iterdir())
        except StopIteration:
            pasta.rmdir()


def importar_upload_estoque(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    arquivos_xls = []
    for arquivo in arquivos or []:
        caminho_relativo = _normalizar_relpath_upload_estoque(arquivo.name)
        if caminho_relativo is not None:
            arquivos_xls.append((arquivo, caminho_relativo))

    if not arquivos_xls:
        return False, "Selecione a pasta ESTOQUE com arquivos .xls de posicao e reservado."

    _arquivar_arquivos_estoque(diretorio_importacao, diretorio_subscritos)

    for indice, (arquivo_upload, caminho_relativo) in enumerate(arquivos_xls, start=1):
        destino = diretorio_importacao / caminho_relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            destino = destino.with_name(f"{destino.stem}_{indice:04d}{destino.suffix}")
        with destino.open("wb+") as file_out:
            for chunk in arquivo_upload.chunks():
                file_out.write(chunk)

    try:
        resultado = importar_estoque_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar estoque: {exc}"

    if resultado["arquivos_posicao"] == 0 or resultado["arquivos_reservado"] == 0:
        return (
            False,
            (
                "Importacao incompleta. Envie a pasta ESTOQUE com as subpastas "
                f"de posicao e reservado. Arquivos detectados - posicao: {resultado['arquivos_posicao']}, "
                f"reservado: {resultado['arquivos_reservado']}."
            ),
        )
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="estoque_pcp",
            usuario=usuario,
            arquivos=[str(caminho_relativo).replace("\\", "/") for _, caminho_relativo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(resultado, "estoques", "registros de estoque importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']} "
            f"(posicao: {resultado['arquivos_posicao']}, reservado: {resultado['arquivos_reservado']}), "
            f"linhas: {resultado['linhas']}, estoques: {resultado['estoques']}."
        ),
    )


def importar_upload_producao(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
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
        resultado = importar_producao_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar producao: {exc}"
    try:
        _registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            modulo="producao",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = _detalhe_erro_importacao(
        resultado,
        "producoes",
        "producoes importadas",
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, producoes: {resultado['producoes']}, "
            f"produtos vinculados/criados: {resultado['produtos']}."
        ),
    )

