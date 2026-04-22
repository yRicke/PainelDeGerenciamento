import json
import re
from datetime import datetime

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from ..utils.importacao_metadados import (
    caminho_metadados_importacao,
    nome_metadados_importacao_por_empresa_id,
)
from ..utils.modulos_permissoes import MODULOS_POR_AREA

TIPO_IMPORTACAO_POR_MODULO = {
    "carteira": "Arquivo .xlsx (selecao unica).",
    "pedidos_pendentes": "Arquivo .xlsx (selecao unica).",
    "controle_de_margem": "Arquivo .xls ou .xlsx (selecao unica).",
    "vendas_por_categoria": "Pasta com arquivos .xls no padrao dd.mm.aaaa.xls.",
    "contas_a_receber": "Pasta com arquivos .xls.",
    "dfc": "Arquivo .xls (selecao unica).",
    "faturamento": "Pasta com subpastas '1 - Faturamento diario' e '2 - Venda por Produto (NF)' contendo arquivos .xlsx.",
    "adiantamentos": "Pasta ADIANTAMENTOS com subpastas de ano e mes contendo arquivos .xls.",
    "comite_diario": "Arquivo .xls (selecao unica).",
    "orcamento": "Pasta com arquivos .xls.",
    "cargas_em_aberto": "Arquivo .xls (selecao unica).",
    "producao": "Pasta com arquivos .xls.",
    "tabela_de_fretes": "Arquivo .xls (selecao unica).",
    "estoque_pcp": "Pasta ESTOQUE com subpastas contendo arquivos .xls.",
}


def _obter_modulo(area, nome):
    return next(m for m in MODULOS_POR_AREA[area] if m["nome"] == nome)


def _resumir_arquivos_existentes(arquivos, limite=8):
    arquivos_ordenados = sorted([str(arquivo) for arquivo in arquivos if arquivo])
    if not arquivos_ordenados:
        return "", False
    if len(arquivos_ordenados) > limite:
        texto = (
            ", ".join(arquivos_ordenados[:limite])
            + f" ... (+{len(arquivos_ordenados) - limite})"
        )
        return texto, True
    return ", ".join(arquivos_ordenados), True


def _normalizar_empresa_id(empresa_id):
    try:
        empresa_id_int = int(empresa_id)
    except (TypeError, ValueError):
        return None
    if empresa_id_int <= 0:
        return None
    return empresa_id_int


def _nome_metadados_importacao_por_empresa(empresa_id):
    empresa_id_int = _normalizar_empresa_id(empresa_id)
    if not empresa_id_int:
        return ""
    return nome_metadados_importacao_por_empresa_id(empresa_id_int)


def _caminho_metadados_importacao(diretorio_importacao, empresa_id):
    empresa_id_int = _normalizar_empresa_id(empresa_id)
    if not empresa_id_int:
        return None
    return caminho_metadados_importacao(diretorio_importacao, empresa_id_int)


