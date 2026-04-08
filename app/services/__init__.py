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
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from ..models import (
    Adiantamento,
    Agenda,
    Atividade,
    BalancoPatrimonial,
    BalancoPatrimonialAtivo,
    Banco,
    CentroResultado,
    ComiteDiario,
    ContratoRede,
    Cargas,
    Carteira,
    Cidade,
    Colaborador,
    ContaBancaria,
    Descritivo,
    ControleMargem,
    ContasAReceber,
    DescricaoPerfil,
    Empresa,
    EmpresaTitular,
    Faturamento,
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
    ParametroNegocios,
    ParametroMeta,
    PrecificacaoCalculadoraPrecoMedio,
    PrecificacaoCenario,
    PrecificacaoMateriaPrima,
    PrecificacaoProdutoAcabadoCMV,
    PrecificacaoProdutoAcabadoDespesa,
    PrecificacaoProdutoAcabadoImposto,
    PrecificacaoProdutoAcabadoPrecoVenda,
    PrecificacaoSimulacaoCompraVenda,
    PedidoPendente,
    Motorista,
    Producao,
    Produto,
    Projeto,
    PlanoCargoSalario,
    Rota,
    Regiao,
    SaldoLimite,
    Titulo,
    Transportadora,
    UnidadeFederativa,
    Usuario,
    Venda,
)
from ..utils.administrativo_utils import (
    _set_prazo_inicio_e_prazo_termino,
    _transformar_date_ou_none,
    _transformar_int_ou_none,
    _transformar_iso_week_parts_ou_none,
)
from ..utils.controle_margem_regras import (
    calcular_campos_controle_margem_legado,
    obter_parametros_controle_margem,
)
from ..utils.comercial import _sincronizar_descricao_perfil
from ..utils.importacao_metadados import caminho_metadados_importacao
from ..utils.comercial_importacao import (
    _iterar_linhas_xlsx,
    importar_carteira_do_diretorio,
    importar_controle_margem_do_diretorio,
    importar_pedidos_pendentes_do_diretorio,
    importar_vendas_do_diretorio,
)
from ..utils.financeiro_importacao import (
    importar_adiantamentos_do_diretorio,
    importar_comite_diario_do_diretorio,
    importar_contas_a_receber_do_diretorio,
    importar_dfc_do_diretorio,
    importar_faturamento_do_diretorio,
    importar_orcamento_do_diretorio,
)
from ..utils.financeiro_dfc_saldo import (
    construir_payload_tabela_saldo_dfc as _construir_payload_tabela_saldo_dfc,
    salvar_dfc_saldo_manual_por_post as _salvar_dfc_saldo_manual_por_post,
)
from ..utils.operacional_importacao import (
    importar_cargas_do_diretorio,
    importar_estoque_do_diretorio,
    importar_fretes_do_diretorio,
    importar_producao_do_diretorio,
)
from .financeiro import (
    importar_upload_adiantamentos,
    importar_upload_comite_diario,
    importar_upload_contas_a_receber,
    importar_upload_dfc,
    importar_upload_faturamento,
    importar_upload_orcamento,
    preparar_diretorios_adiantamentos,
    preparar_diretorios_comite_diario,
    preparar_diretorios_contas_a_receber,
    preparar_diretorios_dfc,
    preparar_diretorios_faturamento,
    preparar_diretorios_orcamento,
)

def _normalizar_empresa_id(empresa):
    empresa_id = getattr(empresa, "id", empresa)
    try:
        empresa_id_int = int(empresa_id)
    except (TypeError, ValueError):
        raise ValueError("Empresa invalida para importacao.")
    if empresa_id_int <= 0:
        raise ValueError("Empresa invalida para importacao.")
    return empresa_id_int


def _preparar_diretorios_importacao(*, area, modulo, empresa):
    empresa_id = str(_normalizar_empresa_id(empresa))
    diretorio_importacao = Path(settings.BASE_DIR) / "importacoes" / area / modulo / empresa_id
    diretorio_subscritos = diretorio_importacao / "subscritos"
    diretorio_importacao.mkdir(parents=True, exist_ok=True)
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)
    return diretorio_importacao, diretorio_subscritos


def _registrar_metadados_importacao(
    *,
    diretorio_subscritos,
    empresa,
    modulo,
    usuario,
    arquivos,
):
    empresa_id = _normalizar_empresa_id(empresa)
    caminho_metadados = caminho_metadados_importacao(Path(diretorio_subscritos).parent, empresa_id)
    nomes_arquivos = [
        Path(nome_arquivo).name
        for nome_arquivo in (arquivos or [])
        if str(nome_arquivo or "").strip()
    ]
    payload = {
        "empresa_id": empresa_id,
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
    try:
        empresa.excluir_empresa()
    except ProtectedError as exc:
        modelos = sorted({obj.__class__.__name__ for obj in getattr(exc, "protected_objects", [])})
        if modelos:
            tipos = ", ".join(modelos)
            return (
                False,
                f"Empresa nao pode ser excluida porque possui registros vinculados em: {tipos}.",
            )
        return False, "Empresa nao pode ser excluida porque possui registros vinculados protegidos."
    return True, "Empresa excluida com sucesso!"


def _valor_checkbox_ativo(post_data, campo):
    return str(post_data.get(campo, "")).strip().lower() in {"1", "true", "on", "sim", "yes"}


def criar_usuario_por_post(empresa, post_data, permissoes):
    nome = (post_data.get("nome") or "").strip()
    senha = post_data.get("senha")
    is_staff = _valor_checkbox_ativo(post_data, "is_staff")
    if not nome:
        return "O nome do usuario e obrigatorio."

    usuario, created = Usuario.objects.get_or_create(
        username=nome,
        defaults={
            "empresa": empresa,
            "is_staff": is_staff,
        },
    )
    if not created:
        return "Ja existe um username igual ao cadastrado para outro usuario."

    usuario.set_password(senha)
    usuario.save(update_fields=["password"])
    permissoes_usuario = list(Permissao.objects.all()) if is_staff else permissoes
    if permissoes_usuario:
        usuario.permissoes.set(permissoes_usuario)
    return ""


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


def _dados_plano_cargo_salario_from_post(post_data):
    cadastro_raw = (post_data.get("cadastro") or "").strip()
    data_admissao_raw = (post_data.get("data_admissao") or "").strip()
    return {
        "cadastro_raw": cadastro_raw,
        "cadastro": _parse_int_ou_zero(cadastro_raw),
        "funcionario": (post_data.get("funcionario") or "").strip(),
        "contrato": (post_data.get("contrato") or "").strip(),
        "genero": (post_data.get("genero") or "").strip(),
        "setor": (post_data.get("setor") or "").strip(),
        "cargo": (post_data.get("cargo") or "").strip(),
        "novo_cargo": (post_data.get("novo_cargo") or "").strip(),
        "data_admissao_raw": data_admissao_raw,
        "data_admissao": _parse_date_ou_none(data_admissao_raw),
        "salario_carteira": _parse_decimal_ou_none(post_data.get("salario_carteira")),
        "piso_categoria": _parse_decimal_ou_none(post_data.get("piso_categoria")),
        "jr": _parse_decimal_ou_none(post_data.get("jr")),
        "pleno": _parse_decimal_ou_none(post_data.get("pleno")),
        "senior": _parse_decimal_ou_none(post_data.get("senior")),
    }


def criar_plano_cargo_salario_por_post(empresa, post_data):
    dados = _dados_plano_cargo_salario_from_post(post_data)
    if not dados["cadastro_raw"]:
        return "Cadastro e obrigatorio."
    if dados["cadastro"] <= 0:
        return "Cadastro invalido."
    if not dados["funcionario"]:
        return "Funcionario e obrigatorio."
    if not dados["contrato"]:
        return "Contrato e obrigatorio."
    if not dados["genero"]:
        return "Genero e obrigatorio."
    if not dados["setor"]:
        return "Setor e obrigatorio."
    if not dados["cargo"]:
        return "Cargo e obrigatorio."
    if dados["data_admissao_raw"] and not dados["data_admissao"]:
        return "Data de admissao invalida."
    if PlanoCargoSalario.objects.filter(empresa=empresa, cadastro=dados["cadastro"]).exists():
        return "Ja existe cadastro com este numero nesta empresa."

    dados.pop("cadastro_raw", None)
    dados.pop("data_admissao_raw", None)
    PlanoCargoSalario.criar_plano_cargo_salario(empresa=empresa, **dados)
    return ""


def atualizar_plano_cargo_salario_por_post(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_plano_cargo_salario_from_post(post_data)
    if not dados["cadastro_raw"]:
        return "Cadastro e obrigatorio."
    if dados["cadastro"] <= 0:
        return "Cadastro invalido."
    if not dados["funcionario"]:
        return "Funcionario e obrigatorio."
    if not dados["contrato"]:
        return "Contrato e obrigatorio."
    if not dados["genero"]:
        return "Genero e obrigatorio."
    if not dados["setor"]:
        return "Setor e obrigatorio."
    if not dados["cargo"]:
        return "Cargo e obrigatorio."
    if dados["data_admissao_raw"] and not dados["data_admissao"]:
        return "Data de admissao invalida."
    if (
        PlanoCargoSalario.objects.filter(empresa=empresa, cadastro=dados["cadastro"])
        .exclude(id=item.id)
        .exists()
    ):
        return "Ja existe cadastro com este numero nesta empresa."

    dados.pop("cadastro_raw", None)
    dados.pop("data_admissao_raw", None)
    item.atualizar_plano_cargo_salario(**dados)
    return ""


_CAMPOS_DESCRITIVO_TEXTO = (
    "contas_a_pagar",
    "contas_a_receber",
    "supervisor_financeiro",
    "faturamento",
    "supervisor_logistica",
    "conferente",
    "gerente_de_producao",
    "gerente_cml",
    "assistente_comercial",
    "diretor",
)


def _dados_descritivo_from_post(post_data):
    inicio_raw = (post_data.get("inicio") or "").strip()
    termino_raw = (post_data.get("termino") or "").strip()
    dados = {
        "inicio_raw": inicio_raw,
        "termino_raw": termino_raw,
        "inicio": _parse_time_ou_none(inicio_raw),
        "termino": _parse_time_ou_none(termino_raw),
    }
    for campo in _CAMPOS_DESCRITIVO_TEXTO:
        dados[campo] = (post_data.get(campo) or "").strip()
    return dados


def _validar_dados_descritivo(dados, *, empresa, descritivo_id=None):
    if not dados["inicio_raw"]:
        return "Horario de inicio e obrigatorio."
    if not dados["termino_raw"]:
        return "Horario de termino e obrigatorio."
    if not dados["inicio"]:
        return "Horario de inicio invalido."
    if not dados["termino"]:
        return "Horario de termino invalido."
    if dados["inicio"] >= dados["termino"]:
        return "Horario de termino deve ser maior que o inicio."

    conflito_qs = Descritivo.objects.filter(
        empresa=empresa,
        inicio=dados["inicio"],
        termino=dados["termino"],
    )
    if descritivo_id is not None:
        conflito_qs = conflito_qs.exclude(id=descritivo_id)
    if conflito_qs.exists():
        return "Ja existe descritivo com este intervalo nesta empresa."
    return ""


def criar_descritivo_por_post(empresa, post_data):
    dados = _dados_descritivo_from_post(post_data)
    erro = _validar_dados_descritivo(dados, empresa=empresa)
    if erro:
        return erro

    dados.pop("inicio_raw", None)
    dados.pop("termino_raw", None)
    Descritivo.criar_descritivo(empresa=empresa, **dados)
    return ""


def atualizar_descritivo_por_post(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_descritivo_from_post(post_data)
    erro = _validar_dados_descritivo(
        dados,
        empresa=empresa,
        descritivo_id=item.id,
    )
    if erro:
        return erro

    dados.pop("inicio_raw", None)
    dados.pop("termino_raw", None)
    item.atualizar_descritivo(**dados)
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


def criar_empresa_titular_por_dados(empresa, codigo, nome):
    codigo_normalizado = _parse_int_ou_zero(codigo)
    nome_normalizado = (nome or "").strip()
    if codigo_normalizado <= 0:
        return "Codigo da empresa titular e obrigatorio e deve ser maior que zero."
    if not nome_normalizado:
        return "Nome da empresa titular e obrigatorio."
    if EmpresaTitular.objects.filter(empresa=empresa, codigo=codigo_normalizado).exists():
        return "Ja existe empresa titular com este codigo nesta empresa."
    if EmpresaTitular.objects.filter(empresa=empresa, nome__iexact=nome_normalizado).exists():
        return "Ja existe empresa titular com este nome nesta empresa."
    EmpresaTitular.criar_empresa_titular(empresa=empresa, codigo=codigo_normalizado, nome=nome_normalizado)
    return ""


def atualizar_empresa_titular_por_dados(empresa_titular, empresa, codigo, nome):
    codigo_normalizado = _parse_int_ou_zero(codigo)
    nome_normalizado = (nome or "").strip()
    if empresa_titular.empresa_id != empresa.id:
        return "Empresa titular invalida para esta empresa."
    if codigo_normalizado <= 0:
        return "Codigo da empresa titular e obrigatorio e deve ser maior que zero."
    if not nome_normalizado:
        return "Nome da empresa titular e obrigatorio."
    if (
        EmpresaTitular.objects.filter(empresa=empresa, codigo=codigo_normalizado)
        .exclude(id=empresa_titular.id)
        .exists()
    ):
        return "Ja existe empresa titular com este codigo nesta empresa."
    if (
        EmpresaTitular.objects.filter(empresa=empresa, nome__iexact=nome_normalizado)
        .exclude(id=empresa_titular.id)
        .exists()
    ):
        return "Ja existe empresa titular com este nome nesta empresa."
    empresa_titular.atualizar_empresa_titular(codigo=codigo_normalizado, nome=nome_normalizado)
    return ""


def excluir_empresa_titular_por_dados(empresa_titular, empresa):
    if empresa_titular.empresa_id != empresa.id:
        return "Empresa titular invalida para esta empresa."
    empresa_titular.excluir_empresa_titular()
    return ""


def criar_banco_por_dados(empresa, nome):
    nome_normalizado = (nome or "").strip()
    if not nome_normalizado:
        return "Nome do banco e obrigatorio."
    if Banco.objects.filter(empresa=empresa, nome__iexact=nome_normalizado).exists():
        return "Ja existe banco com este nome nesta empresa."
    Banco.criar_banco(empresa=empresa, nome=nome_normalizado)
    return ""


def atualizar_banco_por_dados(banco, empresa, nome):
    nome_normalizado = (nome or "").strip()
    if banco.empresa_id != empresa.id:
        return "Banco invalido para esta empresa."
    if not nome_normalizado:
        return "Nome do banco e obrigatorio."
    if Banco.objects.filter(empresa=empresa, nome__iexact=nome_normalizado).exclude(id=banco.id).exists():
        return "Ja existe banco com este nome nesta empresa."
    banco.atualizar_banco(nome=nome_normalizado)
    return ""


def excluir_banco_por_dados(banco, empresa):
    if banco.empresa_id != empresa.id:
        return "Banco invalido para esta empresa."
    banco.excluir_banco()
    return ""


def _obter_empresa_titular_por_id(empresa, empresa_titular_id):
    if not empresa_titular_id:
        return None
    return EmpresaTitular.objects.filter(id=empresa_titular_id, empresa=empresa).first()


def _obter_banco_por_id(empresa, banco_id):
    if not banco_id:
        return None
    return Banco.objects.filter(id=banco_id, empresa=empresa).first()


def criar_conta_bancaria_por_dados(empresa, post_data):
    agencia = _parse_int_ou_zero(post_data.get("agencia"))
    numero_conta = _parse_int64_ou_zero(post_data.get("numero_conta"))
    banco = _obter_banco_por_id(empresa, post_data.get("banco_id"))
    empresa_titular = _obter_empresa_titular_por_id(empresa, post_data.get("empresa_titular_id"))

    if agencia <= 0:
        return "Agencia e obrigatoria e deve ser maior que zero."
    if numero_conta <= 0:
        return "Numero da conta e obrigatorio e deve ser maior que zero."
    if not banco:
        return "Banco e obrigatorio."
    if not empresa_titular:
        return "Empresa titular e obrigatoria."
    if ContaBancaria.objects.filter(empresa=empresa, agencia=agencia, numero_conta=numero_conta).exists():
        return "Ja existe conta bancaria com agencia e numero de conta nesta empresa."

    ContaBancaria.criar_conta_bancaria(
        empresa=empresa,
        empresa_titular=empresa_titular,
        agencia=agencia,
        numero_conta=numero_conta,
        banco=banco,
    )
    return ""


def atualizar_conta_bancaria_por_dados(conta_bancaria, empresa, post_data):
    agencia = _parse_int_ou_zero(post_data.get("agencia"))
    numero_conta = _parse_int64_ou_zero(post_data.get("numero_conta"))
    banco = _obter_banco_por_id(empresa, post_data.get("banco_id"))
    empresa_titular = _obter_empresa_titular_por_id(empresa, post_data.get("empresa_titular_id"))

    if conta_bancaria.empresa_id != empresa.id:
        return "Conta bancaria invalida para esta empresa."
    if agencia <= 0:
        return "Agencia e obrigatoria e deve ser maior que zero."
    if numero_conta <= 0:
        return "Numero da conta e obrigatorio e deve ser maior que zero."
    if not banco:
        return "Banco e obrigatorio."
    if not empresa_titular:
        return "Empresa titular e obrigatoria."
    if (
        ContaBancaria.objects.filter(empresa=empresa, agencia=agencia, numero_conta=numero_conta)
        .exclude(id=conta_bancaria.id)
        .exists()
    ):
        return "Ja existe conta bancaria com agencia e numero de conta nesta empresa."

    conta_bancaria.atualizar_conta_bancaria(
        empresa_titular=empresa_titular,
        agencia=agencia,
        numero_conta=numero_conta,
        banco=banco,
    )
    return ""


def excluir_conta_bancaria_por_dados(conta_bancaria, empresa):
    if conta_bancaria.empresa_id != empresa.id:
        return "Conta bancaria invalida para esta empresa."
    conta_bancaria.excluir_conta_bancaria()
    return ""


def _tipo_movimentacao_saldo_limite_valido(valor):
    valor_normalizado = str(valor or "").strip()
    tipos_validos = {item[0] for item in SaldoLimite.TIPO_MOVIMENTACAO_CHOICES}
    return valor_normalizado if valor_normalizado in tipos_validos else ""


def _dados_saldo_limite_from_post(empresa, post_data):
    data = _parse_date_ou_none(post_data.get("data"))
    empresa_titular = _obter_empresa_titular_por_id(empresa, post_data.get("empresa_titular_id"))
    conta_bancaria = ContaBancaria.objects.filter(
        id=post_data.get("conta_bancaria_id"),
        empresa=empresa,
    ).first()
    tipo_movimentacao = _tipo_movimentacao_saldo_limite_valido(post_data.get("tipo_movimentacao"))
    valor_atual = _parse_decimal_ou_zero(post_data.get("valor_atual"))
    return {
        "data": data,
        "empresa_titular": empresa_titular,
        "conta_bancaria": conta_bancaria,
        "tipo_movimentacao": tipo_movimentacao,
        "valor_atual": valor_atual,
    }


def criar_saldo_limite_por_dados(empresa, post_data):
    dados = _dados_saldo_limite_from_post(empresa, post_data)
    if not dados["data"]:
        return "Data e obrigatoria."
    if not dados["empresa_titular"]:
        return "Empresa titular e obrigatoria."
    if not dados["conta_bancaria"]:
        return "Conta bancaria e obrigatoria."
    if not dados["tipo_movimentacao"]:
        return "Tipo de movimentacao e obrigatorio."
    if dados["conta_bancaria"].empresa_titular_id != dados["empresa_titular"].id:
        return "Conta bancaria nao pertence a empresa titular selecionada."
    if SaldoLimite.objects.filter(
        empresa=empresa,
        data=dados["data"],
        empresa_titular=dados["empresa_titular"],
        conta_bancaria=dados["conta_bancaria"],
        tipo_movimentacao=dados["tipo_movimentacao"],
    ).exists():
        return "Ja existe registro para a combinacao de data, empresa titular, conta e tipo."

    SaldoLimite.criar_saldo_limite(empresa=empresa, **dados)
    return ""


def atualizar_saldo_limite_por_dados(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_saldo_limite_from_post(empresa, post_data)
    if not dados["data"]:
        return "Data e obrigatoria."
    if not dados["empresa_titular"]:
        return "Empresa titular e obrigatoria."
    if not dados["conta_bancaria"]:
        return "Conta bancaria e obrigatoria."
    if not dados["tipo_movimentacao"]:
        return "Tipo de movimentacao e obrigatorio."
    if dados["conta_bancaria"].empresa_titular_id != dados["empresa_titular"].id:
        return "Conta bancaria nao pertence a empresa titular selecionada."
    if (
        SaldoLimite.objects.filter(
            empresa=empresa,
            data=dados["data"],
            empresa_titular=dados["empresa_titular"],
            conta_bancaria=dados["conta_bancaria"],
            tipo_movimentacao=dados["tipo_movimentacao"],
        )
        .exclude(id=item.id)
        .exists()
    ):
        return "Ja existe registro para a combinacao de data, empresa titular, conta e tipo."

    item.atualizar_saldo_limite(**dados)
    return ""


def excluir_saldo_limite_por_dados(item, empresa):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."
    item.excluir_saldo_limite()
    return ""


def _choice_valido(valor, choices):
    valor_normalizado = str(valor or "").strip()
    valores_validos = {item[0] for item in choices}
    return valor_normalizado if valor_normalizado in valores_validos else ""


def _dados_comite_diario_from_post(empresa, post_data):
    receita_despesa = _choice_valido(post_data.get("receita_despesa"), ComiteDiario.RECEITA_DESPESA_CHOICES)
    tipo_movimento = _choice_valido(post_data.get("tipo_movimento"), ComiteDiario.TIPO_MOVIMENTO_CHOICES)
    decisao = _choice_valido(post_data.get("decisao"), ComiteDiario.DECISAO_CHOICES)

    data_negociacao = _parse_date_ou_none(post_data.get("data_negociacao"))
    data_vencimento = _parse_date_ou_none(post_data.get("data_vencimento"))
    data_prorrogada = _parse_date_ou_none(post_data.get("data_prorrogada"))

    empresa_titular = _obter_empresa_titular_por_id(empresa, post_data.get("empresa_titular_id"))
    para_empresa = _obter_empresa_titular_por_id(empresa, post_data.get("para_empresa_id"))

    parceiro = Parceiro.objects.filter(
        id=post_data.get("parceiro_id"),
        empresa=empresa,
    ).first()
    natureza = Natureza.objects.filter(
        id=post_data.get("natureza_id"),
        empresa=empresa,
    ).first()
    centro_resultado = CentroResultado.objects.filter(
        id=post_data.get("centro_resultado_id"),
        empresa=empresa,
    ).first()
    de_banco = _obter_banco_por_id(empresa, post_data.get("de_banco_id"))
    para_banco = _obter_banco_por_id(empresa, post_data.get("para_banco_id"))

    if decisao != ComiteDiario.DECISAO_TRANSFERIR:
        de_banco = None
        para_banco = None
        para_empresa = None
    if decisao != ComiteDiario.DECISAO_ADIAR:
        data_prorrogada = None

    return {
        "data_negociacao_raw": (post_data.get("data_negociacao") or "").strip(),
        "data_vencimento_raw": (post_data.get("data_vencimento") or "").strip(),
        "data_negociacao": data_negociacao,
        "data_vencimento": data_vencimento,
        "receita_despesa": receita_despesa,
        "empresa_titular": empresa_titular,
        "parceiro": parceiro,
        "natureza": natureza,
        "centro_resultado": centro_resultado,
        "historico": (post_data.get("historico") or "").strip(),
        "numero_nota": _parse_int_ou_zero(post_data.get("numero_nota")),
        "valor_liquido": _parse_decimal_ou_zero(post_data.get("valor_liquido")),
        "tipo_movimento": tipo_movimento,
        "decisao": decisao,
        "data_prorrogada": data_prorrogada,
        "de_banco": de_banco,
        "para_banco": para_banco,
        "para_empresa": para_empresa,
    }


def _validar_dados_comite_diario(dados):
    if not dados["data_negociacao_raw"]:
        return "Data de negociacao e obrigatoria."
    if not dados["data_negociacao"]:
        return "Data de negociacao invalida."
    if not dados["data_vencimento_raw"]:
        return "Data de vencimento e obrigatoria."
    if not dados["data_vencimento"]:
        return "Data de vencimento invalida."
    if not dados["receita_despesa"]:
        return "Receita/Despesa e obrigatorio."
    if not dados["empresa_titular"]:
        return "Empresa titular e obrigatoria."
    if not dados["parceiro"]:
        return "Parceiro e obrigatorio."
    if not dados["natureza"]:
        return "Natureza e obrigatoria."
    if not dados["centro_resultado"]:
        return "Centro de resultado e obrigatorio."
    if not dados["historico"]:
        return "Historico e obrigatorio."
    if dados["numero_nota"] <= 0:
        return "Numero da nota e obrigatorio."
    if not dados["tipo_movimento"]:
        return "Tipo de movimento e obrigatorio."
    if not dados["decisao"]:
        return "Decisao e obrigatoria."

    return ""


def criar_comite_diario_por_dados(empresa, post_data):
    dados = _dados_comite_diario_from_post(empresa, post_data)
    erro = _validar_dados_comite_diario(dados)
    if erro:
        return erro

    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    ComiteDiario.criar_comite_diario(empresa=empresa, **dados)
    return ""


def atualizar_comite_diario_por_dados(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_comite_diario_from_post(empresa, post_data)
    erro = _validar_dados_comite_diario(dados)
    if erro:
        return erro

    dados.pop("data_negociacao_raw", None)
    dados.pop("data_vencimento_raw", None)
    item.atualizar_comite_diario(**dados)
    return ""


def excluir_comite_diario_por_dados(item, empresa):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."
    item.excluir_comite_diario()
    return ""


def _dados_balanco_patrimonial_from_post(post_data):
    data_lancamento_raw = (post_data.get("data_lancamento") or "").strip()
    data_balanco_raw = (post_data.get("data_balanco_patrimonial") or "").strip()
    valor_raw = (post_data.get("valor") or "").strip()

    return {
        "data_lancamento_raw": data_lancamento_raw,
        "data_lancamento": _parse_date_ou_none(data_lancamento_raw),
        "data_balanco_patrimonial_raw": data_balanco_raw,
        "data_balanco_patrimonial": _parse_date_ou_none(data_balanco_raw),
        "empresa_balanco_patrimonial": _choice_valido(
            post_data.get("empresa_balanco_patrimonial"),
            BalancoPatrimonial.EMPRESA_BALANCO_PATRIMONIAL_CHOICES,
        ),
        "tipo_movimentacao": _choice_valido(
            post_data.get("tipo_movimentacao"),
            BalancoPatrimonial.TIPO_MOVIMENTACAO_CHOICES,
        ),
        "descricao": (post_data.get("descricao") or "").strip(),
        "valor_raw": valor_raw,
        "valor": _parse_decimal_ou_zero(valor_raw),
        "observacao": (post_data.get("observacao") or "").strip(),
    }


def _validar_dados_balanco_patrimonial(dados):
    if dados["data_lancamento_raw"] and not dados["data_lancamento"]:
        return "Data lancamento invalida."
    if not dados["data_balanco_patrimonial_raw"]:
        return "Data BP e obrigatoria."
    if not dados["data_balanco_patrimonial"]:
        return "Data BP invalida."
    if not dados["empresa_balanco_patrimonial"]:
        return "Empresa BP e obrigatoria."
    if not dados["descricao"]:
        return "Descricao BP e obrigatoria."
    if not dados["valor_raw"]:
        return "Valor e obrigatorio."
    return ""


def criar_balanco_patrimonial_por_dados(empresa, post_data):
    dados = _dados_balanco_patrimonial_from_post(post_data)
    erro = _validar_dados_balanco_patrimonial(dados)
    if erro:
        return erro

    dados.pop("data_lancamento_raw", None)
    dados.pop("data_balanco_patrimonial_raw", None)
    dados.pop("valor_raw", None)
    dados["numero_registro"] = BalancoPatrimonial.proximo_numero_registro(empresa)
    BalancoPatrimonial.criar_balanco_patrimonial(empresa=empresa, **dados)
    return ""


def atualizar_balanco_patrimonial_por_dados(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_balanco_patrimonial_from_post(post_data)
    erro = _validar_dados_balanco_patrimonial(dados)
    if erro:
        return erro

    dados.pop("data_lancamento_raw", None)
    dados.pop("data_balanco_patrimonial_raw", None)
    dados.pop("valor_raw", None)
    item.atualizar_balanco_patrimonial(**dados)
    return ""


def excluir_balanco_patrimonial_por_dados(item, empresa):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."
    item.excluir_balanco_patrimonial()
    return ""


def _parse_bool_like(valor):
    texto = str(valor or "").strip().lower()
    return texto in {"1", "true", "on", "sim", "yes", "verdadeiro"}


def _dados_balanco_patrimonial_ativo_from_post(post_data):
    data_aquisicao_raw = (post_data.get("data_aquisicao") or "").strip()
    categoria = _choice_valido(post_data.get("categoria"), BalancoPatrimonialAtivo.CATEGORIA_CHOICES)
    empresa_bp = _choice_valido(post_data.get("empresa_bp"), BalancoPatrimonialAtivo.EMPRESA_BP_CHOICES)
    status_financiado = _parse_bool_like(post_data.get("status_financiado"))

    parcelas_raw = (post_data.get("parcelas") or "").strip()
    parcelas = _parse_int_ou_zero(parcelas_raw) if parcelas_raw else None
    if parcelas is not None and parcelas <= 0:
        parcelas = None

    dados = {
        "data_aquisicao_raw": data_aquisicao_raw,
        "data_aquisicao": _parse_date_ou_none(data_aquisicao_raw),
        "empresa_bp": empresa_bp,
        "categoria": categoria,
        "sub_categoria": (post_data.get("sub_categoria") or "").strip(),
        "secao": (post_data.get("secao") or "").strip(),
        "nivel": (post_data.get("nivel") or "").strip(),
        "patrimonio": (post_data.get("patrimonio") or "").strip(),
        "placa": (post_data.get("placa") or "").strip().upper(),
        "local": (post_data.get("local") or "").strip(),
        "renda": _parse_decimal_ou_none(post_data.get("renda")),
        "ano": (post_data.get("ano") or "").strip(),
        "valor_bem": _parse_decimal_ou_none(post_data.get("valor_bem")),
        "valor_real_atual": _parse_decimal_ou_none(post_data.get("valor_real_atual")),
        "valor_venda_forcada": _parse_decimal_ou_none(post_data.get("valor_venda_forcada")),
        "valor_declarado_ir": _parse_decimal_ou_none(post_data.get("valor_declarado_ir")),
        "valor_avaliacao": _parse_decimal_ou_none(post_data.get("valor_avaliacao")),
        "quitacao": _parse_decimal_ou_none(post_data.get("quitacao")),
        "alienacao": _parse_decimal_ou_none(post_data.get("alienacao")),
        "parcelas": parcelas,
        "valor_parcela": _parse_decimal_ou_none(post_data.get("valor_parcela")),
        "passivo": _parse_decimal_ou_none(post_data.get("passivo")),
        "valor_liquido": _parse_decimal_ou_none(post_data.get("valor_liquido")),
        "status_financiado": status_financiado,
        "status": (post_data.get("status") or "").strip(),
    }

    if categoria != BalancoPatrimonialAtivo.CATEGORIA_VEICULOS:
        dados["placa"] = ""
        dados["ano"] = ""
    if categoria != BalancoPatrimonialAtivo.CATEGORIA_IMOVEL:
        dados["local"] = ""
        dados["renda"] = None
    if not status_financiado:
        dados["quitacao"] = None
        dados["alienacao"] = None
        dados["parcelas"] = None
        dados["valor_parcela"] = None
        dados["passivo"] = None

    return dados


def _validar_dados_balanco_patrimonial_ativo(dados):
    if dados["data_aquisicao_raw"] and not dados["data_aquisicao"]:
        return "Data aquisicao invalida."
    if not dados["empresa_bp"]:
        return "Empresa BP e obrigatoria."
    if not dados["categoria"]:
        return "Categoria e obrigatoria."
    return ""


def criar_balanco_patrimonial_ativo_por_dados(empresa, post_data):
    dados = _dados_balanco_patrimonial_ativo_from_post(post_data)
    erro = _validar_dados_balanco_patrimonial_ativo(dados)
    if erro:
        return erro

    dados.pop("data_aquisicao_raw", None)
    BalancoPatrimonialAtivo.criar_balanco_patrimonial_ativo(empresa=empresa, **dados)
    return ""


def atualizar_balanco_patrimonial_ativo_por_dados(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."

    dados = _dados_balanco_patrimonial_ativo_from_post(post_data)
    erro = _validar_dados_balanco_patrimonial_ativo(dados)
    if erro:
        return erro

    dados.pop("data_aquisicao_raw", None)
    item.atualizar_balanco_patrimonial_ativo(**dados)
    return ""


def excluir_balanco_patrimonial_ativo_por_dados(item, empresa):
    if item.empresa_id != empresa.id:
        return "Registro invalido para esta empresa."
    item.excluir_balanco_patrimonial_ativo()
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


def criar_descricao_perfil_por_dados(empresa, descricao):
    descricao = (descricao or "").strip()
    if not descricao:
        return "Descricao do perfil e obrigatoria."
    if DescricaoPerfil.objects.filter(empresa=empresa, descricao__iexact=descricao).exists():
        return "Ja existe descricao de perfil com este nome nesta empresa."
    DescricaoPerfil.criar_descricao_perfil(empresa=empresa, descricao=descricao)
    return ""


def atualizar_descricao_perfil_por_dados(item, descricao, empresa):
    descricao = (descricao or "").strip()
    if not descricao:
        return "Descricao do perfil e obrigatoria."
    if item.empresa_id != empresa.id:
        return "Descricao de perfil invalida para esta empresa."
    if (
        DescricaoPerfil.objects.filter(empresa=empresa, descricao__iexact=descricao)
        .exclude(id=item.id)
        .exists()
    ):
        return "Ja existe descricao de perfil com este nome nesta empresa."
    item.atualizar_descricao_perfil(descricao=descricao)
    return ""


def _dados_parametro_meta_from_post(post_data, empresa):
    descricao_perfil = DescricaoPerfil.objects.filter(
        id=post_data.get("descricao_perfil_id"),
        empresa=empresa,
    ).first()
    return {
        "descricao_perfil": descricao_perfil,
        "meta_acabado_percentual": _parse_percentual_ratio_ou_none_aceitando_inteiro_como_percentual(
            post_data.get("meta_acabado_percentual")
        ),
        "valor_meta_pd_acabado": _parse_decimal_ou_none(post_data.get("valor_meta_pd_acabado")),
        "meta_mt_prima_percentual": _parse_percentual_ratio_ou_none_aceitando_inteiro_como_percentual(
            post_data.get("meta_mt_prima_percentual")
        ),
    }


def criar_parametro_meta_por_dados(empresa, post_data):
    dados = _dados_parametro_meta_from_post(post_data, empresa)
    descricao_perfil = dados["descricao_perfil"]
    if not descricao_perfil:
        return "Descricao perfil invalida."
    if ParametroMeta.objects.filter(empresa=empresa, descricao_perfil=descricao_perfil).exists():
        return "Ja existe parametro de metas para esta descricao perfil."

    ParametroMeta.criar_parametro_meta(
        empresa=empresa,
        descricao_perfil=descricao_perfil,
        meta_acabado_percentual=dados["meta_acabado_percentual"],
        valor_meta_pd_acabado=dados["valor_meta_pd_acabado"],
        meta_mt_prima_percentual=dados["meta_mt_prima_percentual"],
    )
    return ""


def atualizar_parametro_meta_por_dados(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Parametro de metas invalido para esta empresa."

    dados = _dados_parametro_meta_from_post(post_data, empresa)
    descricao_perfil = dados["descricao_perfil"]
    if not descricao_perfil:
        return "Descricao perfil invalida."
    if (
        ParametroMeta.objects.filter(empresa=empresa, descricao_perfil=descricao_perfil)
        .exclude(id=item.id)
        .exists()
    ):
        return "Ja existe parametro de metas para esta descricao perfil."

    item.atualizar_parametro_meta(
        descricao_perfil=descricao_perfil,
        meta_acabado_percentual=dados["meta_acabado_percentual"],
        valor_meta_pd_acabado=dados["valor_meta_pd_acabado"],
        meta_mt_prima_percentual=dados["meta_mt_prima_percentual"],
    )
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


def _normalizar_status_contrato(valor):
    texto = (valor or "").strip()
    if texto.lower() == "ativo":
        return ContratoRede.STATUS_ATIVO
    if texto.lower() == "inativo":
        return ContratoRede.STATUS_INATIVO
    return ""


def _dados_contrato_rede_from_post(post_data, empresa):
    data_inicio_raw = (post_data.get("data_inicio") or "").strip()
    data_encerramento_raw = (post_data.get("data_encerramento") or "").strip()
    parceiro_id = str(post_data.get("parceiro_id") or "").strip()

    parceiro = None
    if parceiro_id:
        try:
            parceiro_id_int = int(parceiro_id)
        except (TypeError, ValueError):
            parceiro_id_int = None
        if parceiro_id_int and parceiro_id_int > 0:
            parceiro = Parceiro.objects.filter(id=parceiro_id_int, empresa=empresa).first()

    valor_acordo_raw = (post_data.get("valor_acordo") or "").strip()
    return {
        "codigo_registro": (post_data.get("codigo_registro") or "").strip(),
        "numero_contrato": (post_data.get("numero_contrato") or "").strip(),
        "data_inicio_raw": data_inicio_raw,
        "data_inicio": _parse_date_ou_none(data_inicio_raw),
        "data_encerramento_raw": data_encerramento_raw,
        "data_encerramento": _parse_date_ou_none(data_encerramento_raw),
        "parceiro_id_raw": parceiro_id,
        "parceiro": parceiro,
        "descricao_acordos": (post_data.get("descricao_acordos") or "").strip(),
        "valor_acordo_raw": valor_acordo_raw,
        "valor_acordo": _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(valor_acordo_raw),
        "status_contrato": _normalizar_status_contrato(post_data.get("status_contrato")),
    }


def _validar_dados_contrato_rede(dados):
    if not dados["codigo_registro"]:
        return "Codigo de registro e obrigatorio."
    if not dados["numero_contrato"]:
        return "Numero do contrato e obrigatorio."
    if not dados["data_inicio_raw"]:
        return "Data de inicio e obrigatoria."
    if not dados["data_inicio"]:
        return "Data de inicio invalida."
    if dados["data_encerramento_raw"] and not dados["data_encerramento"]:
        return "Data de encerramento invalida."
    if dados["data_encerramento"] and dados["data_encerramento"] < dados["data_inicio"]:
        return "Data de encerramento nao pode ser menor que a data de inicio."
    if dados["parceiro_id_raw"] and not dados["parceiro"]:
        return "Parceiro invalido para o contrato."
    if not dados["descricao_acordos"]:
        return "Descricao dos acordos e obrigatoria."
    if not dados["valor_acordo_raw"]:
        return "Valor do acordo e obrigatorio."
    if not dados["status_contrato"]:
        return "Status do contrato invalido. Use Ativo ou Inativo."
    return ""


def criar_contrato_rede_por_post(empresa, post_data):
    dados = _dados_contrato_rede_from_post(post_data, empresa)
    erro = _validar_dados_contrato_rede(dados)
    if erro:
        return erro

    ContratoRede.criar_contrato_rede(
        empresa=empresa,
        codigo_registro=dados["codigo_registro"],
        numero_contrato=dados["numero_contrato"],
        data_inicio=dados["data_inicio"],
        data_encerramento=dados["data_encerramento"],
        parceiro=dados["parceiro"],
        descricao_acordos=dados["descricao_acordos"],
        valor_acordo=dados["valor_acordo"],
        status_contrato=dados["status_contrato"],
    )
    return ""


def atualizar_contrato_rede_por_post(contrato, empresa, post_data):
    if contrato.empresa_id != empresa.id:
        return "Contrato invalido para esta empresa."

    dados = _dados_contrato_rede_from_post(post_data, empresa)
    erro = _validar_dados_contrato_rede(dados)
    if erro:
        return erro

    contrato.atualizar_contrato_rede(
        codigo_registro=dados["codigo_registro"],
        numero_contrato=dados["numero_contrato"],
        data_inicio=dados["data_inicio"],
        data_encerramento=dados["data_encerramento"],
        parceiro=dados["parceiro"],
        descricao_acordos=dados["descricao_acordos"],
        valor_acordo=dados["valor_acordo"],
        status_contrato=dados["status_contrato"],
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


def _parse_percentual_ratio_ou_none_aceitando_inteiro_como_percentual(valor):
    texto = (valor or "").strip()
    if not texto:
        return None
    return _parse_percentual_ratio_ou_zero_aceitando_inteiro_como_percentual(texto)


def _parse_date_ou_none(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_time_ou_none(valor):
    if not valor:
        return None
    texto = (valor or "").strip()
    formatos = (
        "%H:%M",
        "%H:%M:%S",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).time()
        except (TypeError, ValueError):
            continue
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
    descricao_perfil = _sincronizar_descricao_perfil(
        empresa,
        post_data.get("descricao_perfil"),
        vazio_como_none=True,
    )

    return {
        "nro_unico_raw": nro_unico_raw,
        "nro_unico": _parse_int_ou_zero(nro_unico_raw),
        "data_origem": data_origem,
        "nome_empresa": nome_empresa,
        "parceiro": parceiro,
        "cod_nome_parceiro": cod_nome_parceiro,
        "descricao_perfil": descricao_perfil,
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


PRECIFICACAO_PRODUTOS_CONFIG = [
    {
        "chave": "30x1",
        "descricao": "30x1",
        "acucar_base": Decimal("30"),
        "emb_primaria_base": Decimal("0.15"),
        "emb_secundaria_base": Decimal("0.042"),
        "emb_primaria_chave": "emb_primaria_kg",
        "emb_secundaria_chave": "emb_secundaria_kg",
        "peso_base": Decimal("30"),
        "default_pv_bruto": Decimal("63.21"),
        "default_producao_valor": Decimal("1.4"),
        "default_interno_imposto": True,
    },
    {
        "chave": "15x2",
        "descricao": "15x2",
        "acucar_base": Decimal("30"),
        "emb_primaria_base": Decimal("0.105"),
        "emb_secundaria_base": Decimal("0.042"),
        "emb_primaria_chave": "emb_primaria_kg",
        "emb_secundaria_chave": "emb_secundaria_kg",
        "peso_base": Decimal("30"),
        "default_pv_bruto": Decimal("81"),
        "default_producao_valor": Decimal("1.4"),
        "default_interno_imposto": True,
    },
    {
        "chave": "6x5",
        "descricao": "6x5",
        "acucar_base": Decimal("30"),
        "emb_primaria_base": Decimal("0.09"),
        "emb_secundaria_base": Decimal("0.042"),
        "emb_primaria_chave": "emb_primaria_kg",
        "emb_secundaria_chave": "emb_secundaria_kg",
        "peso_base": Decimal("30"),
        "default_pv_bruto": Decimal("68"),
        "default_producao_valor": Decimal("1.4"),
        "default_interno_imposto": True,
    },
    {
        "chave": "25",
        "descricao": "25",
        "acucar_base": Decimal("25"),
        "emb_primaria_base": Decimal("1"),
        "emb_secundaria_base": Decimal("0"),
        "emb_primaria_chave": "sacaria_25_un",
        "emb_secundaria_chave": "",
        "peso_base": Decimal("25"),
        "default_pv_bruto": Decimal("0"),
        "default_producao_valor": Decimal("1.4"),
        "default_interno_imposto": False,
    },
    {
        "chave": "50",
        "descricao": "50",
        "acucar_base": Decimal("50"),
        "emb_primaria_base": Decimal("1"),
        "emb_secundaria_base": Decimal("0"),
        "emb_primaria_chave": "sacaria_50_un",
        "emb_secundaria_chave": "",
        "peso_base": Decimal("50"),
        "default_pv_bruto": Decimal("0"),
        "default_producao_valor": Decimal("2"),
        "default_interno_imposto": False,
    },
]

PRECIFICACAO_MATERIA_PRIMA_BASE_FRETE_CHAVES = {
    "emb_primaria_kg",
    "emb_secundaria_kg",
    "sacaria_25_un",
    "sacaria_50_un",
}

PRECIFICACAO_MATERIA_PRIMA_CAMPOS_PROTEGIDOS = {
    "acucar_sc": {"valor", "frete_mp"},
    "acucar_kg": {"valor"},
}


def _precificacao_decimal(valor, default=Decimal("0")):
    if valor in (None, ""):
        return default
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _precificacao_quantize(valor, casas=6):
    numero = _precificacao_decimal(valor, Decimal("0"))
    try:
        casas_int = int(casas)
    except (TypeError, ValueError):
        casas_int = 6
    if casas_int < 0:
        casas_int = 6
    passo = Decimal("1").scaleb(-casas_int)
    try:
        return numero.quantize(passo, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0")


def _precificacao_bool(valor):
    texto = str(valor or "").strip().lower()
    return texto in {"1", "true", "on", "sim", "yes", "verdadeiro"}


def _seed_precificacao_cenario(cenario):
    origens_padrao = [
        ("GOIASA", Decimal("4071.11"), Decimal("88"), Decimal("0"), Decimal("6.2")),
        ("SONORA", Decimal("18888"), Decimal("93.5"), Decimal("0"), Decimal("0")),
        ("CAMBUI", Decimal("1669.72"), Decimal("88"), Decimal("0"), Decimal("6.2")),
        ("VALE", Decimal("15728.04"), Decimal("87.86"), Decimal("0"), Decimal("6.2")),
    ]
    for ordem, (origem, volume, preco, prazo, frete) in enumerate(origens_padrao, start=1):
        PrecificacaoCalculadoraPrecoMedio.objects.get_or_create(
            cenario=cenario,
            origem=origem,
            defaults={
                "ordem": ordem,
                "volume": volume,
                "preco": preco,
                "prazo": prazo,
                "frete": frete,
            },
        )

    PrecificacaoSimulacaoCompraVenda.objects.get_or_create(
        cenario=cenario,
        defaults={
            "margem_requerida_compra": Decimal("0.035"),
            "margem_requerida_venda": Decimal("0.035"),
            "frete_compra": Decimal("4.7"),
            "frete_venda": Decimal("66.5"),
        },
    )

    materias_primas = [
        ("acucar_sc", "Acucar (SC)", True, Decimal("0"), Decimal("0"), Decimal("0.07")),
        ("acucar_kg", "Acucar (Kg)", True, Decimal("0"), Decimal("0"), Decimal("0.07")),
        ("emb_primaria_kg", "Emb. Primaria (Kg)", True, Decimal("0"), Decimal("14.92"), Decimal("0.07")),
        ("emb_secundaria_kg", "Emb. Secundaria (Kg)", True, Decimal("0"), Decimal("12.35"), Decimal("0.07")),
        ("sacaria_25_un", "Sacaria 25 KG (Un)", True, Decimal("0"), Decimal("1.03"), Decimal("0.07")),
        ("sacaria_50_un", "Sacaria 50 KG (Un)", True, Decimal("0"), Decimal("1.37"), Decimal("0.07")),
    ]
    for ordem, (chave, descricao, ativo, valor, frete_mp, credito) in enumerate(materias_primas, start=1):
        PrecificacaoMateriaPrima.objects.get_or_create(
            cenario=cenario,
            chave=chave,
            defaults={
                "ordem": ordem,
                "descricao": descricao,
                "ativo": ativo,
                "valor": valor,
                "frete_mp": frete_mp,
                "credito": credito,
            },
        )

    for ordem, conf in enumerate(PRECIFICACAO_PRODUTOS_CONFIG, start=1):
        chave = conf["chave"]
        descricao = conf["descricao"]
        PrecificacaoProdutoAcabadoCMV.objects.get_or_create(
            cenario=cenario,
            chave=chave,
            defaults={
                "ordem": ordem,
                "descricao": descricao,
                "acucar_quebra": Decimal("0.005"),
                "emb_primaria_quebra": Decimal("0.015") if chave in {"30x1", "15x2", "6x5"} else Decimal("0"),
                "emb_secundaria_quebra": Decimal("0.015") if chave in {"30x1", "15x2", "6x5"} else Decimal("0"),
            },
        )
        PrecificacaoProdutoAcabadoDespesa.objects.get_or_create(
            cenario=cenario,
            chave=chave,
            defaults={
                "ordem": ordem,
                "descricao": descricao,
                "prazo_dias": Decimal("0"),
                "financeiro_taxa": Decimal("0.02"),
                "inadimplencia_taxa": Decimal("0.0015"),
                "administracao_taxa": Decimal("0.0075"),
                "producao_ativo": True,
                "producao_valor": conf["default_producao_valor"],
                "cif_ativo": False,
                "cif_manual_ativo": False,
                "cif_rota": "BRASILIA",
                "log_op_logistica_ativo": True,
            },
        )
        PrecificacaoProdutoAcabadoImposto.objects.get_or_create(
            cenario=cenario,
            chave=chave,
            defaults={
                "ordem": ordem,
                "descricao": descricao,
                "interno_ativo": conf["default_interno_imposto"],
                "imposto_aliquota": Decimal("0.11"),
                "imposto_interno_aliquota": Decimal("0.07"),
                "pro_goias_ativo": True,
                "pro_goias_aliquota_a": Decimal("0.00256"),
                "pro_goias_aliquota_b": Decimal("0.01864"),
            },
        )
        PrecificacaoProdutoAcabadoPrecoVenda.objects.get_or_create(
            cenario=cenario,
            chave=chave,
            defaults={
                "ordem": ordem,
                "descricao": descricao,
                "pv_bruto": conf["default_pv_bruto"],
                "interno_ativo": True,
                "comissao_aliquota": Decimal("0.0115"),
                "contrato_aliquota": Decimal("0"),
            },
        )


def obter_ou_criar_cenario_precificacao(empresa):
    cenario = (
        PrecificacaoCenario.objects.filter(empresa=empresa, ativo=True)
        .order_by("id")
        .first()
    )
    if not cenario:
        cenario = PrecificacaoCenario.criar_precificacao_cenario(empresa=empresa, nome="Cenario padrao", ativo=True)
    _seed_precificacao_cenario(cenario)
    recalcular_precificacao_cenario(cenario)
    return cenario


def listar_tabelas_precificacao(cenario):
    return {
        "calculadora": PrecificacaoCalculadoraPrecoMedio.objects.filter(cenario=cenario).order_by("ordem", "id"),
        "simulacao": PrecificacaoSimulacaoCompraVenda.objects.filter(cenario=cenario).order_by("id"),
        "materia_prima": PrecificacaoMateriaPrima.objects.filter(cenario=cenario).order_by("ordem", "id"),
        "produto_cmv": PrecificacaoProdutoAcabadoCMV.objects.filter(cenario=cenario).order_by("ordem", "id"),
        "produto_despesas": PrecificacaoProdutoAcabadoDespesa.objects.filter(cenario=cenario).order_by("ordem", "id"),
        "produto_impostos": PrecificacaoProdutoAcabadoImposto.objects.filter(cenario=cenario).order_by("ordem", "id"),
        "produto_preco_venda": PrecificacaoProdutoAcabadoPrecoVenda.objects.filter(cenario=cenario).order_by("ordem", "id"),
    }


def _precificacao_situacao_por_percentual(percentual):
    valor = _precificacao_decimal(percentual)
    if valor <= Decimal("0.02"):
        return (
            PrecificacaoProdutoAcabadoPrecoVenda.SITUACAO_DIRECAO,
            "roxo",
        )
    if valor <= Decimal("0.04"):
        return (
            PrecificacaoProdutoAcabadoPrecoVenda.SITUACAO_GERENTE_COMERCIAL,
            "vermelho",
        )
    if valor <= Decimal("0.05"):
        return (
            PrecificacaoProdutoAcabadoPrecoVenda.SITUACAO_SUPERVISOR,
            "amarelo",
        )
    return (
        PrecificacaoProdutoAcabadoPrecoVenda.SITUACAO_VENDEDOR,
        "verde",
    )


def recalcular_precificacao_cenario(cenario):
    calculadora = list(PrecificacaoCalculadoraPrecoMedio.objects.filter(cenario=cenario).order_by("ordem", "id"))
    materia_prima = list(PrecificacaoMateriaPrima.objects.filter(cenario=cenario).order_by("ordem", "id"))
    cmv_rows = list(PrecificacaoProdutoAcabadoCMV.objects.filter(cenario=cenario).order_by("ordem", "id"))
    despesas_rows = list(
        PrecificacaoProdutoAcabadoDespesa.objects.filter(cenario=cenario).order_by("ordem", "id")
    )
    impostos_rows = list(
        PrecificacaoProdutoAcabadoImposto.objects.filter(cenario=cenario).order_by("ordem", "id")
    )
    preco_rows = list(
        PrecificacaoProdutoAcabadoPrecoVenda.objects.filter(cenario=cenario).order_by("ordem", "id")
    )
    simulacao = PrecificacaoSimulacaoCompraVenda.objects.filter(cenario=cenario).first()

    if simulacao is None:
        simulacao = PrecificacaoSimulacaoCompraVenda.criar_item(cenario=cenario)

    for linha in calculadora:
        preco = _precificacao_decimal(linha.preco)
        prazo = _precificacao_decimal(linha.prazo)
        frete = _precificacao_decimal(linha.frete)
        preco_liquido = preco - prazo
        financeiro = (Decimal("0.02") / Decimal("30")) * prazo * preco
        total = preco_liquido + frete
        linha.preco_liquido = _precificacao_quantize(preco_liquido, casas=4)
        linha.financeiro = _precificacao_quantize(financeiro, casas=4)
        linha.total = _precificacao_quantize(total, casas=4)
    if calculadora:
        PrecificacaoCalculadoraPrecoMedio.objects.bulk_update(
            calculadora,
            ["preco_liquido", "financeiro", "total"],
            batch_size=100,
        )

    volume_total = Decimal("0")
    weighted_preco_liquido = Decimal("0")
    weighted_frete = Decimal("0")
    for linha in calculadora:
        volume = _precificacao_decimal(linha.volume)
        if volume <= 0:
            continue
        volume_total += volume
        weighted_preco_liquido += volume * _precificacao_decimal(linha.preco_liquido)
        weighted_frete += volume * _precificacao_decimal(linha.frete)
    media_preco_liquido = (weighted_preco_liquido / volume_total) if volume_total > 0 else Decimal("0")
    media_frete = (weighted_frete / volume_total) if volume_total > 0 else Decimal("0")
    subtotal_acucar_sc = media_preco_liquido + media_frete

    materia_por_chave = {item.chave: item for item in materia_prima}
    acucar_sc = materia_por_chave.get("acucar_sc")
    acucar_kg = materia_por_chave.get("acucar_kg")
    if acucar_sc:
        acucar_sc.ativo = True
        acucar_sc.valor = _precificacao_quantize(media_preco_liquido)
        acucar_sc.frete_mp = _precificacao_quantize(media_frete)
    if acucar_kg:
        acucar_kg.ativo = True
        acucar_kg.valor = _precificacao_quantize(subtotal_acucar_sc / Decimal("50"))
        acucar_kg.frete_mp = Decimal("0")

    for linha in materia_prima:
        valor = _precificacao_decimal(linha.valor)
        frete = _precificacao_decimal(linha.frete_mp)
        credito = _precificacao_decimal(linha.credito)

        # Compatibilidade com cenarios antigos: embalagens/sacarias eram salvas em "valor"
        # e no legado a base dessa faixa sempre fica na coluna equivalente ao "frete_mp".
        if linha.chave in PRECIFICACAO_MATERIA_PRIMA_BASE_FRETE_CHAVES and frete == 0 and valor > 0:
            frete = valor
            linha.frete_mp = _precificacao_quantize(frete)
        if linha.chave in PRECIFICACAO_MATERIA_PRIMA_BASE_FRETE_CHAVES and valor != 0:
            valor = Decimal("0")
            linha.valor = Decimal("0")

        if linha.chave == "acucar_sc":
            sub_total = valor + frete
            base_custo = sub_total
        elif linha.chave == "acucar_kg":
            sub_total = Decimal("0")
            base_custo = valor
        elif linha.chave in PRECIFICACAO_MATERIA_PRIMA_BASE_FRETE_CHAVES:
            sub_total = Decimal("0")
            base_custo = frete
        else:
            sub_total = valor + frete
            base_custo = sub_total

        custo_ex_works = (Decimal("1") - credito) * base_custo
        linha.sub_total = _precificacao_quantize(sub_total)
        linha.custo_ex_works = _precificacao_quantize(custo_ex_works)

    if materia_prima:
        PrecificacaoMateriaPrima.objects.bulk_update(
            materia_prima,
            ["ativo", "valor", "frete_mp", "sub_total", "custo_ex_works"],
            batch_size=100,
        )

    materia_por_chave = {item.chave: item for item in materia_prima}

    def _valor_material(chave, ex_works=False):
        if not chave:
            return Decimal("0")
        item = materia_por_chave.get(chave)
        if not item or not item.ativo:
            return Decimal("0")
        if ex_works:
            return _precificacao_decimal(item.custo_ex_works)
        if chave in PRECIFICACAO_MATERIA_PRIMA_BASE_FRETE_CHAVES:
            return _precificacao_decimal(item.frete_mp)
        return _precificacao_decimal(item.valor)

    conf_por_chave = {item["chave"]: item for item in PRECIFICACAO_PRODUTOS_CONFIG}
    cmv_por_chave = {item.chave: item for item in cmv_rows}

    for linha in cmv_rows:
        conf = conf_por_chave.get(linha.chave)
        if not conf:
            continue
        acucar_qtd = (Decimal("1") + _precificacao_decimal(linha.acucar_quebra)) * conf["acucar_base"]
        acucar_valor = acucar_qtd * _valor_material("acucar_kg", ex_works=False)
        acucar_valor_ex = acucar_qtd * _valor_material("acucar_kg", ex_works=True)

        emb_primaria_qtd = (Decimal("1") + _precificacao_decimal(linha.emb_primaria_quebra)) * conf["emb_primaria_base"]
        emb_primaria_valor = emb_primaria_qtd * _valor_material(conf["emb_primaria_chave"], ex_works=False)
        emb_primaria_valor_ex = emb_primaria_qtd * _valor_material(conf["emb_primaria_chave"], ex_works=True)

        emb_sec_qtd = (Decimal("1") + _precificacao_decimal(linha.emb_secundaria_quebra)) * conf["emb_secundaria_base"]
        emb_sec_valor = emb_sec_qtd * _valor_material(conf["emb_secundaria_chave"], ex_works=False)
        emb_sec_valor_ex = emb_sec_qtd * _valor_material(conf["emb_secundaria_chave"], ex_works=True)

        cmv = acucar_valor + emb_primaria_valor + emb_sec_valor
        cmv_ex = acucar_valor_ex + emb_primaria_valor_ex + emb_sec_valor_ex

        linha.acucar_qtd = _precificacao_quantize(acucar_qtd)
        linha.acucar_valor = _precificacao_quantize(acucar_valor)
        linha.acucar_valor_ex_works = _precificacao_quantize(acucar_valor_ex)
        linha.emb_primaria_qtd = _precificacao_quantize(emb_primaria_qtd)
        linha.emb_primaria_valor = _precificacao_quantize(emb_primaria_valor)
        linha.emb_primaria_valor_ex_works = _precificacao_quantize(emb_primaria_valor_ex)
        linha.emb_secundaria_qtd = _precificacao_quantize(emb_sec_qtd)
        linha.emb_secundaria_valor = _precificacao_quantize(emb_sec_valor)
        linha.emb_secundaria_valor_ex_works = _precificacao_quantize(emb_sec_valor_ex)
        linha.cmv = _precificacao_quantize(cmv)
        linha.cmv_ex_works = _precificacao_quantize(cmv_ex)

    if cmv_rows:
        PrecificacaoProdutoAcabadoCMV.objects.bulk_update(
            cmv_rows,
            [
                "acucar_qtd",
                "acucar_valor",
                "acucar_valor_ex_works",
                "emb_primaria_qtd",
                "emb_primaria_valor",
                "emb_primaria_valor_ex_works",
                "emb_secundaria_qtd",
                "emb_secundaria_valor",
                "emb_secundaria_valor_ex_works",
                "cmv",
                "cmv_ex_works",
            ],
            batch_size=100,
        )

    preco_por_chave = {item.chave: item for item in preco_rows}
    for linha in preco_rows:
        cmv_item = cmv_por_chave.get(linha.chave)
        pv_bruto = _precificacao_decimal(linha.pv_bruto)
        cmv = _precificacao_decimal(cmv_item.cmv if cmv_item else 0)
        comissao_valor = _precificacao_decimal(linha.comissao_aliquota) * pv_bruto
        contrato_valor = _precificacao_decimal(linha.contrato_aliquota) * pv_bruto
        subtotal = pv_bruto - comissao_valor - contrato_valor
        cmv_estimado = (cmv / pv_bruto) if pv_bruto > 0 else Decimal("0")
        linha.comissao_valor = _precificacao_quantize(comissao_valor)
        linha.contrato_valor = _precificacao_quantize(contrato_valor)
        linha.subtotal = _precificacao_quantize(subtotal)
        linha.cmv_estimado = _precificacao_quantize(cmv_estimado)

    if preco_rows:
        PrecificacaoProdutoAcabadoPrecoVenda.objects.bulk_update(
            preco_rows,
            ["comissao_valor", "contrato_valor", "subtotal", "cmv_estimado"],
            batch_size=100,
        )

    despesas_por_chave = {item.chave: item for item in despesas_rows}
    for linha in despesas_rows:
        conf = conf_por_chave.get(linha.chave) or {}
        pv_item = preco_por_chave.get(linha.chave)
        pv_bruto = _precificacao_decimal(pv_item.pv_bruto if pv_item else 0)
        prazo_dias = _precificacao_decimal(linha.prazo_dias)
        financeiro_valor = (_precificacao_decimal(linha.financeiro_taxa) / Decimal("30")) * (prazo_dias + Decimal("10")) * pv_bruto
        inadimplencia_valor = _precificacao_decimal(linha.inadimplencia_taxa) * pv_bruto
        administracao_valor = _precificacao_decimal(linha.administracao_taxa) * pv_bruto
        producao_valor = _precificacao_decimal(linha.producao_valor) if linha.producao_ativo else Decimal("0")

        if linha.cif_manual_ativo:
            log_frete_rota = _precificacao_decimal(linha.cif_manual_valor)
        else:
            log_frete_rota = _precificacao_decimal(simulacao.frete_venda)

        if linha.cif_ativo:
            peso_base = _precificacao_decimal(conf.get("peso_base", 0))
            log_frete_rota_valor = (log_frete_rota / Decimal("1000")) * peso_base
        else:
            log_frete_rota_valor = Decimal("0")

        if linha.log_op_logistica_ativo:
            peso_base = _precificacao_decimal(conf.get("peso_base", 0))
            log_op_logistica_valor = (Decimal("25") / Decimal("1000")) * peso_base
        else:
            log_op_logistica_valor = Decimal("0")

        subtotal = (
            financeiro_valor
            + inadimplencia_valor
            + administracao_valor
            + producao_valor
            + log_frete_rota_valor
            + log_op_logistica_valor
        )
        linha.financeiro_valor = _precificacao_quantize(financeiro_valor)
        linha.inadimplencia_valor = _precificacao_quantize(inadimplencia_valor)
        linha.administracao_valor = _precificacao_quantize(administracao_valor)
        linha.log_frete_rota = _precificacao_quantize(log_frete_rota)
        linha.log_frete_rota_valor = _precificacao_quantize(log_frete_rota_valor)
        linha.log_op_logistica_valor = _precificacao_quantize(log_op_logistica_valor)
        linha.subtotal = _precificacao_quantize(subtotal)

    if despesas_rows:
        PrecificacaoProdutoAcabadoDespesa.objects.bulk_update(
            despesas_rows,
            [
                "financeiro_valor",
                "inadimplencia_valor",
                "administracao_valor",
                "log_frete_rota",
                "log_frete_rota_valor",
                "log_op_logistica_valor",
                "subtotal",
            ],
            batch_size=100,
        )

    impostos_por_chave = {item.chave: item for item in impostos_rows}
    for linha in impostos_rows:
        pv_item = preco_por_chave.get(linha.chave)
        pv_bruto = _precificacao_decimal(pv_item.pv_bruto if pv_item else 0)
        imposto_valor = _precificacao_decimal(linha.imposto_aliquota) * pv_bruto
        imposto_interno_valor = _precificacao_decimal(linha.imposto_interno_aliquota) * pv_bruto
        subtotal_interno = imposto_interno_valor if linha.interno_ativo else imposto_valor

        pro_goias_valor_a = _precificacao_decimal(linha.pro_goias_aliquota_a) * pv_bruto
        pro_goias_valor_b = _precificacao_decimal(linha.pro_goias_aliquota_b) * pv_bruto
        subtotal_pro_goias = pro_goias_valor_a if linha.interno_ativo else pro_goias_valor_b
        total = subtotal_pro_goias if linha.pro_goias_ativo else subtotal_interno

        linha.imposto_valor = _precificacao_quantize(imposto_valor)
        linha.imposto_interno_valor = _precificacao_quantize(imposto_interno_valor)
        linha.subtotal_interno = _precificacao_quantize(subtotal_interno)
        linha.pro_goias_valor_a = _precificacao_quantize(pro_goias_valor_a)
        linha.pro_goias_valor_b = _precificacao_quantize(pro_goias_valor_b)
        linha.subtotal_pro_goias = _precificacao_quantize(subtotal_pro_goias)
        linha.total = _precificacao_quantize(total)

    if impostos_rows:
        PrecificacaoProdutoAcabadoImposto.objects.bulk_update(
            impostos_rows,
            [
                "imposto_valor",
                "imposto_interno_valor",
                "subtotal_interno",
                "pro_goias_valor_a",
                "pro_goias_valor_b",
                "subtotal_pro_goias",
                "total",
            ],
            batch_size=100,
        )

    for linha in preco_rows:
        cmv_item = cmv_por_chave.get(linha.chave)
        despesa_item = despesas_por_chave.get(linha.chave)
        imposto_item = impostos_por_chave.get(linha.chave)

        subtotal = _precificacao_decimal(linha.subtotal)
        cmv = _precificacao_decimal(cmv_item.cmv if cmv_item else 0)
        cmv_ex_works = _precificacao_decimal(cmv_item.cmv_ex_works if cmv_item else 0)
        despesa = _precificacao_decimal(despesa_item.subtotal if despesa_item else 0)
        imposto_total = _precificacao_decimal(imposto_item.total if imposto_item else 0)
        usa_cmv_padrao = bool(imposto_item.pro_goias_ativo) if imposto_item else True
        base_cmv = cmv if usa_cmv_padrao else cmv_ex_works

        lucro_valor = subtotal - base_cmv - despesa - imposto_total
        pv_bruto = _precificacao_decimal(linha.pv_bruto)
        lucro_percentual = (lucro_valor / pv_bruto) if pv_bruto > 0 else Decimal("0")
        situacao, situacao_cor = _precificacao_situacao_por_percentual(lucro_percentual)

        linha.lucro_valor = _precificacao_quantize(lucro_valor)
        linha.lucro_percentual = _precificacao_quantize(lucro_percentual)
        linha.situacao = situacao
        linha.situacao_cor = situacao_cor

    if preco_rows:
        PrecificacaoProdutoAcabadoPrecoVenda.objects.bulk_update(
            preco_rows,
            ["lucro_valor", "lucro_percentual", "situacao", "situacao_cor"],
            batch_size=100,
        )

    # Pr.Total segue o encadeamento do legado (base 6x5 -> converte para 50kg):
    # d52 = pv_bruto_6x5 - (margem_requerida_compra * pv_bruto_6x5)
    # d53 = impostos_total_6x5 + comissao_6x5 + contrato_6x5 + despesas_6x5
    # d55 = emb_primaria_valor_6x5 + emb_secundaria_valor_6x5
    # d56 = d52 - d53 - d55
    # d57 = d56 / acucar_qtd_6x5
    # d58 = d57 * 50
    item_6x5_preco = preco_por_chave.get("6x5")
    item_6x5_cmv = cmv_por_chave.get("6x5")
    item_6x5_despesa = despesas_por_chave.get("6x5")
    item_6x5_imposto = impostos_por_chave.get("6x5")

    pv_bruto_6x5 = _precificacao_decimal(item_6x5_preco.pv_bruto if item_6x5_preco else 0)
    margem_requerida_compra = _precificacao_decimal(simulacao.margem_requerida_compra)
    d52 = pv_bruto_6x5 - (margem_requerida_compra * pv_bruto_6x5)

    d53 = (
        _precificacao_decimal(item_6x5_imposto.total if item_6x5_imposto else 0)
        + _precificacao_decimal(item_6x5_preco.comissao_valor if item_6x5_preco else 0)
        + _precificacao_decimal(item_6x5_preco.contrato_valor if item_6x5_preco else 0)
        + _precificacao_decimal(item_6x5_despesa.financeiro_valor if item_6x5_despesa else 0)
        + _precificacao_decimal(item_6x5_despesa.inadimplencia_valor if item_6x5_despesa else 0)
        + _precificacao_decimal(item_6x5_despesa.administracao_valor if item_6x5_despesa else 0)
        + _precificacao_decimal(item_6x5_despesa.producao_valor if item_6x5_despesa else 0)
        + _precificacao_decimal(item_6x5_despesa.log_frete_rota_valor if item_6x5_despesa else 0)
        + _precificacao_decimal(item_6x5_despesa.log_op_logistica_valor if item_6x5_despesa else 0)
    )

    d55 = (
        _precificacao_decimal(item_6x5_cmv.emb_primaria_valor if item_6x5_cmv else 0)
        + _precificacao_decimal(item_6x5_cmv.emb_secundaria_valor if item_6x5_cmv else 0)
    )
    d56 = d52 - d53 - d55

    acucar_qtd_6x5 = _precificacao_decimal(item_6x5_cmv.acucar_qtd if item_6x5_cmv else 0)
    d57 = (d56 / acucar_qtd_6x5) if acucar_qtd_6x5 > 0 else Decimal("0")

    simulacao.preco_total = _precificacao_quantize(d57 * Decimal("50"), casas=4)
    simulacao.mp = _precificacao_quantize(
        _precificacao_decimal(simulacao.preco_total) - _precificacao_decimal(simulacao.frete_compra),
        casas=4,
    )
    simulacao.full_clean()
    simulacao.save(update_fields=["mp", "preco_total"])


def atualizar_linha_precificacao(cenario, tabela, registro_id, post_data):
    tabela_norm = str(tabela or "").strip().lower()
    try:
        registro_id_int = int(registro_id)
    except (TypeError, ValueError):
        return "Registro invalido."

    try:
        if tabela_norm == "calculadora":
            item = PrecificacaoCalculadoraPrecoMedio.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."
            item.atualizar_linha(
                volume=_parse_decimal_ou_zero(post_data.get("volume")),
                preco=_parse_decimal_ou_zero(post_data.get("preco")),
                prazo=_parse_decimal_ou_zero(post_data.get("prazo")),
                frete=_parse_decimal_ou_zero(post_data.get("frete")),
            )
        elif tabela_norm == "simulacao":
            item = PrecificacaoSimulacaoCompraVenda.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."
            item.atualizar_item(
                margem_requerida_compra=_parse_decimal_ou_zero(post_data.get("margem_requerida_compra")),
                margem_requerida_venda=_parse_decimal_ou_zero(post_data.get("margem_requerida_venda")),
                frete_compra=_parse_decimal_ou_zero(post_data.get("frete_compra")),
                frete_venda=_parse_decimal_ou_zero(post_data.get("frete_venda")),
            )
        elif tabela_norm == "materia_prima":
            item = PrecificacaoMateriaPrima.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."

            campos_protegidos = PRECIFICACAO_MATERIA_PRIMA_CAMPOS_PROTEGIDOS.get(item.chave, set())
            kwargs_update = {
                "ativo": _precificacao_bool(post_data.get("ativo")),
                "credito": _parse_decimal_ou_zero(post_data.get("credito")),
            }
            if "valor" not in campos_protegidos:
                kwargs_update["valor"] = _parse_decimal_ou_zero(post_data.get("valor"))
            if "frete_mp" not in campos_protegidos:
                kwargs_update["frete_mp"] = _parse_decimal_ou_zero(post_data.get("frete_mp"))

            item.atualizar_linha(**kwargs_update)
        elif tabela_norm == "produto_cmv":
            item = PrecificacaoProdutoAcabadoCMV.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."
            item.atualizar_linha(
                acucar_quebra=_parse_decimal_ou_zero(post_data.get("acucar_quebra")),
                emb_primaria_quebra=_parse_decimal_ou_zero(post_data.get("emb_primaria_quebra")),
                emb_secundaria_quebra=_parse_decimal_ou_zero(post_data.get("emb_secundaria_quebra")),
            )
        elif tabela_norm == "produto_despesas":
            if _precificacao_bool(post_data.get("aplicar_global_cif")) or _precificacao_bool(post_data.get("aplicar_global_despesas")):
                cif_ativo = _precificacao_bool(post_data.get("cif_ativo"))
                cif_manual_ativo = _precificacao_bool(post_data.get("cif_manual_ativo"))
                cif_rota = (post_data.get("cif_rota") or "").strip()
                cif_manual_valor = _parse_decimal_ou_zero(post_data.get("cif_manual_valor"))
                prazo_dias = _parse_decimal_ou_zero(post_data.get("prazo_dias"))

                itens = list(PrecificacaoProdutoAcabadoDespesa.objects.filter(cenario=cenario).order_by("ordem", "id"))
                for item in itens:
                    item.prazo_dias = prazo_dias
                    item.cif_ativo = cif_ativo
                    item.cif_manual_ativo = cif_manual_ativo
                    item.cif_rota = cif_rota
                    item.cif_manual_valor = cif_manual_valor
                if itens:
                    PrecificacaoProdutoAcabadoDespesa.objects.bulk_update(
                        itens,
                        ["prazo_dias", "cif_ativo", "cif_manual_ativo", "cif_rota", "cif_manual_valor"],
                        batch_size=100,
                    )
            else:
                item = PrecificacaoProdutoAcabadoDespesa.objects.filter(id=registro_id_int, cenario=cenario).first()
                if not item:
                    return "Registro nao encontrado."
                item.atualizar_linha(
                    financeiro_taxa=_parse_decimal_ou_zero(post_data.get("financeiro_taxa")),
                    inadimplencia_taxa=_parse_decimal_ou_zero(post_data.get("inadimplencia_taxa")),
                    administracao_taxa=_parse_decimal_ou_zero(post_data.get("administracao_taxa")),
                    producao_ativo=_precificacao_bool(post_data.get("producao_ativo")),
                    producao_valor=_parse_decimal_ou_zero(post_data.get("producao_valor")),
                    log_op_logistica_ativo=_precificacao_bool(post_data.get("log_op_logistica_ativo")),
                )
        elif tabela_norm == "produto_impostos":
            item = PrecificacaoProdutoAcabadoImposto.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."
            item.atualizar_linha(
                interno_ativo=_precificacao_bool(post_data.get("interno_ativo")),
                imposto_aliquota=_parse_decimal_ou_zero(post_data.get("imposto_aliquota")),
                imposto_interno_aliquota=_parse_decimal_ou_zero(post_data.get("imposto_interno_aliquota")),
                pro_goias_ativo=_precificacao_bool(post_data.get("pro_goias_ativo")),
                pro_goias_aliquota_a=_parse_decimal_ou_zero(post_data.get("pro_goias_aliquota_a")),
                pro_goias_aliquota_b=_parse_decimal_ou_zero(post_data.get("pro_goias_aliquota_b")),
            )
        elif tabela_norm == "produto_preco_venda":
            item = PrecificacaoProdutoAcabadoPrecoVenda.objects.filter(id=registro_id_int, cenario=cenario).first()
            if not item:
                return "Registro nao encontrado."
            item.atualizar_linha(
                pv_bruto=_parse_decimal_ou_zero(post_data.get("pv_bruto")),
                interno_ativo=_precificacao_bool(post_data.get("interno_ativo")),
                comissao_aliquota=_parse_decimal_ou_zero(post_data.get("comissao_aliquota")),
                contrato_aliquota=_parse_decimal_ou_zero(post_data.get("contrato_aliquota")),
            )
        else:
            return "Tabela invalida."

        recalcular_precificacao_cenario(cenario)
    except ValidationError as exc:
        if hasattr(exc, "message_dict") and exc.message_dict:
            for mensagens in exc.message_dict.values():
                if mensagens:
                    return str(mensagens[0])
        if getattr(exc, "messages", None):
            return str(exc.messages[0])
        return "Dados invalidos para salvar."

    return ""


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


def _calcular_gerente_mp_e_gerente_luciano(compromisso, gerente_pa_e_outros):
    compromisso_decimal = _parse_decimal_ou_zero(str(compromisso))
    gerente_pa_decimal = _parse_decimal_ou_zero(str(gerente_pa_e_outros))
    return compromisso_decimal - gerente_pa_decimal


def criar_parametro_negocios(empresa, post_data):
    direcao = (post_data.get("direcao") or "").strip()
    meta = _parse_decimal_ou_zero(post_data.get("meta"))
    compromisso = _parse_decimal_ou_zero(post_data.get("compromisso"))
    gerente_pa_e_outros = _parse_decimal_ou_zero(post_data.get("gerente_pa_e_outros"))
    gerente_mp_e_gerente_luciano = _calcular_gerente_mp_e_gerente_luciano(compromisso, gerente_pa_e_outros)
    if not direcao:
        return "Direcao e obrigatoria."

    ParametroNegocios.objects.create(
        empresa=empresa,
        direcao=direcao,
        meta=meta,
        compromisso=compromisso,
        gerente_pa_e_outros=gerente_pa_e_outros,
        gerente_mp_e_gerente_luciano=gerente_mp_e_gerente_luciano,
    )
    return ""


def atualizar_parametro_negocios(item, empresa, post_data):
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa."

    direcao = (post_data.get("direcao") or "").strip()
    meta = _parse_decimal_ou_zero(post_data.get("meta"))
    compromisso = _parse_decimal_ou_zero(post_data.get("compromisso"))
    gerente_pa_e_outros = _parse_decimal_ou_zero(post_data.get("gerente_pa_e_outros"))
    gerente_mp_e_gerente_luciano = _calcular_gerente_mp_e_gerente_luciano(compromisso, gerente_pa_e_outros)
    if not direcao:
        return "Direcao e obrigatoria."

    item.direcao = direcao
    item.meta = meta
    item.compromisso = compromisso
    item.gerente_pa_e_outros = gerente_pa_e_outros
    item.gerente_mp_e_gerente_luciano = gerente_mp_e_gerente_luciano
    item.save(
        update_fields=[
            "direcao",
            "meta",
            "compromisso",
            "gerente_pa_e_outros",
            "gerente_mp_e_gerente_luciano",
        ]
    )
    return ""


def excluir_parametro_negocios(item, empresa):
    if item.empresa_id != empresa.id:
        return "Parametro invalido para esta empresa."
    item.delete()
    return ""


def _dados_carteira_from_post(post_data, empresa):
    regiao = Regiao.objects.filter(id=post_data.get("regiao_id"), empresa=empresa).first()
    cidade = Cidade.objects.filter(id=post_data.get("cidade_id"), empresa=empresa).first()
    parceiro = Parceiro.objects.filter(id=post_data.get("parceiro_id"), empresa=empresa).first()

    data_cadastro_raw = post_data.get("data_cadastro")
    data_cadastro = _parse_date_ou_none(data_cadastro_raw)
    descricao_perfil = _sincronizar_descricao_perfil(empresa, post_data.get("descricao_perfil"))

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
        "descricao_perfil": descricao_perfil,
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


def construir_payload_tabela_saldo_dfc(empresa, dfc_registros, hoje=None, dias_periodo=10):
    return _construir_payload_tabela_saldo_dfc(
        empresa=empresa,
        dfc_registros=dfc_registros,
        hoje=hoje,
        dias_periodo=dias_periodo,
    )


def salvar_dfc_saldo_manual_por_post(empresa, post_data):
    return _salvar_dfc_saldo_manual_por_post(empresa=empresa, post_data=post_data)


def _parse_decimal_ou_none(valor):
    texto = (valor or "").strip()
    if not texto:
        return None
    return _parse_decimal_ou_zero(texto)


def _dados_faturamento_from_post(post_data):
    data_faturamento_raw = (post_data.get("data_faturamento") or "").strip()
    valor_frete_raw = (post_data.get("valor_frete") or "").strip()
    empresa_id = post_data.get("empresa_id")
    empresa = Empresa.objects.filter(id=empresa_id).first() if empresa_id else None

    def _fk_id(campo):
        valor = str(post_data.get(campo) or "").strip()
        if not valor:
            return None
        try:
            valor_int = int(valor)
        except (TypeError, ValueError):
            return None
        return valor_int if valor_int > 0 else None

    parceiro = None
    operacao = None
    natureza = None
    centro_resultado = None
    produto = None
    descricao_perfil = (post_data.get("descricao_perfil") or "").strip()
    if empresa:
        parceiro_id = _fk_id("parceiro_id")
        operacao_id = _fk_id("operacao_id")
        natureza_id = _fk_id("natureza_id")
        centro_resultado_id = _fk_id("centro_resultado_id")
        produto_id = _fk_id("produto_id")

        parceiro = Parceiro.objects.filter(id=parceiro_id, empresa=empresa).first() if parceiro_id else None
        operacao = Operacao.objects.filter(id=operacao_id, empresa=empresa).first() if operacao_id else None
        natureza = Natureza.objects.filter(id=natureza_id, empresa=empresa).first() if natureza_id else None
        centro_resultado = CentroResultado.objects.filter(
            id=centro_resultado_id,
            empresa=empresa,
        ).first() if centro_resultado_id else None
        produto = Produto.objects.filter(id=produto_id, empresa=empresa).first() if produto_id else None
        descricao_perfil = _sincronizar_descricao_perfil(empresa, descricao_perfil)

    return {
        "data_faturamento_raw": data_faturamento_raw,
        "data_faturamento": _parse_date_ou_none(data_faturamento_raw),
        "nome_origem": (post_data.get("nome_origem") or "").strip(),
        "nome_empresa": (post_data.get("nome_empresa") or "").strip(),
        "parceiro": parceiro,
        "numero_nota": _parse_int64_ou_zero(post_data.get("numero_nota")),
        "valor_nota": _parse_decimal_ou_zero(post_data.get("valor_nota")),
        "participacao_venda_geral": _parse_decimal_ou_zero(post_data.get("participacao_venda_geral")),
        "participacao_venda_cliente": _parse_decimal_ou_zero(post_data.get("participacao_venda_cliente")),
        "valor_nota_unico": _parse_decimal_ou_zero(post_data.get("valor_nota_unico")),
        "peso_bruto_unico": _parse_decimal_ou_zero(post_data.get("peso_bruto_unico")),
        "quantidade_volumes": _parse_decimal_ou_zero(post_data.get("quantidade_volumes")),
        "quantidade_saida": _parse_decimal_ou_zero(post_data.get("quantidade_saida")),
        "status_nfe": (post_data.get("status_nfe") or "").strip(),
        "apelido_vendedor": (post_data.get("apelido_vendedor") or "").strip(),
        "operacao": operacao,
        "natureza": natureza,
        "centro_resultado": centro_resultado,
        "tipo_movimento": (post_data.get("tipo_movimento") or "").strip(),
        "prazo_medio": _parse_decimal_ou_zero(post_data.get("prazo_medio")),
        "media_unica": _parse_decimal_ou_none(post_data.get("media_unica")),
        "tipo_venda": (post_data.get("tipo_venda") or "").strip(),
        "produto": produto,
        "gerente": (post_data.get("gerente") or "").strip(),
        "descricao_perfil": descricao_perfil,
        "valor_frete_raw": valor_frete_raw,
        "valor_frete": _parse_decimal_ou_none(valor_frete_raw),
    }


def criar_faturamento_por_post(empresa, post_data):
    post_data = post_data.copy()
    post_data["empresa_id"] = empresa.id
    dados = _dados_faturamento_from_post(post_data)
    if not dados["data_faturamento_raw"]:
        return "Data do faturamento e obrigatoria."
    if not dados["data_faturamento"]:
        return "Data do faturamento invalida."
    if dados["numero_nota"] <= 0:
        return "Numero da nota e obrigatorio."

    dados.pop("data_faturamento_raw", None)
    dados.pop("valor_frete_raw", None)
    Faturamento.criar_faturamento(empresa=empresa, **dados)
    return ""


def atualizar_faturamento_por_post(faturamento_item, post_data):
    post_data = post_data.copy()
    post_data["empresa_id"] = faturamento_item.empresa_id
    dados = _dados_faturamento_from_post(post_data)
    if not dados["data_faturamento_raw"]:
        return "Data do faturamento e obrigatoria."
    if not dados["data_faturamento"]:
        return "Data do faturamento invalida."
    if dados["numero_nota"] <= 0:
        return "Numero da nota e obrigatorio."

    dados.pop("data_faturamento_raw", None)
    dados.pop("valor_frete_raw", None)
    faturamento_item.atualizar_faturamento(**dados)
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


def preparar_diretorios_carteira(empresa):
    return _preparar_diretorios_importacao(area="comercial", modulo="carteira", empresa=empresa)


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
            empresa=empresa,
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


def preparar_diretorios_vendas(empresa):
    return _preparar_diretorios_importacao(area="comercial", modulo="vendas", empresa=empresa)


def preparar_diretorios_pedidos_pendentes(empresa):
    return _preparar_diretorios_importacao(area="comercial", modulo="pedidos_pendentes", empresa=empresa)


def preparar_diretorios_controle_margem(empresa):
    return _preparar_diretorios_importacao(area="comercial", modulo="controle_de_margem", empresa=empresa)


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
            empresa=empresa,
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
            empresa=empresa,
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
            empresa=empresa,
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


def preparar_diretorios_cargas(empresa):
    return _preparar_diretorios_importacao(area="operacional", modulo="cargas_em_aberto", empresa=empresa)


def preparar_diretorios_producao(empresa):
    return _preparar_diretorios_importacao(area="operacional", modulo="producao", empresa=empresa)


def preparar_diretorios_fretes(empresa):
    return _preparar_diretorios_importacao(area="operacional", modulo="tabela_de_fretes", empresa=empresa)


def preparar_diretorios_estoque(empresa):
    return _preparar_diretorios_importacao(area="operacional", modulo="estoque_pcp", empresa=empresa)


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
            empresa=empresa,
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
            empresa=empresa,
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
            empresa=empresa,
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
            empresa=empresa,
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