def _ler_metadados_importacao(diretorio_importacao, modulo, empresa_id):
    caminho_metadados = _caminho_metadados_importacao(diretorio_importacao, empresa_id)
    if not caminho_metadados:
        return {}
    if not caminho_metadados.exists():
        return {}
    try:
        payload = json.loads(caminho_metadados.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    empresa_payload = _normalizar_empresa_id(payload.get("empresa_id"))
    empresa_esperada = _normalizar_empresa_id(empresa_id)
    if not empresa_payload or empresa_payload != empresa_esperada:
        return {}
    if str(payload.get("modulo") or "").strip() != str(modulo or "").strip():
        return {}
    return payload


def _datas_no_nome_arquivo(nome_arquivo):
    texto = str(nome_arquivo or "").strip()
    if not texto:
        return []
    datas = []
    for correspondencia in re.finditer(r"(\d{2})[.\-_/](\d{2})[.\-_/](\d{4})", texto):
        dia, mes, ano = correspondencia.groups()
        try:
            datas.append(datetime(int(ano), int(mes), int(dia)).date())
        except ValueError:
            continue
    return datas


def _data_hora_referencia_arquivo_ou_none(arquivo):
    datas_no_nome = _datas_no_nome_arquivo(getattr(arquivo, "name", ""))
    if datas_no_nome:
        return datetime.combine(max(datas_no_nome), datetime.min.time())
    try:
        return datetime.fromtimestamp(arquivo.stat().st_mtime)
    except (OSError, OverflowError, ValueError):
        return None


def _listar_arquivos_importacao(diretorio_importacao, diretorio_subscritos, extensoes=None):
    extensoes_norm = {
        str(extensao or "").strip().lower()
        for extensao in (extensoes or [])
        if str(extensao or "").strip()
    }
    return sorted(
        [
            arquivo
            for arquivo in diretorio_importacao.rglob("*")
            if arquivo.is_file()
            and diretorio_subscritos not in arquivo.parents
            and (
                not extensoes_norm
                or arquivo.suffix.lower() in extensoes_norm
            )
        ]
    )


def _data_metadados_importacao_ou_none(metadados):
    valor_iso = str(metadados.get("registrado_em_iso") or "").strip()
    if not valor_iso:
        return None
    try:
        data_hora = datetime.fromisoformat(valor_iso)
    except ValueError:
        return None
    if timezone.is_aware(data_hora):
        return timezone.localtime(data_hora)
    return data_hora


def _montar_resumo_importacao(diretorio_importacao, diretorio_subscritos, modulo, empresa_id, extensoes=None):
    arquivos_atuais = _listar_arquivos_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        extensoes=extensoes,
    )
    if not arquivos_atuais:
        return {
            "tem_arquivos": False,
            "data_referencia": "",
            "usuario": "",
            "quantidade_arquivos": 0,
        }

    metadados = _ler_metadados_importacao(
        diretorio_importacao=diretorio_importacao,
        modulo=modulo,
        empresa_id=empresa_id,
    )
    data_hora_referencia_metadado = _data_metadados_importacao_ou_none(metadados)

    datas_horas_arquivos = []
    for arquivo in arquivos_atuais:
        data_hora_arquivo = _data_hora_referencia_arquivo_ou_none(arquivo)
        if data_hora_arquivo:
            datas_horas_arquivos.append(data_hora_arquivo)
    data_hora_referencia_arquivos = max(datas_horas_arquivos) if datas_horas_arquivos else None
    data_hora_referencia = data_hora_referencia_metadado or data_hora_referencia_arquivos
    data_referencia_texto = data_hora_referencia.strftime("%d/%m/%Y %H:%M") if data_hora_referencia else "-"

    quantidade_arquivos_metadado = 0
    try:
        quantidade_arquivos_metadado = int(metadados.get("quantidade_arquivos") or 0)
    except (TypeError, ValueError):
        quantidade_arquivos_metadado = 0

    quantidade_arquivos = (
        quantidade_arquivos_metadado
        if quantidade_arquivos_metadado > 0
        else len(arquivos_atuais)
    )

    usuario_importacao = str(metadados.get("usuario") or "").strip()
    if not usuario_importacao:
        usuario_importacao = "Nao identificado"

    return {
        "tem_arquivos": True,
        "data_referencia": data_referencia_texto,
        "usuario": usuario_importacao,
        "quantidade_arquivos": quantidade_arquivos,
    }


def _empresa_bloqueia_cadastro_edicao_importacao(empresa):
    return bool(getattr(empresa, "possui_sistema", False))


def _coletar_param_json_lista(request, chaves):
    for chave in chaves:
        bruto = request.GET.get(chave)
        if bruto is None:
            continue
        texto = str(bruto).strip()
        if not texto:
            continue
        try:
            valor = json.loads(texto)
        except (TypeError, ValueError):
            continue
        if isinstance(valor, list):
            return [item for item in valor if isinstance(item, dict)]
    return []


def _bloquear_criar_em_modulo_com_importacao_se_necessario(request, empresa, acao, acoes_criar):
    if (
        request.method == "POST"
        and acao in acoes_criar
        and _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    ):
        messages.error(
            request,
            "Cadastro manual desabilitado para esta empresa neste modulo.",
        )
        return True
    return False


def _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, redirect_name):
    if _empresa_bloqueia_cadastro_edicao_importacao(empresa):
        messages.error(
            request,
            "Edicao manual desabilitada para esta empresa neste modulo.",
        )
        return redirect(redirect_name, empresa_id=empresa.id)
    return None
