import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Case, DecimalField, F, FloatField, Q, Sum, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Cast, Coalesce

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
    Estoque,
    Faturamento,
    FluxoDeCaixaDFC,
    Frete,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
    Parceiro,
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
from .utils.administrativo_transformers import montar_contexto_tofu_lista
from .utils.comercial_transformers import montar_contexto_carteira, montar_contexto_vendas
from .utils.modulos_permissoes import (
    MODULOS_POR_AREA,
    _modulos_com_acesso,
    _obter_empresa_e_validar_permissao_modulo,
    _obter_empresa_e_validar_permissao_tofu,
    _obter_permissoes_do_form,
    _obter_permissoes_por_modulo,
    _render_modulo_com_permissao,
)
from .services import (
    criar_atividade_por_post,
    atualizar_atividade_por_post,
    semana_iso_input_atividade,
    preparar_diretorios_carteira,
    preparar_diretorios_vendas,
    preparar_diretorios_pedidos_pendentes,
    preparar_diretorios_controle_margem,
    preparar_diretorios_dfc,
    preparar_diretorios_faturamento,
    preparar_diretorios_adiantamentos,
    preparar_diretorios_contas_a_receber,
    preparar_diretorios_orcamento,
    preparar_diretorios_cargas,
    preparar_diretorios_estoque,
    preparar_diretorios_fretes,
    preparar_diretorios_producao,
    importar_upload_carteira,
    importar_upload_vendas,
    importar_upload_pedidos_pendentes,
    importar_upload_controle_margem,
    importar_upload_dfc,
    importar_upload_faturamento,
    importar_upload_adiantamentos,
    importar_upload_contas_a_receber,
    importar_upload_orcamento,
    importar_upload_cargas,
    importar_upload_estoque,
    importar_upload_fretes,
    importar_upload_producao,
    usuarios_com_permissoes_ids,
    criar_empresa_por_nome,
    atualizar_empresa_por_nome,
    excluir_empresa_por_id,
    criar_usuario_por_post,
    atualizar_usuario_por_post,
    excluir_usuario_por_id,
    criar_colaborador_por_nome,
    criar_motorista_por_dados,
    atualizar_colaborador_por_nome,
    criar_parceiro_por_dados,
    atualizar_parceiro_por_dados,
    criar_produto_por_dados,
    criar_unidade_federativa_por_dados,
    criar_transportadora_por_dados,
    criar_agenda_por_post,
    atualizar_produto_por_dados,
    atualizar_unidade_federativa_por_dados,
    atualizar_motorista_por_dados,
    atualizar_transportadora_por_dados,
    atualizar_agenda_por_post,
    criar_pedido_pendente_por_post,
    atualizar_pedido_pendente_por_post,
    criar_controle_margem_por_post,
    atualizar_controle_margem_por_post,
    criar_parametro_margem_vendas,
    atualizar_parametro_margem_vendas,
    excluir_parametro_margem_vendas,
    criar_parametro_margem_logistica,
    atualizar_parametro_margem_logistica,
    excluir_parametro_margem_logistica,
    salvar_parametro_margem_administracao,
    criar_parametro_margem_financeiro,
    atualizar_parametro_margem_financeiro,
    excluir_parametro_margem_financeiro,
    criar_titulo_por_dados,
    atualizar_titulo_por_dados,
    criar_natureza_por_dados,
    atualizar_natureza_por_dados,
    criar_operacao_por_dados,
    atualizar_operacao_por_dados,
    criar_centro_resultado_por_dados,
    atualizar_centro_resultado_por_dados,
    criar_dfc_por_post,
    atualizar_dfc_por_post,
    criar_faturamento_por_post,
    atualizar_faturamento_por_post,
    criar_adiantamento_por_post,
    atualizar_adiantamento_por_post,
    criar_contas_a_receber_por_post,
    atualizar_contas_a_receber_por_post,
    criar_orcamento_por_post,
    criar_orcamento_planejado_por_post,
    atualizar_orcamento_por_post,
    atualizar_orcamento_planejado_por_post,
    criar_carteira_por_post,
    atualizar_carteira_por_post,
    criar_venda_por_post,
    atualizar_venda_por_post,
    criar_carga_por_post,
    criar_estoque_por_post,
    criar_frete_por_post,
    atualizar_carga_por_post,
    atualizar_estoque_por_post,
    atualizar_frete_por_post,
    criar_producao_por_post,
    atualizar_producao_por_post,
    criar_cidade_por_dados,
    criar_rota_por_dados,
    atualizar_cidade_por_dados,
    criar_projeto_por_dados,
    criar_regiao_por_dados,
    atualizar_projeto_por_dados,
    atualizar_regiao_por_dados,
    atualizar_rota_por_dados,
)
from .tabulator import (
    build_cidades_tabulator,
    build_colaboradores_tabulator,
    build_projetos_tabulator,
    build_regioes_tabulator,
    build_rotas_tabulator,
    build_unidades_federativas_tabulator,
    build_parceiros_tabulator,
    build_motoristas_tabulator,
    build_transportadoras_tabulator,
    build_agenda_tabulator,
    build_produtos_tabulator,
    build_titulos_tabulator,
    build_naturezas_tabulator,
    build_operacoes_tabulator,
    build_centros_resultado_tabulator,
    build_parametros_margem_vendas_tabulator,
    build_parametros_margem_logistica_tabulator,
    build_parametros_margem_financeiro_tabulator,
    build_dfc_tabulator,
    build_faturamento_tabulator,
    build_adiantamentos_tabulator,
    build_contas_a_receber_tabulator,
    build_orcamento_tabulator,
    build_orcamento_x_realizado_tabulator,
    build_orcamentos_planejados_tabulator,
    build_pedidos_pendentes_tabulator,
    build_controle_margem_tabulator,
    build_cargas_tabulator,
    build_estoque_tabulator,
    build_fretes_tabulator,
    build_producao_tabulator,
)

IMPORTACAO_METADATA_FILE_PREFIX = "_ultimo_import_empresa_"
TIPO_IMPORTACAO_POR_MODULO = {
    "carteira": "Arquivo .xlsx (selecao unica).",
    "pedidos_pendentes": "Arquivo .xlsx (selecao unica).",
    "controle_de_margem": "Arquivo .xls ou .xlsx (selecao unica).",
    "vendas_por_categoria": "Pasta com arquivos .xls no padrao dd.mm.aaaa.xls.",
    "contas_a_receber": "Pasta com arquivos .xls.",
    "dfc": "Arquivo .xls (selecao unica).",
    "faturamento": "Pasta com subpastas '1 - Faturamento diario' e '2 - Venda por Produto (NF)' contendo arquivos .xlsx.",
    "adiantamentos": "Arquivo .xls (selecao unica).",
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
    return f"{IMPORTACAO_METADATA_FILE_PREFIX}{empresa_id_int}.json"


def _ler_metadados_importacao(diretorio_subscritos, modulo, empresa_id):
    nome_arquivo = _nome_metadados_importacao_por_empresa(empresa_id)
    if not nome_arquivo:
        return {}
    caminho_metadados = diretorio_subscritos / nome_arquivo
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


def _data_referencia_arquivo_ou_none(arquivo):
    datas_no_nome = _datas_no_nome_arquivo(getattr(arquivo, "name", ""))
    if datas_no_nome:
        return max(datas_no_nome)
    try:
        return datetime.fromtimestamp(arquivo.stat().st_mtime).date()
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
        return datetime.fromisoformat(valor_iso).date()
    except ValueError:
        return None


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
        diretorio_subscritos=diretorio_subscritos,
        modulo=modulo,
        empresa_id=empresa_id,
    )
    data_referencia_metadado = _data_metadados_importacao_ou_none(metadados)

    datas_arquivos = []
    for arquivo in arquivos_atuais:
        data_arquivo = _data_referencia_arquivo_ou_none(arquivo)
        if data_arquivo:
            datas_arquivos.append(data_arquivo)
    data_referencia_arquivos = max(datas_arquivos) if datas_arquivos else None
    data_referencia = data_referencia_metadado or data_referencia_arquivos
    data_referencia_texto = data_referencia.strftime("%d/%m/%Y") if data_referencia else "-"

    quantidade_arquivos = len(arquivos_atuais)
    if quantidade_arquivos > 1:
        data_referencia_texto = f"{data_referencia_texto} +{quantidade_arquivos - 1}"

    usuario_importacao = str(metadados.get("usuario") or "").strip()
    if not usuario_importacao:
        usuario_importacao = "Nao identificado"

    return {
        "tem_arquivos": True,
        "data_referencia": data_referencia_texto,
        "usuario": usuario_importacao,
        "quantidade_arquivos": quantidade_arquivos,
    }


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


def _empresa_bloqueia_cadastro_edicao_importacao(empresa):
    return bool(getattr(empresa, "possui_sistema", False))


def _valor_checkbox_possui_sistema(post_data):
    return str(post_data.get("possui_sistema", "")).strip().lower() in {"1", "true", "on", "sim", "yes"}


def _normalizar_lista_query(request, chave):
    valores = [str(v or "").strip() for v in request.GET.getlist(chave)]
    return [v for v in valores if v]


def _situacao_controle_margem_param_ou_none(valor):
    texto = (valor or "").strip().lower()
    if not texto:
        return ""
    mapa = {
        "amarelo": ControleMargem.SITUACAO_AMARELO,
        "roxo": ControleMargem.SITUACAO_ROXO,
        "verde": ControleMargem.SITUACAO_VERDE,
        "vermelho": ControleMargem.SITUACAO_VERMELHO,
    }
    return mapa.get(texto, "")


def _filtrar_controle_margem_por_situacao(qs, situacao):
    if not situacao:
        return qs
    if situacao == ControleMargem.SITUACAO_ROXO:
        return qs.filter(margem_bruta__lt=0.10)
    if situacao == ControleMargem.SITUACAO_VERMELHO:
        return qs.filter(margem_bruta__gte=0.10, margem_bruta__lt=0.12)
    if situacao == ControleMargem.SITUACAO_AMARELO:
        return qs.filter(margem_bruta__gte=0.12, margem_bruta__lt=0.14)
    if situacao == ControleMargem.SITUACAO_VERDE:
        return qs.filter(margem_bruta__gte=0.14)
    return qs.none()


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


def _parse_data_tabulator(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _fmt_date_br(valor):
    if not valor:
        return ""
    return valor.strftime("%d/%m/%Y")


def _parse_decimal_tabulator(valor):
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extrair_valores_filtro(valor_bruto):
    if isinstance(valor_bruto, (list, tuple, set)):
        return [str(v).strip() for v in valor_bruto if str(v).strip()]
    texto = str(valor_bruto or "").strip()
    if not texto:
        return []
    if "||" in texto:
        return [item.strip() for item in texto.split("||") if item.strip()]
    return [texto]


def _intervalo_para_faixa_dias(intervalo_texto):
    texto = str(intervalo_texto or "").strip().lower()
    if not texto:
        return None, None
    if texto.startswith("+"):
        limite = "".join(ch for ch in texto if ch.isdigit())
        if not limite:
            return None, None
        return int(limite), None
    match = re.search(r"(\d+)\s*-\s*(\d+)", texto)
    if not match:
        return None, None
    inicio, fim = int(match.group(1)), int(match.group(2))
    if inicio > fim:
        inicio, fim = fim, inicio
    return inicio, fim


def _q_intervalo_contas(hoje, valor_intervalo):
    inicio, fim = _intervalo_para_faixa_dias(valor_intervalo)
    if inicio is None:
        return Q()

    if fim is None:
        return (
            Q(data_vencimento__lte=hoje - timedelta(days=inicio))
            | Q(data_vencimento__gte=hoje + timedelta(days=inicio))
        )

    return (
        Q(
            data_vencimento__gte=hoje - timedelta(days=fim),
            data_vencimento__lte=hoje - timedelta(days=inicio),
        )
        | Q(
            data_vencimento__gte=hoje + timedelta(days=inicio),
            data_vencimento__lte=hoje + timedelta(days=fim),
        )
    )


def _filtrar_contas_a_receber_por_intervalo(qs, valor_intervalo):
    hoje = datetime.now().date()
    q_intervalo = _q_intervalo_contas(hoje, valor_intervalo)
    if not q_intervalo:
        return qs
    return qs.filter(q_intervalo)


def _datas_posicao_contas(qs):
    datas = list(
        qs.exclude(data_arquivo__isnull=True)
        .order_by("-data_arquivo")
        .values_list("data_arquivo", flat=True)
        .distinct()[:2]
    )
    ultima = datas[0] if len(datas) >= 1 else None
    penultima = datas[1] if len(datas) >= 2 else None
    return ultima, penultima


def _aplicar_filtros_contas_a_receber(qs, filtros):
    hoje = datetime.now().date()
    for filtro in filtros:
        campo = str(filtro.get("field") or "").strip()
        tipo = str(filtro.get("type") or "").strip().lower()
        valores = _extrair_valores_filtro(filtro.get("value"))
        if not campo or not valores:
            continue

        if campo == "status":
            q_status = Q()
            for valor in valores:
                valor_lower = valor.lower()
                if "vencido" in valor_lower:
                    q_status |= Q(data_vencimento__lt=hoje)
                elif "vencer" in valor_lower:
                    q_status |= Q(data_vencimento__gte=hoje)
            if q_status:
                qs = qs.filter(q_status)
            continue

        if campo == "intervalo":
            q_intervalos = Q()
            for valor in valores:
                q_intervalo = _q_intervalo_contas(hoje, valor)
                if q_intervalo:
                    q_intervalos |= q_intervalo
            if q_intervalos:
                qs = qs.filter(q_intervalos)
            continue

        if campo == "dias_diferenca":
            q_dias = Q()
            for valor in valores:
                if re.fullmatch(r"-?\d+", valor):
                    q_dias |= Q(data_vencimento=hoje - timedelta(days=int(valor)))
            if q_dias:
                qs = qs.filter(q_dias)
            continue

        if campo in {"data_negociacao", "data_vencimento", "data_arquivo"}:
            q_datas = Q()
            for valor in valores:
                data = _parse_data_tabulator(valor)
                if data:
                    q_datas |= Q(**{campo: data})
                elif valor.isdigit() and len(valor) == 4:
                    q_datas |= Q(**{f"{campo}__year": int(valor)})
            if q_datas:
                qs = qs.filter(q_datas)
            continue

        if campo == "data_arquivo_iso":
            q_data_arquivo = Q()
            for valor in valores:
                data_iso = _parse_data_tabulator(valor)
                if data_iso:
                    q_data_arquivo |= Q(data_arquivo=data_iso)
            if q_data_arquivo:
                qs = qs.filter(q_data_arquivo)
            continue

        if campo in {"valor_desdobramento", "valor_liquido"}:
            q_valores = Q()
            for valor in valores:
                valor_decimal = _parse_decimal_tabulator(valor)
                if valor_decimal is not None:
                    q_valores |= Q(**{campo: valor_decimal})
            if q_valores:
                qs = qs.filter(q_valores)
            continue

        if campo == "posicao_contagem":
            ultima_data, penultima_data = _datas_posicao_contas(qs)
            q_posicao = Q()
            for valor in valores:
                token = str(valor or "").strip().lower()
                if token == "ultima_posicao" and ultima_data:
                    q_posicao |= Q(data_arquivo=ultima_data)
                elif token == "penultima_posicao" and penultima_data:
                    q_posicao |= Q(data_arquivo=penultima_data)
                elif token == "anteriores_posicao":
                    q_anteriores = Q()
                    if ultima_data:
                        q_anteriores &= ~Q(data_arquivo=ultima_data)
                    if penultima_data:
                        q_anteriores &= ~Q(data_arquivo=penultima_data)
                    q_posicao |= q_anteriores
            if q_posicao:
                qs = qs.filter(q_posicao)
            continue

        filtros_texto = {
            "nome_fantasia_empresa": "nome_fantasia_empresa__icontains",
            "parceiro_nome": "parceiro__nome__icontains",
            "numero_nota": "numero_nota__icontains",
            "titulo_descricao": "titulo__descricao__icontains",
            "natureza_descricao": "natureza__descricao__icontains",
            "centro_resultado_descricao": "centro_resultado__descricao__icontains",
            "vendedor": "vendedor__icontains",
            "operacao_descricao": "operacao__descricao_receita_despesa__icontains",
        }
        lookup = filtros_texto.get(campo)
        if lookup:
            q_texto = Q()
            if tipo == "in":
                lookup_exato = lookup.replace("__icontains", "")
                for valor in valores:
                    q_texto |= Q(**{lookup_exato: valor})
            else:
                for valor in valores:
                    q_texto |= Q(**{lookup: valor})
            if q_texto:
                qs = qs.filter(q_texto)

    return qs


def _ordenar_contas_a_receber(qs, sorters):
    mapeamento = {
        "id": "id",
        "data_negociacao": "data_negociacao",
        "data_vencimento": "data_vencimento",
        "data_arquivo": "data_arquivo",
        "nome_fantasia_empresa": "nome_fantasia_empresa",
        "parceiro_nome": "parceiro__nome",
        "numero_nota": "numero_nota",
        "valor_desdobramento": "valor_desdobramento",
        "valor_liquido": "valor_liquido",
        "titulo_descricao": "titulo__descricao",
        "natureza_descricao": "natureza__descricao",
        "centro_resultado_descricao": "centro_resultado__descricao",
        "vendedor": "vendedor",
        "operacao_descricao": "operacao__descricao_receita_despesa",
        "status": "data_vencimento",
        "dias_diferenca": "data_vencimento",
        "intervalo": "data_vencimento",
    }

    ordenacoes = []
    for sorter in sorters:
        campo = str(sorter.get("field") or "").strip()
        direcao = str(sorter.get("dir") or "asc").strip().lower()
        order_field = mapeamento.get(campo)
        if not order_field:
            continue
        prefixo = "-" if direcao == "desc" else ""
        ordenacoes.append(f"{prefixo}{order_field}")

    if not ordenacoes:
        ordenacoes = ["-id"]
    elif not any(item.lstrip("-") == "id" for item in ordenacoes):
        ordenacoes.append("-id")

    return qs.order_by(*ordenacoes)


def _resumo_contas_a_receber(qs, total_registros):
    agregado = qs.aggregate(
        valor_faturado=Coalesce(
            Sum(
                Case(
                    When(
                        operacao__descricao_receita_despesa__icontains="despesa",
                        then=-F("valor_liquido"),
                    ),
                    default=F("valor_liquido"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            ),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=16, decimal_places=2)),
        ),
    )
    return {
        "quantidade": int(total_registros or 0),
        "valor_faturado": float(agregado.get("valor_faturado") or 0),
    }


def _filtros_sem_campo(filtros, campo):
    alvo = str(campo or "").strip()
    if not alvo:
        return list(filtros or [])
    return [
        filtro for filtro in (filtros or [])
        if str((filtro or {}).get("field") or "").strip() != alvo
    ]


def _opcoes_texto_distintas_contas(qs, campo_lookup):
    valores = (
        qs.exclude(**{f"{campo_lookup}__isnull": True})
        .exclude(**{campo_lookup: ""})
        .order_by(campo_lookup)
        .values_list(campo_lookup, flat=True)
        .distinct()
    )
    return [
        {"value": str(valor), "label": str(valor)}
        for valor in valores
        if str(valor or "").strip()
    ]


def _opcoes_data_arquivo_contas(qs):
    datas = (
        qs.exclude(data_arquivo__isnull=True)
        .order_by("-data_arquivo")
        .values_list("data_arquivo", flat=True)
        .distinct()
    )
    return [
        {"value": data.strftime("%Y-%m-%d"), "label": _fmt_date_br(data)}
        for data in datas
        if data
    ]


def _opcoes_externas_contas_a_receber(base_qs, filtros):
    filtros_status = _filtros_sem_campo(filtros, "status")
    filtros_intervalo = _filtros_sem_campo(filtros, "intervalo")
    filtros_data_arquivo = _filtros_sem_campo(filtros, "data_arquivo_iso")
    filtros_titulo = _filtros_sem_campo(filtros, "titulo_descricao")
    filtros_nome = _filtros_sem_campo(filtros, "nome_fantasia_empresa")
    filtros_natureza = _filtros_sem_campo(filtros, "natureza_descricao")
    filtros_posicao = _filtros_sem_campo(filtros, "posicao_contagem")

    qs_status = _aplicar_filtros_contas_a_receber(base_qs, filtros_status)
    qs_intervalo = _aplicar_filtros_contas_a_receber(base_qs, filtros_intervalo)
    qs_data_arquivo = _aplicar_filtros_contas_a_receber(base_qs, filtros_data_arquivo)
    qs_titulo = _aplicar_filtros_contas_a_receber(base_qs, filtros_titulo)
    qs_nome = _aplicar_filtros_contas_a_receber(base_qs, filtros_nome)
    qs_natureza = _aplicar_filtros_contas_a_receber(base_qs, filtros_natureza)
    qs_posicao = _aplicar_filtros_contas_a_receber(base_qs, filtros_posicao)

    hoje = datetime.now().date()
    opcoes_status = []
    if qs_status.filter(data_vencimento__lt=hoje).exists():
        opcoes_status.append({"value": "Vencido", "label": "Vencido"})
    if qs_status.filter(data_vencimento__gte=hoje).exists():
        opcoes_status.append({"value": "A Vencer", "label": "A Vencer"})

    opcoes_intervalo = []
    intervalos = [
        "0-5 (CML)",
        "6-20 (FIN)",
        "21-30 (POL)",
        "31-60 (POL)",
        "61-90 (POL)",
        "91-120 (JUR1)",
        "121-180 (JUR1)",
        "+180 (JUR2)",
    ]
    for item in intervalos:
        if _filtrar_contas_a_receber_por_intervalo(qs_intervalo, item).exists():
            opcoes_intervalo.append({"value": item, "label": item})

    ultima_data, penultima_data = _datas_posicao_contas(qs_posicao)
    opcoes_posicao = []
    if ultima_data:
        opcoes_posicao.append({"value": "ultima_posicao", "label": "Ultima Posicao"})
    if penultima_data:
        opcoes_posicao.append({"value": "penultima_posicao", "label": "Penultima Posicao"})

    q_anteriores = Q()
    if ultima_data:
        q_anteriores &= ~Q(data_arquivo=ultima_data)
    if penultima_data:
        q_anteriores &= ~Q(data_arquivo=penultima_data)
    if qs_posicao.filter(q_anteriores).exists():
        opcoes_posicao.append({"value": "anteriores_posicao", "label": "Anteriores"})

    return {
        "status": opcoes_status,
        "intervalo": opcoes_intervalo,
        "data_arquivo_iso": _opcoes_data_arquivo_contas(qs_data_arquivo),
        "titulo_descricao": _opcoes_texto_distintas_contas(qs_titulo, "titulo__descricao"),
        "nome_fantasia_empresa": _opcoes_texto_distintas_contas(qs_nome, "nome_fantasia_empresa"),
        "natureza_descricao": _opcoes_texto_distintas_contas(qs_natureza, "natureza__descricao"),
        "posicao_contagem": opcoes_posicao,
    }


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


def _usuario_pode_gerenciar_atividade(usuario, atividade):
    return atividade.pode_ser_editada_por(usuario)


@login_required(login_url="entrar")
def index(request):
    return render(request, "index.html")

@login_required(login_url="entrar")
def financeiro(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Financeiro"),
    }
    return render(request, "financeiro/financeiro.html", contexto)


@login_required(login_url="entrar")
def administrativo(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Administrativo"),
    }
    return render(request, "administrativo/administrativo.html", contexto)


@login_required(login_url="entrar")
def comercial(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Comercial"),
    }
    return render(request, "comercial/comercial.html", contexto)


@login_required(login_url="entrar")
def parametros(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Parametros"),
    }
    return render(request, "parametros/parametros.html", contexto)


@login_required(login_url="entrar")
def operacional(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Operacional"),
    }
    return render(request, "operacional/operacional.html", contexto)


def entrar(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login bem-sucedido!")
            return redirect("index")
        messages.error(request, "Credenciais invalidas. Tente novamente.")
    return render(request, "autentificacao/entrar.html")


@login_required(login_url="entrar")
def sair(request):
    logout(request)
    messages.success(request, "Logout bem-sucedido!")
    return redirect("entrar")


def _usuario_admin_pode_acessar_empresa(usuario, empresa):
    if not usuario:
        return False
    if usuario.is_superuser:
        return True
    if not empresa:
        return False
    if not usuario.is_staff:
        return False
    return bool(getattr(usuario, "empresa_id", None) and usuario.empresa_id == empresa.id)


def _empresas_painel_admin_para_usuario(usuario):
    if usuario.is_superuser:
        return Empresa.objects.all()
    if not usuario.is_staff or not getattr(usuario, "empresa_id", None):
        return Empresa.objects.none()
    return Empresa.objects.filter(id=usuario.empresa_id)


def _obter_empresa_admin_autorizada(request, empresa_id):
    empresa = Empresa.objects.filter(id=empresa_id).first()
    if not empresa:
        messages.error(request, "Empresa nao encontrada.")
        return None
    if not _usuario_admin_pode_acessar_empresa(request.user, empresa):
        messages.error(request, "Voce nao tem permissao para acessar esta empresa.")
        return None
    return empresa


def _obter_usuario_admin_autorizado(request, usuario_id):
    usuario = Usuario.objects.select_related("empresa").filter(id=usuario_id).first()
    if not usuario:
        messages.error(request, "Usuario nao encontrado.")
        return None
    if not _usuario_admin_pode_acessar_empresa(request.user, usuario.empresa):
        messages.error(request, "Voce nao tem permissao para acessar este usuario.")
        return None
    return usuario


@staff_member_required(login_url="entrar")
def painel_admin(request):
    empresas = _empresas_painel_admin_para_usuario(request.user).order_by("nome")
    contexto = {
        "empresas": empresas,
        "pode_cadastrar_empresa": request.user.is_superuser,
        "pode_editar_possui_sistema": request.user.is_superuser,
    }
    return render(request, "admin/painel_admin.html", contexto)


@staff_member_required(login_url="entrar")
def criar_empresa(request):
    if not request.user.is_superuser:
        messages.error(request, "Somente superusuario pode cadastrar empresa.")
        return redirect("painel_admin")
    if request.method == "POST":
        erro = criar_empresa_por_nome(
            request.POST.get("nome"),
            possui_sistema=_valor_checkbox_possui_sistema(request.POST),
        )
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa criada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def editar_empresa(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    if request.method == "POST":
        possui_sistema = empresa.possui_sistema
        if request.user.is_superuser:
            possui_sistema = _valor_checkbox_possui_sistema(request.POST)
        erro = atualizar_empresa_por_nome(
            empresa,
            request.POST.get("nome"),
            possui_sistema=possui_sistema,
        )
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa atualizada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def excluir_empresa(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    ok, mensagem = excluir_empresa_por_id(empresa_id)
    if ok:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def usuarios_permissoes(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    usuarios_qs = Usuario.objects.filter(empresa=empresa).prefetch_related("permissoes")
    usuarios = usuarios_com_permissoes_ids(usuarios_qs)

    contexto = {
        "empresa": empresa,
        "usuarios": usuarios,
        "permissoes_por_modulo": _obter_permissoes_por_modulo(),
    }
    return render(request, "admin/usuarios_permissoes.html", contexto)


@staff_member_required(login_url="entrar")
def cadastrar_usuario(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")
    if request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        erro = criar_usuario_por_post(empresa, request.POST, permissoes)
        if erro:
            messages.error(request, erro)
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        messages.success(request, "Usuario criado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def editar_usuario(request, usuario_id):
    usuario = _obter_usuario_admin_autorizado(request, usuario_id)
    if not usuario:
        return redirect("painel_admin")
    empresa_id = usuario.empresa_id
    if not empresa_id:
        messages.error(request, "Usuario sem empresa vinculada.")
        return redirect("painel_admin")
    if request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        erro = atualizar_usuario_por_post(
            usuario,
            request.POST,
            permissoes,
            usuario_logado=request.user,
        )
        if erro:
            messages.error(request, erro)
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        messages.success(request, "Usuario atualizado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def excluir_usuario(request, usuario_id):
    usuario = _obter_usuario_admin_autorizado(request, usuario_id)
    if not usuario:
        return redirect("painel_admin")

    ok, empresa_id, mensagem = excluir_usuario_por_id(usuario_id)
    if ok:
        messages.success(request, mensagem)
        if empresa_id:
            return redirect("usuarios_permissoes", empresa_id=empresa_id)
        return redirect("painel_admin")
    messages.error(request, mensagem)
    return redirect("painel_admin")

@login_required(login_url="entrar")
def tofu_lista_de_atividades(request, empresa_id):
    # 1) Autorizacao
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    # 2) Query
    atividades_qs = (
        Atividade.objects.filter(projeto__empresa=empresa)
        .select_related("projeto", "gestor", "responsavel", "usuario")
        .order_by("-id")
    )
    projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
    colaboradores = Colaborador.objects.filter(empresa=empresa).order_by("nome")

    # 3) Transformacao
    contexto = montar_contexto_tofu_lista(
        empresa=empresa,
        atividades_qs=atividades_qs,
        projetos=projetos,
        colaboradores=colaboradores,
        usuario_logado=request.user,
    )

    # 4) Render
    return render(request, "administrativo/tofu_lista_de_atividades.html", contexto)




@login_required(login_url="entrar")
def criar_atividade_tofu(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    erro = criar_atividade_por_post(request.POST, empresa, usuario=request.user)
    if erro:
        messages.error(request, erro)
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)
    messages.success(request, "Atividade criada com sucesso.")
    return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_atividade_tofu(request, empresa_id, atividade_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    atividade = Atividade.objects.filter(id=atividade_id, projeto__empresa=empresa).first()
    if not atividade:
        messages.error(request, "Atividade nao encontrada.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)
    if not _usuario_pode_gerenciar_atividade(request.user, atividade):
        messages.error(request, "Voce nao pode editar esta atividade.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_atividade_por_post(atividade, request.POST, empresa)
        if erro:
            messages.error(request, erro)
            return redirect("editar_atividade_tofu", empresa_id=empresa.id, atividade_id=atividade.id)
        messages.success(request, "Atividade atualizada com sucesso.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
    colaboradores = Colaborador.objects.filter(empresa=empresa).order_by("nome")
    semana_de_prazo_valor = semana_iso_input_atividade(atividade)
    contexto = {
        "empresa": empresa,
        "atividade": atividade,
        "projetos": projetos,
        "colaboradores": colaboradores,
        "semana_de_prazo_valor": semana_de_prazo_valor,
    }
    return render(request, "administrativo/tofu_editar_atividade.html", contexto)


@login_required(login_url="entrar")
def excluir_atividade_tofu(request, empresa_id, atividade_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    atividade = Atividade.objects.filter(id=atividade_id, projeto__empresa=empresa).first()
    if not atividade:
        messages.error(request, "Atividade nao encontrada.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)
    if not _usuario_pode_gerenciar_atividade(request.user, atividade):
        messages.error(request, "Voce nao pode excluir esta atividade.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    atividade.excluir_atividade()
    messages.success(request, "Atividade excluida com sucesso.")
    return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)


@login_required(login_url="entrar")
def colaboradores_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Colaboradores")
    if not autorizado:
        return redirect("index")

    colaboradores = Colaborador.objects.filter(empresa=empresa).order_by("nome")
    colaboradores_tabulator = build_colaboradores_tabulator(colaboradores, empresa.id)
    contexto = {
        "empresa": empresa,
        "colaboradores": colaboradores,
        "colaboradores_tabulator": colaboradores_tabulator,
    }
    return render(request, "administrativo/colaboradores.html", contexto)


@login_required(login_url="entrar")
def criar_colaborador_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Colaboradores")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("colaboradores", empresa_id=empresa.id)

    erro = criar_colaborador_por_nome(empresa, request.POST.get("nome"))
    if erro:
        messages.error(request, erro)
        return redirect("colaboradores", empresa_id=empresa.id)
    messages.success(request, "Colaborador criado com sucesso.")
    return redirect("colaboradores", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_colaborador_modulo(request, empresa_id, colaborador_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Colaboradores")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("colaboradores", empresa_id=empresa.id)

    colaborador = Colaborador.objects.filter(id=colaborador_id, empresa=empresa).first()
    if not colaborador:
        messages.error(request, "Colaborador nao encontrado.")
        return redirect("colaboradores", empresa_id=empresa.id)

    erro = atualizar_colaborador_por_nome(colaborador, request.POST.get("nome"))
    if erro:
        messages.error(request, erro)
        return redirect("colaboradores", empresa_id=empresa.id)
    messages.success(request, "Colaborador atualizado com sucesso.")
    return redirect("colaboradores", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_colaborador_modulo(request, empresa_id, colaborador_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Colaboradores")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("colaboradores", empresa_id=empresa.id)

    colaborador = Colaborador.objects.filter(id=colaborador_id, empresa=empresa).first()
    if not colaborador:
        messages.error(request, "Colaborador nao encontrado.")
        return redirect("colaboradores", empresa_id=empresa.id)

    colaborador.excluir_colaborador()
    messages.success(request, "Colaborador excluido com sucesso.")
    return redirect("colaboradores", empresa_id=empresa.id)


@login_required(login_url="entrar")
def projetos_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Projetos")
    if not autorizado:
        return redirect("index")

    projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
    projetos_tabulator = build_projetos_tabulator(projetos, empresa.id)
    contexto = {
        "empresa": empresa,
        "projetos": projetos,
        "projetos_tabulator": projetos_tabulator,
    }
    return render(request, "administrativo/projetos.html", contexto)


@login_required(login_url="entrar")
def criar_projeto_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Projetos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("projetos", empresa_id=empresa.id)

    erro = criar_projeto_por_dados(empresa, request.POST.get("nome"), request.POST.get("codigo"))
    if erro:
        messages.error(request, erro)
        return redirect("projetos", empresa_id=empresa.id)
    messages.success(request, "Projeto criado com sucesso.")
    return redirect("projetos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_projeto_modulo(request, empresa_id, projeto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Projetos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("projetos", empresa_id=empresa.id)

    projeto = Projeto.objects.filter(id=projeto_id, empresa=empresa).first()
    if not projeto:
        messages.error(request, "Projeto nao encontrado.")
        return redirect("projetos", empresa_id=empresa.id)

    erro = atualizar_projeto_por_dados(projeto, request.POST.get("nome"), request.POST.get("codigo"))
    if erro:
        messages.error(request, erro)
        return redirect("projetos", empresa_id=empresa.id)
    messages.success(request, "Projeto atualizado com sucesso.")
    return redirect("projetos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_projeto_modulo(request, empresa_id, projeto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Projetos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("projetos", empresa_id=empresa.id)

    projeto = Projeto.objects.filter(id=projeto_id, empresa=empresa).first()
    if not projeto:
        messages.error(request, "Projeto nao encontrado.")
        return redirect("projetos", empresa_id=empresa.id)

    projeto.excluir_projeto()
    messages.success(request, "Projeto excluido com sucesso.")
    return redirect("projetos", empresa_id=empresa.id)

@login_required(login_url="entrar")
def comite_diario(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Comite Diario")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def balanco_patrimonial(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Balanco Patrimonial")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def dre(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "DRE")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def contas_a_receber(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_contas_a_receber(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_conta"},
        ):
            return redirect("contas_a_receber", empresa_id=empresa.id)
        if acao == "criar_conta":
            erro = criar_contas_a_receber_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Contas a Receber criado com sucesso.")
        else:
            arquivos = request.FILES.getlist("arquivos_contas_a_receber")
            ok, mensagem = importar_upload_contas_a_receber(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("contas_a_receber", empresa_id=empresa.id)

    arquivos_existentes = sorted(
        [
            str(f.relative_to(diretorio_importacao)).replace("\\", "/")
            for f in diretorio_importacao.rglob("*.xls")
            if diretorio_subscritos not in f.parents
        ]
    )
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="contas_a_receber",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["contas_a_receber"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "contas_tabulator_url": reverse("contas_a_receber_dados", kwargs={"empresa_id": empresa.id}),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def contas_a_receber_dados(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contas a Receber")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)

    page_raw = str(request.GET.get("page") or "").strip()
    size_raw = str(request.GET.get("size") or "").strip()
    try:
        page = int(page_raw) if page_raw else 1
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(size_raw) if size_raw else 100
    except (TypeError, ValueError):
        page_size = 100

    page = max(page, 1)
    page_size = max(1, min(page_size, 200))

    filtros = _coletar_param_json_lista(request, ("filters", "filter"))
    sorters = _coletar_param_json_lista(request, ("sorters", "sort"))

    base_qs = ContasAReceber.objects.filter(empresa=empresa)
    filtrado_qs = _aplicar_filtros_contas_a_receber(base_qs, filtros)
    ordenado_qs = _ordenar_contas_a_receber(filtrado_qs, sorters)
    filtros_externos = _opcoes_externas_contas_a_receber(base_qs, filtros)

    total_registros = ordenado_qs.count()
    total_paginas = max(1, (total_registros + page_size - 1) // page_size)
    if page > total_paginas:
        page = total_paginas

    inicio = (page - 1) * page_size
    fim = inicio + page_size

    contas_pagina_qs = (
        ordenado_qs
        .annotate(
            valor_desdobramento_num=Cast("valor_desdobramento", FloatField()),
            valor_liquido_num=Cast("valor_liquido", FloatField()),
        )
        .values(
            "id",
            "data_negociacao",
            "data_vencimento",
            "data_arquivo",
            "nome_fantasia_empresa",
            "numero_nota",
            "vendedor",
            "valor_desdobramento_num",
            "valor_liquido_num",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "parceiro__codigo",
            "parceiro__nome",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
        )[inicio:fim]
    )

    permitir_edicao = not _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    dados = build_contas_a_receber_tabulator(
        contas_pagina_qs,
        empresa.id,
        permitir_edicao=permitir_edicao,
    )
    resumo = _resumo_contas_a_receber(filtrado_qs, total_registros)

    return JsonResponse(
        {
            "data": dados,
            "last_page": total_paginas,
            "last_row": total_registros,
            "summary": resumo,
            "external_filters": filtros_externos,
        }
    )


@login_required(login_url="entrar")
def dfc(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "DFC")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_dfc(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_dfc"},
        ):
            return redirect("dfc", empresa_id=empresa.id)
        if acao == "criar_dfc":
            erro = criar_dfc_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de DFC criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_dfc")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_dfc(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("dfc", empresa_id=empresa.id)

    dfc_qs = (
        FluxoDeCaixaDFC.objects.filter(empresa=empresa)
        .annotate(valor_liquido_num=Cast("valor_liquido", FloatField()))
        .values(
            "id",
            "empresa_id",
            "empresa__nome",
            "data_negociacao",
            "data_vencimento",
            "valor_liquido_num",
            "numero_nota",
            "titulo_id",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "centro_resultado_id",
            "centro_resultado__descricao",
            "natureza_id",
            "natureza__codigo",
            "natureza__descricao",
            "historico",
            "parceiro_id",
            "parceiro__codigo",
            "parceiro__nome",
            "operacao_id",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
            "tipo_movimento",
        )
        .order_by("-id")
    )

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="dfc",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["dfc"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "dfc_tabulator": build_dfc_tabulator(
            dfc_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


def _orcamentos_realizados_qs_para_tabulator(empresa):
    return (
        Orcamento.objects.filter(empresa=empresa)
        .annotate(
            valor_baixa_num=Cast("valor_baixa", FloatField()),
            valor_liquido_num=Cast("valor_liquido", FloatField()),
            valor_desdobramento_num=Cast("valor_desdobramento", FloatField()),
        )
        .values(
            "id",
            "nome_empresa",
            "data_vencimento",
            "data_baixa",
            "valor_baixa_num",
            "valor_liquido_num",
            "valor_desdobramento_num",
            "titulo_id",
            "natureza_id",
            "centro_resultado_id",
            "operacao_id",
            "parceiro_id",
            "titulo__tipo_titulo_codigo",
            "titulo__descricao",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "operacao__tipo_operacao_codigo",
            "operacao__descricao_receita_despesa",
            "parceiro__codigo",
            "parceiro__nome",
        )
        .order_by("-data_vencimento", "-id")
    )


def _orcamentos_planejados_qs_para_tabulator(empresa):
    return (
        OrcamentoPlanejado.objects.filter(empresa=empresa)
        .annotate(
            janeiro_num=Cast("janeiro", FloatField()),
            fevereiro_num=Cast("fevereiro", FloatField()),
            marco_num=Cast("marco", FloatField()),
            abril_num=Cast("abril", FloatField()),
            maio_num=Cast("maio", FloatField()),
            junho_num=Cast("junho", FloatField()),
            julho_num=Cast("julho", FloatField()),
            agosto_num=Cast("agosto", FloatField()),
            setembro_num=Cast("setembro", FloatField()),
            outubro_num=Cast("outubro", FloatField()),
            novembro_num=Cast("novembro", FloatField()),
            dezembro_num=Cast("dezembro", FloatField()),
        )
        .values(
            "id",
            "nome_empresa",
            "ano",
            "natureza_id",
            "centro_resultado_id",
            "natureza__codigo",
            "natureza__descricao",
            "centro_resultado__descricao",
            "janeiro_num",
            "fevereiro_num",
            "marco_num",
            "abril_num",
            "maio_num",
            "junho_num",
            "julho_num",
            "agosto_num",
            "setembro_num",
            "outubro_num",
            "novembro_num",
            "dezembro_num",
            "natureza__descricao",
            "centro_resultado__descricao",
        )
        .order_by("ano", "centro_resultado__descricao", "natureza__descricao")
    )


@login_required(login_url="entrar")
def orcamento(request, empresa_id):
    modulo = {"nome": "Orcamento x Realizado", "template": "administrativo/orcamento.html"}
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_orcamento(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "importar_orcamento":
            arquivos = request.FILES.getlist("arquivos_orcamento")
            ok, mensagem = importar_upload_orcamento(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.error(request, "Acao de importacao invalida.")
        return redirect("orcamento", empresa_id=empresa.id)

    orcamentos_realizados_qs = _orcamentos_realizados_qs_para_tabulator(empresa)
    orcamentos_qs = _orcamentos_planejados_qs_para_tabulator(empresa)

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="orcamento",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["orcamento"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "orcamento_x_realizado_tabulator": build_orcamento_x_realizado_tabulator(
            orcamentos_realizados_qs,
            orcamentos_qs,
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def orcamentos_realizados(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "criar_orcamento":
            erro = criar_orcamento_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Orcamento criado com sucesso.")
        else:
            messages.error(request, "Acao de Orcamento invalida.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamentos_realizados_qs = _orcamentos_realizados_qs_para_tabulator(empresa)

    titulos_qs = Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo")
    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    operacoes_qs = Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo")
    parceiros_qs = Parceiro.objects.filter(empresa=empresa).order_by("nome")
    centros_resultado_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")

    contexto = {
        "empresa": empresa,
        "orcamento_tabulator": build_orcamento_tabulator(orcamentos_realizados_qs, empresa.id),
        "titulos": titulos_qs,
        "naturezas": naturezas_qs,
        "operacoes": operacoes_qs,
        "parceiros": parceiros_qs,
        "centros_resultado": centros_resultado_qs,
        "orcamento_titulos_js": list(
            titulos_qs.values("id", "tipo_titulo_codigo", "descricao")
        ),
        "orcamento_naturezas_js": list(
            naturezas_qs.values("id", "codigo", "descricao")
        ),
        "orcamento_operacoes_js": list(
            operacoes_qs.values("id", "tipo_operacao_codigo", "descricao_receita_despesa")
        ),
        "orcamento_parceiros_js": list(
            parceiros_qs.values("id", "codigo", "nome")
        ),
        "orcamento_centros_resultado_js": list(
            centros_resultado_qs.values("id", "descricao")
        ),
    }
    return render(request, "administrativo/orcamentos_realizados.html", contexto)


@login_required(login_url="entrar")
def orcamentos(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not permitido:
        return redirect("index")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "criar_orcamento_planejado":
            erro = criar_orcamento_planejado_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Orcamento planejado criado com sucesso.")
        else:
            messages.error(request, "Acao de Orcamento invalida.")
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamentos_qs = _orcamentos_planejados_qs_para_tabulator(empresa)

    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    centros_resultado_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")

    contexto = {
        "empresa": empresa,
        "orcamentos_tabulator": build_orcamentos_planejados_tabulator(orcamentos_qs, empresa.id),
        "naturezas": naturezas_qs,
        "centros_resultado": centros_resultado_qs,
        "orcamento_planejado_naturezas_js": list(
            naturezas_qs.values("id", "codigo", "descricao")
        ),
        "orcamento_planejado_centros_resultado_js": list(
            centros_resultado_qs.values("id", "descricao")
        ),
    }
    return render(request, "administrativo/orcamentos.html", contexto)


@login_required(login_url="entrar")
def editar_orcamento_modulo(request, empresa_id, orcamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    orcamento_item = Orcamento.objects.filter(id=orcamento_id, empresa=empresa).first()
    if not orcamento_item:
        messages.error(request, "Registro de Orcamento nao encontrado.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_orcamento_por_post(orcamento_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_orcamento_modulo", empresa_id=empresa.id, orcamento_id=orcamento_item.id)
        messages.success(request, "Registro de Orcamento atualizado com sucesso.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "orcamento_item": orcamento_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "administrativo/orcamento_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_orcamento_modulo(request, empresa_id, orcamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamento_item = Orcamento.objects.filter(id=orcamento_id, empresa=empresa).first()
    if not orcamento_item:
        messages.error(request, "Registro de Orcamento nao encontrado.")
        return redirect("orcamentos_realizados", empresa_id=empresa.id)

    orcamento_item.excluir_orcamento()
    messages.success(request, "Registro de Orcamento excluido com sucesso.")
    return redirect("orcamentos_realizados", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_orcamento_planejado_modulo(request, empresa_id, orcamento_planejado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    orcamento_planejado_item = OrcamentoPlanejado.objects.filter(id=orcamento_planejado_id, empresa=empresa).first()
    if not orcamento_planejado_item:
        messages.error(request, "Orcamento planejado nao encontrado.")
        return redirect("orcamentos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_orcamento_planejado_por_post(orcamento_planejado_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect(
                "editar_orcamento_planejado_modulo",
                empresa_id=empresa.id,
                orcamento_planejado_id=orcamento_planejado_item.id,
            )
        messages.success(request, "Orcamento planejado atualizado com sucesso.")
        return redirect("orcamentos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "orcamento_planejado_item": orcamento_planejado_item,
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "administrativo/orcamento_planejado_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_orcamento_planejado_modulo(request, empresa_id, orcamento_planejado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Orcamento x Realizado")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamento_planejado_item = OrcamentoPlanejado.objects.filter(id=orcamento_planejado_id, empresa=empresa).first()
    if not orcamento_planejado_item:
        messages.error(request, "Orcamento planejado nao encontrado.")
        return redirect("orcamentos", empresa_id=empresa.id)

    orcamento_planejado_item.excluir_orcamento_planejado()
    messages.success(request, "Orcamento planejado excluido com sucesso.")
    return redirect("orcamentos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def adiantamentos(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Adiantamentos")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_adiantamentos(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_adiantamento"},
        ):
            return redirect("adiantamentos", empresa_id=empresa.id)
        if acao == "criar_adiantamento":
            erro = criar_adiantamento_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Adiantamentos criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_adiantamentos")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_adiantamentos(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("adiantamentos", empresa_id=empresa.id)

    adiantamentos_qs = (
        Adiantamento.objects.filter(empresa=empresa)
        .annotate(
            saldo_banco_em_reais_num=Cast("saldo_banco_em_reais", FloatField()),
            saldo_real_em_reais_num=Cast("saldo_real_em_reais", FloatField()),
            saldo_real_num=Cast("saldo_real", FloatField()),
        )
        .values(
            "id",
            "empresa_id",
            "empresa__nome",
            "moeda",
            "saldo_banco_em_reais_num",
            "saldo_real_em_reais_num",
            "saldo_real_num",
            "conta_descricao",
            "saldo_banco",
            "banco",
            "agencia",
            "conta_bancaria",
            "empresa_descricao",
        )
        .order_by("-id")
    )

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="adiantamentos",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["adiantamentos"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "adiantamentos_tabulator": build_adiantamentos_tabulator(
            adiantamentos_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def contratos_redes(request, empresa_id):
    modulo = _obter_modulo("Financeiro", "Contratos Redes")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def plano_de_cargos_e_salarios(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Plano de Cargos e Salarios")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def descritivos(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Descritivos")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def fiscal_e_contabil(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Fiscal e Contabil")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def faturamento(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Faturamento")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_faturamento(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_faturamento"},
        ):
            return redirect("faturamento", empresa_id=empresa.id)

        if acao == "criar_faturamento":
            erro = criar_faturamento_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de Faturamento criado com sucesso.")
        else:
            arquivos = request.FILES.getlist("arquivos_faturamento")
            ok, mensagem = importar_upload_faturamento(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("faturamento", empresa_id=empresa.id)

    faturamento_qs = (
        Faturamento.objects.filter(empresa=empresa)
        .annotate(
            valor_nota_num=Cast("valor_nota", FloatField()),
            participacao_venda_geral_num=Cast("participacao_venda_geral", FloatField()),
            participacao_venda_cliente_num=Cast("participacao_venda_cliente", FloatField()),
            valor_nota_unico_num=Cast("valor_nota_unico", FloatField()),
            peso_bruto_unico_num=Cast("peso_bruto_unico", FloatField()),
            quantidade_volumes_num=Cast("quantidade_volumes", FloatField()),
            quantidade_saida_num=Cast("quantidade_saida", FloatField()),
            prazo_medio_num=Cast("prazo_medio", FloatField()),
            media_unica_num=Cast("media_unica", FloatField()),
            valor_frete_num=Cast("valor_frete", FloatField()),
        )
        .values(
            "id",
            "nome_origem",
            "data_faturamento",
            "nome_empresa",
            "parceiro_id",
            "parceiro__codigo",
            "parceiro__nome",
            "parceiro__cidade__nome",
            "numero_nota",
            "valor_nota_num",
            "participacao_venda_geral_num",
            "participacao_venda_cliente_num",
            "valor_nota_unico_num",
            "peso_bruto_unico_num",
            "quantidade_volumes_num",
            "quantidade_saida_num",
            "status_nfe",
            "apelido_vendedor",
            "operacao_id",
            "operacao__descricao_receita_despesa",
            "natureza_id",
            "natureza__descricao",
            "centro_resultado_id",
            "centro_resultado__descricao",
            "tipo_movimento",
            "prazo_medio_num",
            "media_unica_num",
            "tipo_venda",
            "produto_id",
            "produto__codigo_produto",
            "produto__descricao_produto",
            "gerente",
            "descricao_perfil",
            "valor_frete_num",
        )
        .order_by("-data_faturamento", "-id")
    )

    arquivos_existentes = sorted(
        [
            str(arquivo.relative_to(diretorio_importacao)).replace("\\", "/")
            for arquivo in diretorio_importacao.rglob("*")
            if arquivo.is_file() and diretorio_subscritos not in arquivo.parents
        ]
    )
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="faturamento",
        empresa_id=empresa.id,
        extensoes={".xlsx"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["faturamento"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("descricao_receita_despesa"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("descricao"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "produtos": Produto.objects.filter(empresa=empresa).order_by("descricao_produto"),
        "faturamento_tabulator": build_faturamento_tabulator(
            faturamento_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def apuracao_de_resultados(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Apuracao de Resultados")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def orcamento_x_realizado(request, empresa_id):
    return redirect("orcamento", empresa_id=empresa_id)


@login_required(login_url="entrar")
def colaboradores(request, empresa_id):
    return colaboradores_modulo(request, empresa_id)


@login_required(login_url="entrar")
def projetos(request, empresa_id):
    return projetos_modulo(request, empresa_id)


@login_required(login_url="entrar")
def parceiros(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    parceiros_qs = Parceiro.objects.filter(empresa=empresa).select_related("cidade").order_by("nome")
    cidades_qs = Cidade.objects.filter(empresa=empresa).order_by("nome")
    parceiros_tabulator = build_parceiros_tabulator(parceiros_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "parceiros": parceiros_qs,
        "cidades": cidades_qs,
        "cidades_js": list(cidades_qs.values("id", "nome", "codigo")),
        "parceiros_tabulator": parceiros_tabulator,
    }
    return render(request, "financeiro/parceiros.html", contexto)


@login_required(login_url="entrar")
def criar_parceiro_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    erro = criar_parceiro_por_dados(
        empresa,
        request.POST.get("nome"),
        request.POST.get("codigo"),
        request.POST.get("cidade_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("parceiros", empresa_id=empresa.id)
    messages.success(request, "Parceiro criado com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_parceiro_modulo(request, empresa_id, parceiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro = Parceiro.objects.filter(id=parceiro_id, empresa=empresa).first()
    if not parceiro:
        messages.error(request, "Parceiro não encontrado.")
        return redirect("parceiros", empresa_id=empresa.id)

    erro = atualizar_parceiro_por_dados(
        parceiro,
        request.POST.get("nome"),
        request.POST.get("codigo"),
        empresa,
        request.POST.get("cidade_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("parceiros", empresa_id=empresa.id)
    messages.success(request, "Parceiro atualizado com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_parceiro_modulo(request, empresa_id, parceiro_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parceiros")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro = Parceiro.objects.filter(id=parceiro_id, empresa=empresa).first()
    if not parceiro:
        messages.error(request, "Parceiro não encontrado.")
        return redirect("parceiros", empresa_id=empresa.id)

    parceiro.excluir_parceiro()
    messages.success(request, "Parceiro excluído com sucesso.")
    return redirect("parceiros", empresa_id=empresa.id)


@login_required(login_url="entrar")
def parametros_vendas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Vendas")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro, total_recalculado = criar_parametro_margem_vendas(empresa, request.POST)
        elif acao == "editar":
            item = ParametroMargemVendas.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_vendas", empresa_id=empresa.id)
            erro, total_recalculado = atualizar_parametro_margem_vendas(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroMargemVendas.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_vendas", empresa_id=empresa.id)
            erro, total_recalculado = excluir_parametro_margem_vendas(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros de vendas.")
            return redirect("parametros_vendas", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_vendas", empresa_id=empresa.id)
        messages.success(request, f"Parametros de vendas atualizados. Registros recalculados: {total_recalculado}.")
        return redirect("parametros_vendas", empresa_id=empresa.id)

    parametros_qs = ParametroMargemVendas.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_vendas_tabulator": build_parametros_margem_vendas_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_vendas.html", contexto)


@login_required(login_url="entrar")
def parametros_logistica(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Logistica")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro, total_recalculado = criar_parametro_margem_logistica(empresa, request.POST)
        elif acao == "editar":
            item = ParametroMargemLogistica.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_logistica", empresa_id=empresa.id)
            erro, total_recalculado = atualizar_parametro_margem_logistica(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroMargemLogistica.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_logistica", empresa_id=empresa.id)
            erro, total_recalculado = excluir_parametro_margem_logistica(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros de logistica.")
            return redirect("parametros_logistica", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_logistica", empresa_id=empresa.id)
        messages.success(request, f"Parametros de logistica atualizados. Registros recalculados: {total_recalculado}.")
        return redirect("parametros_logistica", empresa_id=empresa.id)

    parametros_qs = ParametroMargemLogistica.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_logistica_tabulator": build_parametros_margem_logistica_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_logistica.html", contexto)


@login_required(login_url="entrar")
def parametros_administracao(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Administracao")
    if not autorizado:
        return redirect("index")

    parametro, _ = ParametroMargemAdministracao.objects.get_or_create(empresa=empresa)
    if request.method == "POST":
        total_recalculado = salvar_parametro_margem_administracao(empresa, request.POST)
        messages.success(
            request,
            f"Parametros de administracao salvos. Registros de Controle de Margem recalculados: {total_recalculado}.",
        )
        return redirect("parametros_administracao", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "parametro": parametro,
    }
    return render(request, "parametros/parametros_administracao.html", contexto)


@login_required(login_url="entrar")
def parametros_financeiro(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Parametros Financeiro")
    if not autorizado:
        return redirect("index")

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if acao == "criar":
            erro, total_recalculado = criar_parametro_margem_financeiro(empresa, request.POST)
        elif acao == "editar":
            item = ParametroMargemFinanceiro.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_financeiro", empresa_id=empresa.id)
            erro, total_recalculado = atualizar_parametro_margem_financeiro(item, empresa, request.POST)
        elif acao == "excluir":
            item = ParametroMargemFinanceiro.objects.filter(id=request.POST.get("item_id"), empresa=empresa).first()
            if not item:
                messages.error(request, "Parametro nao encontrado.")
                return redirect("parametros_financeiro", empresa_id=empresa.id)
            erro, total_recalculado = excluir_parametro_margem_financeiro(item, empresa)
        else:
            messages.error(request, "Acao invalida para parametros financeiro.")
            return redirect("parametros_financeiro", empresa_id=empresa.id)

        if erro:
            messages.error(request, erro)
            return redirect("parametros_financeiro", empresa_id=empresa.id)
        messages.success(request, f"Parametros financeiro atualizados. Registros recalculados: {total_recalculado}.")
        return redirect("parametros_financeiro", empresa_id=empresa.id)

    parametros_qs = ParametroMargemFinanceiro.objects.filter(empresa=empresa).order_by("id")
    contexto = {
        "empresa": empresa,
        "parametros": parametros_qs,
        "parametros_financeiro_tabulator": build_parametros_margem_financeiro_tabulator(parametros_qs, empresa.id),
    }
    return render(request, "parametros/parametros_financeiro.html", contexto)


@login_required(login_url="entrar")
def produtos(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")

    produtos_qs = Produto.objects.filter(empresa=empresa).order_by("codigo_produto")
    produtos_tabulator = build_produtos_tabulator(produtos_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "produtos": produtos_qs,
        "produtos_tabulator": produtos_tabulator,
    }
    return render(request, "parametros/produtos.html", contexto)


@login_required(login_url="entrar")
def criar_produto_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("produtos", empresa_id=empresa.id)

    erro = criar_produto_por_dados(empresa, request.POST)
    if erro:
        messages.error(request, erro)
        return redirect("produtos", empresa_id=empresa.id)
    messages.success(request, "Produto criado com sucesso.")
    return redirect("produtos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_produto_modulo(request, empresa_id, produto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")

    produto = Produto.objects.filter(id=produto_id, empresa=empresa).first()
    if not produto:
        messages.error(request, "Produto nao encontrado.")
        return redirect("produtos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_produto_por_dados(produto, request.POST, empresa)
        if erro:
            messages.error(request, erro)
            return redirect("editar_produto_modulo", empresa_id=empresa.id, produto_id=produto.id)
        messages.success(request, "Produto atualizado com sucesso.")
        return redirect("produtos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "produto": produto,
    }
    return render(request, "parametros/produto_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_produto_modulo(request, empresa_id, produto_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Produtos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("produtos", empresa_id=empresa.id)

    produto = Produto.objects.filter(id=produto_id, empresa=empresa).first()
    if not produto:
        messages.error(request, "Produto nao encontrado.")
        return redirect("produtos", empresa_id=empresa.id)
    produto.excluir_produto()
    messages.success(request, "Produto excluido com sucesso.")
    return redirect("produtos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def unidades_federativas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")

    unidades_qs = UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo")
    unidades_tabulator = build_unidades_federativas_tabulator(unidades_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "unidades_federativas": unidades_qs,
        "unidades_federativas_tabulator": unidades_tabulator,
    }
    return render(request, "parametros/unidades_federativas.html", contexto)


@login_required(login_url="entrar")
def criar_unidade_federativa_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    erro = criar_unidade_federativa_por_dados(
        empresa,
        request.POST.get("codigo"),
        request.POST.get("sigla"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("unidades_federativas", empresa_id=empresa.id)
    messages.success(request, "Unidade federativa criada com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_unidade_federativa_modulo(request, empresa_id, unidade_federativa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa = UnidadeFederativa.objects.filter(id=unidade_federativa_id, empresa=empresa).first()
    if not unidade_federativa:
        messages.error(request, "Unidade federativa nao encontrada.")
        return redirect("unidades_federativas", empresa_id=empresa.id)

    erro = atualizar_unidade_federativa_por_dados(
        unidade_federativa,
        request.POST.get("codigo"),
        request.POST.get("sigla"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("unidades_federativas", empresa_id=empresa.id)
    messages.success(request, "Unidade federativa atualizada com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_unidade_federativa_modulo(request, empresa_id, unidade_federativa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Unidades Federativas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa = UnidadeFederativa.objects.filter(id=unidade_federativa_id, empresa=empresa).first()
    if not unidade_federativa:
        messages.error(request, "Unidade federativa nao encontrada.")
        return redirect("unidades_federativas", empresa_id=empresa.id)

    unidade_federativa.excluir_unidade_federativa()
    messages.success(request, "Unidade federativa excluida com sucesso.")
    return redirect("unidades_federativas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def motoristas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")

    motoristas_qs = Motorista.objects.filter(empresa=empresa).order_by("nome")
    motoristas_tabulator = build_motoristas_tabulator(motoristas_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "motoristas_tabulator": motoristas_tabulator,
    }
    return render(request, "parametros/motoristas.html", contexto)


@login_required(login_url="entrar")
def criar_motorista_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    erro = criar_motorista_por_dados(
        empresa,
        request.POST.get("codigo_motorista"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista criado com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_motorista_modulo(request, empresa_id, motorista_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    motorista = Motorista.objects.filter(id=motorista_id, empresa=empresa).first()
    if not motorista:
        messages.error(request, "Motorista não encontrado.")
        return redirect("motoristas", empresa_id=empresa.id)

    erro = atualizar_motorista_por_dados(
        motorista,
        request.POST.get("codigo_motorista"),
        request.POST.get("nome"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista atualizado com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_motorista_modulo(request, empresa_id, motorista_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Motoristas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("motoristas", empresa_id=empresa.id)

    motorista = Motorista.objects.filter(id=motorista_id, empresa=empresa).first()
    if not motorista:
        messages.error(request, "Motorista não encontrado.")
        return redirect("motoristas", empresa_id=empresa.id)

    try:
        motorista.excluir_motorista()
    except ProtectedError:
        messages.error(request, "Não é possível excluir o motorista porque há agendas vinculadas.")
        return redirect("motoristas", empresa_id=empresa.id)
    messages.success(request, "Motorista excluído com sucesso.")
    return redirect("motoristas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def transportadoras(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")

    transportadoras_qs = Transportadora.objects.filter(empresa=empresa).order_by("nome")
    transportadoras_tabulator = build_transportadoras_tabulator(transportadoras_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "transportadoras_tabulator": transportadoras_tabulator,
    }
    return render(request, "parametros/transportadoras.html", contexto)


@login_required(login_url="entrar")
def criar_transportadora_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    erro = criar_transportadora_por_dados(
        empresa,
        request.POST.get("codigo_transportadora"),
        request.POST.get("nome"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora criada com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_transportadora_modulo(request, empresa_id, transportadora_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    transportadora = Transportadora.objects.filter(id=transportadora_id, empresa=empresa).first()
    if not transportadora:
        messages.error(request, "Transportadora não encontrada.")
        return redirect("transportadoras", empresa_id=empresa.id)

    erro = atualizar_transportadora_por_dados(
        transportadora,
        request.POST.get("codigo_transportadora"),
        request.POST.get("nome"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora atualizada com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_transportadora_modulo(request, empresa_id, transportadora_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Transportadoras")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("transportadoras", empresa_id=empresa.id)

    transportadora = Transportadora.objects.filter(id=transportadora_id, empresa=empresa).first()
    if not transportadora:
        messages.error(request, "Transportadora não encontrada.")
        return redirect("transportadoras", empresa_id=empresa.id)

    try:
        transportadora.excluir_transportadora()
    except ProtectedError:
        messages.error(request, "Não é possível excluir a transportadora porque há agendas vinculadas.")
        return redirect("transportadoras", empresa_id=empresa.id)
    messages.success(request, "Transportadora excluída com sucesso.")
    return redirect("transportadoras", empresa_id=empresa.id)


@login_required(login_url="entrar")
def titulos(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")

    titulos_qs = Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo")
    titulos_tabulator = build_titulos_tabulator(titulos_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "titulos": titulos_qs,
        "titulos_tabulator": titulos_tabulator,
    }
    return render(request, "financeiro/titulos.html", contexto)


@login_required(login_url="entrar")
def criar_titulo_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    erro = criar_titulo_por_dados(empresa, request.POST.get("tipo_titulo_codigo"), request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("titulos", empresa_id=empresa.id)
    messages.success(request, "Titulo criado com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_titulo_modulo(request, empresa_id, titulo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    titulo = Titulo.objects.filter(id=titulo_id, empresa=empresa).first()
    if not titulo:
        messages.error(request, "Titulo nao encontrado.")
        return redirect("titulos", empresa_id=empresa.id)

    erro = atualizar_titulo_por_dados(titulo, request.POST.get("tipo_titulo_codigo"), request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("titulos", empresa_id=empresa.id)
    messages.success(request, "Titulo atualizado com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_titulo_modulo(request, empresa_id, titulo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Titulos")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("titulos", empresa_id=empresa.id)

    titulo = Titulo.objects.filter(id=titulo_id, empresa=empresa).first()
    if not titulo:
        messages.error(request, "Titulo nao encontrado.")
        return redirect("titulos", empresa_id=empresa.id)
    titulo.excluir_titulo()
    messages.success(request, "Titulo excluido com sucesso.")
    return redirect("titulos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def naturezas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")

    naturezas_qs = Natureza.objects.filter(empresa=empresa).order_by("codigo")
    naturezas_tabulator = build_naturezas_tabulator(naturezas_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "naturezas": naturezas_qs,
        "naturezas_tabulator": naturezas_tabulator,
    }
    return render(request, "financeiro/naturezas.html", contexto)


@login_required(login_url="entrar")
def criar_natureza_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    erro = criar_natureza_por_dados(empresa, request.POST.get("codigo"), request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("naturezas", empresa_id=empresa.id)
    messages.success(request, "Natureza criada com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_natureza_modulo(request, empresa_id, natureza_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    natureza = Natureza.objects.filter(id=natureza_id, empresa=empresa).first()
    if not natureza:
        messages.error(request, "Natureza nao encontrada.")
        return redirect("naturezas", empresa_id=empresa.id)

    erro = atualizar_natureza_por_dados(natureza, request.POST.get("codigo"), request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("naturezas", empresa_id=empresa.id)
    messages.success(request, "Natureza atualizada com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_natureza_modulo(request, empresa_id, natureza_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Naturezas")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("naturezas", empresa_id=empresa.id)

    natureza = Natureza.objects.filter(id=natureza_id, empresa=empresa).first()
    if not natureza:
        messages.error(request, "Natureza nao encontrada.")
        return redirect("naturezas", empresa_id=empresa.id)
    natureza.excluir_natureza()
    messages.success(request, "Natureza excluida com sucesso.")
    return redirect("naturezas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def operacoes(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")

    operacoes_qs = Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo")
    operacoes_tabulator = build_operacoes_tabulator(operacoes_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "operacoes": operacoes_qs,
        "operacoes_tabulator": operacoes_tabulator,
    }
    return render(request, "financeiro/operacoes.html", contexto)


@login_required(login_url="entrar")
def criar_operacao_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    erro = criar_operacao_por_dados(
        empresa,
        request.POST.get("tipo_operacao_codigo"),
        request.POST.get("descricao_receita_despesa"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("operacoes", empresa_id=empresa.id)
    messages.success(request, "Operacao criada com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_operacao_modulo(request, empresa_id, operacao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    operacao = Operacao.objects.filter(id=operacao_id, empresa=empresa).first()
    if not operacao:
        messages.error(request, "Operacao nao encontrada.")
        return redirect("operacoes", empresa_id=empresa.id)

    erro = atualizar_operacao_por_dados(
        operacao,
        request.POST.get("tipo_operacao_codigo"),
        request.POST.get("descricao_receita_despesa"),
        empresa,
    )
    if erro:
        messages.error(request, erro)
        return redirect("operacoes", empresa_id=empresa.id)
    messages.success(request, "Operacao atualizada com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_operacao_modulo(request, empresa_id, operacao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Operacoes")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("operacoes", empresa_id=empresa.id)

    operacao = Operacao.objects.filter(id=operacao_id, empresa=empresa).first()
    if not operacao:
        messages.error(request, "Operacao nao encontrada.")
        return redirect("operacoes", empresa_id=empresa.id)
    operacao.excluir_operacao()
    messages.success(request, "Operacao excluida com sucesso.")
    return redirect("operacoes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def centros_resultado(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")

    centros_qs = CentroResultado.objects.filter(empresa=empresa).order_by("descricao")
    centros_tabulator = build_centros_resultado_tabulator(centros_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "centros_resultado": centros_qs,
        "centros_resultado_tabulator": centros_tabulator,
    }
    return render(request, "financeiro/centros_resultado.html", contexto)


@login_required(login_url="entrar")
def criar_centro_resultado_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    erro = criar_centro_resultado_por_dados(empresa, request.POST.get("descricao"))
    if erro:
        messages.error(request, erro)
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado criado com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_centro_resultado_modulo(request, empresa_id, centro_resultado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    centro_resultado = CentroResultado.objects.filter(id=centro_resultado_id, empresa=empresa).first()
    if not centro_resultado:
        messages.error(request, "Centro resultado nao encontrado.")
        return redirect("centros_resultado", empresa_id=empresa.id)

    erro = atualizar_centro_resultado_por_dados(centro_resultado, request.POST.get("descricao"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado atualizado com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_centro_resultado_modulo(request, empresa_id, centro_resultado_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Centro Resultado")
    if not autorizado:
        return redirect("index")
    if request.method != "POST":
        return redirect("centros_resultado", empresa_id=empresa.id)

    centro_resultado = CentroResultado.objects.filter(id=centro_resultado_id, empresa=empresa).first()
    if not centro_resultado:
        messages.error(request, "Centro resultado nao encontrado.")
        return redirect("centros_resultado", empresa_id=empresa.id)
    try:
        centro_resultado.excluir_centro_resultado()
    except ProtectedError:
        messages.error(
            request,
            "Nao e possivel excluir este centro de resultado porque ele esta vinculado a Orcamentos Realizados.",
        )
        return redirect("centros_resultado", empresa_id=empresa.id)
    messages.success(request, "Centro resultado excluido com sucesso.")
    return redirect("centros_resultado", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_dfc_modulo(request, empresa_id, dfc_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "DFC")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "dfc")
    if bloqueio:
        return bloqueio

    dfc_item = FluxoDeCaixaDFC.objects.filter(id=dfc_id, empresa=empresa).first()
    if not dfc_item:
        messages.error(request, "Registro DFC nao encontrado.")
        return redirect("dfc", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_dfc_por_post(dfc_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_dfc_modulo", empresa_id=empresa.id, dfc_id=dfc_item.id)
        messages.success(request, "Registro DFC atualizado com sucesso.")
        return redirect("dfc", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "dfc_item": dfc_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "financeiro/dfc_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_dfc_modulo(request, empresa_id, dfc_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "DFC")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("dfc", empresa_id=empresa.id)

    dfc_item = FluxoDeCaixaDFC.objects.filter(id=dfc_id, empresa=empresa).first()
    if not dfc_item:
        messages.error(request, "Registro DFC nao encontrado.")
        return redirect("dfc", empresa_id=empresa.id)
    dfc_item.excluir_fluxo_de_caixa_dfc()
    messages.success(request, "Registro DFC excluido com sucesso.")
    return redirect("dfc", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_faturamento_modulo(request, empresa_id, faturamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Faturamento")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "faturamento")
    if bloqueio:
        return bloqueio

    faturamento_item = Faturamento.objects.filter(id=faturamento_id, empresa=empresa).first()
    if not faturamento_item:
        messages.error(request, "Registro de Faturamento nao encontrado.")
        return redirect("faturamento", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_faturamento_por_post(faturamento_item, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect(
                "editar_faturamento_modulo",
                empresa_id=empresa.id,
                faturamento_id=faturamento_item.id,
            )
        messages.success(request, "Registro de Faturamento atualizado com sucesso.")
        return redirect("faturamento", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "faturamento_item": faturamento_item,
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("descricao_receita_despesa"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("descricao"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
        "produtos": Produto.objects.filter(empresa=empresa).order_by("descricao_produto"),
    }
    return render(request, "administrativo/faturamento_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_faturamento_modulo(request, empresa_id, faturamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Faturamento")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("faturamento", empresa_id=empresa.id)

    faturamento_item = Faturamento.objects.filter(id=faturamento_id, empresa=empresa).first()
    if not faturamento_item:
        messages.error(request, "Registro de Faturamento nao encontrado.")
        return redirect("faturamento", empresa_id=empresa.id)

    faturamento_item.excluir_faturamento()
    messages.success(request, "Registro de Faturamento excluido com sucesso.")
    return redirect("faturamento", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_adiantamento_modulo(request, empresa_id, adiantamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Adiantamentos")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "adiantamentos")
    if bloqueio:
        return bloqueio

    adiantamento_item = Adiantamento.objects.filter(id=adiantamento_id, empresa=empresa).first()
    if not adiantamento_item:
        messages.error(request, "Registro de Adiantamentos nao encontrado.")
        return redirect("adiantamentos", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_adiantamento_por_post(adiantamento_item, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_adiantamento_modulo", empresa_id=empresa.id, adiantamento_id=adiantamento_item.id)
        messages.success(request, "Registro de Adiantamentos atualizado com sucesso.")
        return redirect("adiantamentos", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "adiantamento_item": adiantamento_item,
    }
    return render(request, "financeiro/adiantamentos_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_adiantamento_modulo(request, empresa_id, adiantamento_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Adiantamentos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("adiantamentos", empresa_id=empresa.id)

    adiantamento_item = Adiantamento.objects.filter(id=adiantamento_id, empresa=empresa).first()
    if not adiantamento_item:
        messages.error(request, "Registro de Adiantamentos nao encontrado.")
        return redirect("adiantamentos", empresa_id=empresa.id)
    adiantamento_item.excluir_adiantamento()
    messages.success(request, "Registro de Adiantamentos excluido com sucesso.")
    return redirect("adiantamentos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_contas_a_receber_modulo(request, empresa_id, conta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas a Receber")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "contas_a_receber")
    if bloqueio:
        return bloqueio

    conta_item = ContasAReceber.objects.filter(id=conta_id, empresa=empresa).first()
    if not conta_item:
        messages.error(request, "Registro de Contas a Receber nao encontrado.")
        return redirect("contas_a_receber", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_contas_a_receber_por_post(conta_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_contas_a_receber_modulo", empresa_id=empresa.id, conta_id=conta_item.id)
        messages.success(request, "Registro de Contas a Receber atualizado com sucesso.")
        return redirect("contas_a_receber", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "conta_item": conta_item,
        "titulos": Titulo.objects.filter(empresa=empresa).order_by("tipo_titulo_codigo"),
        "naturezas": Natureza.objects.filter(empresa=empresa).order_by("codigo"),
        "operacoes": Operacao.objects.filter(empresa=empresa).order_by("tipo_operacao_codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "centros_resultado": CentroResultado.objects.filter(empresa=empresa).order_by("descricao"),
    }
    return render(request, "financeiro/contas_a_receber_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_contas_a_receber_modulo(request, empresa_id, conta_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Contas a Receber")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("contas_a_receber", empresa_id=empresa.id)

    conta_item = ContasAReceber.objects.filter(id=conta_id, empresa=empresa).first()
    if not conta_item:
        messages.error(request, "Registro de Contas a Receber nao encontrado.")
        return redirect("contas_a_receber", empresa_id=empresa.id)
    conta_item.excluir_conta_a_receber()
    messages.success(request, "Registro de Contas a Receber excluido com sucesso.")
    return redirect("contas_a_receber", empresa_id=empresa.id)


@login_required(login_url="entrar")
def carteira(request, empresa_id):
    # 1) Autorizacao
    modulo = _obter_modulo("Comercial", "Carteira")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_carteira(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_carteira"},
        ):
            return redirect("carteira", empresa_id=empresa_id)
        if acao == "criar_carteira":
            erro = criar_carteira_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Carteira criada com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_carteira")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_carteira(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("carteira", empresa_id=empresa_id)

    # 2) Query
    carteiras_qs = (
        Carteira.objects.filter(empresa=empresa)
        .annotate(
            valor_faturado_num=Cast("valor_faturado", FloatField()),
            limite_credito_num=Cast("limite_credito", FloatField()),
        )
        .values(
            "id",
            "parceiro__nome",
            "parceiro__codigo",
            "gerente",
            "vendedor",
            "valor_faturado_num",
            "limite_credito_num",
            "ultima_venda",
            "descricao_perfil",
            "ativo_indicador",
            "cliente_indicador",
            "fornecedor_indicador",
            "transporte_indicador",
            "data_cadastro",
            "regiao__nome",
            "regiao__codigo",
            "cidade__nome",
            "cidade__codigo",
        )
        .order_by("-id")
    )
    carteiras_dashboard_qs = (
        Carteira.objects.filter(empresa=empresa, data_cadastro__isnull=False)
        .values("data_cadastro", "valor_faturado")
    )

    arquivos_existentes = [f.name for f in diretorio_importacao.iterdir() if f.is_file()]
    cidades = Cidade.objects.filter(empresa=empresa).order_by("nome")
    regioes = Regiao.objects.filter(empresa=empresa).order_by("nome")
    parceiros = Parceiro.objects.filter(empresa=empresa).order_by("nome")
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="carteira",
        empresa_id=empresa.id,
        extensoes={".xlsx"},
    )

    # 3) Transformacao
    contexto = montar_contexto_carteira(
        empresa=empresa,
        modulo_nome=modulo["nome"],
        arquivo_existente=arquivo_existente_texto,
        tem_arquivo_existente=tem_arquivo_existente,
        carteiras_qs=carteiras_qs,
        cidades=cidades,
        regioes=regioes,
        parceiros=parceiros,
        carteiras_dashboard_qs=carteiras_dashboard_qs,
        permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
    )
    contexto["bloquear_cadastro_edicao_importacao"] = _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    contexto["tipo_importacao_texto"] = TIPO_IMPORTACAO_POR_MODULO["carteira"]
    contexto["resumo_importacao"] = resumo_importacao

    # 4) Render
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_carteira_modulo(request, empresa_id, carteira_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Carteira")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "carteira")
    if bloqueio:
        return bloqueio

    carteira_item = Carteira.objects.filter(id=carteira_id, empresa=empresa).first()
    if not carteira_item:
        messages.error(request, "Carteira nao encontrada.")
        return redirect("carteira", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_carteira_por_post(carteira_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_carteira_modulo", empresa_id=empresa.id, carteira_id=carteira_item.id)
        messages.success(request, "Carteira atualizada com sucesso.")
        return redirect("carteira", empresa_id=empresa.id)

    cidades = Cidade.objects.filter(empresa=empresa).order_by("nome")
    regioes = Regiao.objects.filter(empresa=empresa).order_by("nome")
    parceiros = Parceiro.objects.filter(empresa=empresa).order_by("nome")
    contexto = {
        "empresa": empresa,
        "carteira": carteira_item,
        "cidades": cidades,
        "regioes": regioes,
        "parceiros": parceiros,
    }
    return render(request, "comercial/carteira_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_carteira_modulo(request, empresa_id, carteira_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Carteira")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("carteira", empresa_id=empresa.id)

    carteira_item = Carteira.objects.filter(id=carteira_id, empresa=empresa).first()
    if not carteira_item:
        messages.error(request, "Carteira nao encontrada.")
        return redirect("carteira", empresa_id=empresa.id)

    carteira_item.excluir_carteira()
    messages.success(request, "Carteira excluida com sucesso.")
    return redirect("carteira", empresa_id=empresa.id)


@login_required(login_url="entrar")
def cidades(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cidades")
    if not autorizado:
        return redirect("index")

    cidades_qs = Cidade.objects.filter(empresa=empresa).order_by("nome")
    cidades_tabulator = build_cidades_tabulator(cidades_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "cidades": cidades_qs,
        "cidades_tabulator": cidades_tabulator,
    }
    return render(request, "comercial/cidades.html", contexto)


@login_required(login_url="entrar")
def criar_cidade_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cidades")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("cidades", empresa_id=empresa.id)

    erro = criar_cidade_por_dados(empresa, request.POST.get("nome"), request.POST.get("codigo"))
    if erro:
        messages.error(request, erro)
        return redirect("cidades", empresa_id=empresa.id)
    messages.success(request, "Cidade criada com sucesso.")
    return redirect("cidades", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_cidade_modulo(request, empresa_id, cidade_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cidades")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("cidades", empresa_id=empresa.id)

    cidade = Cidade.objects.filter(id=cidade_id, empresa=empresa).first()
    if not cidade:
        messages.error(request, "Cidade nao encontrada.")
        return redirect("cidades", empresa_id=empresa.id)

    erro = atualizar_cidade_por_dados(cidade, request.POST.get("nome"), request.POST.get("codigo"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("cidades", empresa_id=empresa.id)
    messages.success(request, "Cidade atualizada com sucesso.")
    return redirect("cidades", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_cidade_modulo(request, empresa_id, cidade_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cidades")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("cidades", empresa_id=empresa.id)

    cidade = Cidade.objects.filter(id=cidade_id, empresa=empresa).first()
    if not cidade:
        messages.error(request, "Cidade nao encontrada.")
        return redirect("cidades", empresa_id=empresa.id)

    cidade.excluir_cidade()
    messages.success(request, "Cidade excluida com sucesso.")
    return redirect("cidades", empresa_id=empresa.id)


@login_required(login_url="entrar")
def regioes(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Regioes")
    if not autorizado:
        return redirect("index")

    regioes_qs = Regiao.objects.filter(empresa=empresa).order_by("nome")
    regioes_tabulator = build_regioes_tabulator(regioes_qs, empresa.id)
    contexto = {
        "empresa": empresa,
        "regioes": regioes_qs,
        "regioes_tabulator": regioes_tabulator,
    }
    return render(request, "comercial/regioes.html", contexto)


@login_required(login_url="entrar")
def criar_regiao_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Regioes")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("regioes", empresa_id=empresa.id)

    erro = criar_regiao_por_dados(empresa, request.POST.get("nome"), request.POST.get("codigo"))
    if erro:
        messages.error(request, erro)
        return redirect("regioes", empresa_id=empresa.id)
    messages.success(request, "Região criada com sucesso.")
    return redirect("regioes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_regiao_modulo(request, empresa_id, regiao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Regioes")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("regioes", empresa_id=empresa.id)

    regiao = Regiao.objects.filter(id=regiao_id, empresa=empresa).first()
    if not regiao:
        messages.error(request, "Região não encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    erro = atualizar_regiao_por_dados(regiao, request.POST.get("nome"), request.POST.get("codigo"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("regioes", empresa_id=empresa.id)
    messages.success(request, "Região atualizada com sucesso.")
    return redirect("regioes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_regiao_modulo(request, empresa_id, regiao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Regioes")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("regioes", empresa_id=empresa.id)

    regiao = Regiao.objects.filter(id=regiao_id, empresa=empresa).first()
    if not regiao:
        messages.error(request, "Região não encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    regiao.excluir_regiao()
    messages.success(request, "Região excluída com sucesso.")
    return redirect("regioes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def rotas(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    rotas_qs = Rota.objects.filter(empresa=empresa).select_related("uf").order_by("nome")
    ufs_qs = UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo")
    contexto = {
        "empresa": empresa,
        "rotas_tabulator": build_rotas_tabulator(rotas_qs, empresa.id),
        "unidades_federativas": ufs_qs,
        "unidades_federativas_js": list(ufs_qs.values("id", "codigo", "sigla")),
    }
    return render(request, "parametros/rotas.html", contexto)


@login_required(login_url="entrar")
def criar_rota_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    erro = criar_rota_por_dados(
        empresa,
        request.POST.get("codigo_rota"),
        request.POST.get("nome"),
        request.POST.get("uf_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("rotas", empresa_id=empresa.id)
    messages.success(request, "Rota criada com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_rota_modulo(request, empresa_id, rota_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    rota = Rota.objects.filter(id=rota_id, empresa=empresa).first()
    if not rota:
        messages.error(request, "Rota não encontrada.")
        return redirect("rotas", empresa_id=empresa.id)

    erro = atualizar_rota_por_dados(
        rota,
        request.POST.get("codigo_rota"),
        request.POST.get("nome"),
        empresa,
        request.POST.get("uf_id"),
    )
    if erro:
        messages.error(request, erro)
        return redirect("rotas", empresa_id=empresa.id)
    messages.success(request, "Rota atualizada com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_rota_modulo(request, empresa_id, rota_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Rotas")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("rotas", empresa_id=empresa.id)

    rota = Rota.objects.filter(id=rota_id, empresa=empresa).first()
    if not rota:
        messages.error(request, "Rota não encontrada.")
        return redirect("rotas", empresa_id=empresa.id)

    rota.excluir_rota()
    messages.success(request, "Rota excluída com sucesso.")
    return redirect("rotas", empresa_id=empresa.id)


@login_required(login_url="entrar")
def pedidos_pendentes(request, empresa_id):
    modulo = _obter_modulo("Comercial", "Pedidos Pendentes")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_pedidos_pendentes(empresa)

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_pedido_pendente"},
        ):
            return redirect("pedidos_pendentes", empresa_id=empresa.id)
        if acao == "criar_pedido_pendente":
            erro = criar_pedido_pendente_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Pedido pendente criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_pedidos_pendentes")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_pedidos_pendentes(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    pedidos_qs = (
        PedidoPendente.objects.filter(empresa=empresa)
        .select_related("rota", "regiao", "parceiro")
        .order_by("-id")
    )
    numeros_unicos = {
        _normalizar_numero_unico_texto(valor)
        for valor in pedidos_qs.values_list("numero_unico", flat=True)
        if _normalizar_numero_unico_texto(valor)
    }
    agendas_por_numero = {}
    agendas_qs = (
        Agenda.objects.filter(empresa=empresa)
        .select_related("motorista", "transportadora")
        .order_by("-id")
    )
    for agenda_item in agendas_qs:
        chave_numero = _normalizar_numero_unico_texto(agenda_item.numero_unico)
        if chave_numero and chave_numero not in agendas_por_numero:
            agendas_por_numero[chave_numero] = agenda_item
    parceiro_ids = set(
        pedidos_qs.filter(parceiro_id__isnull=False).values_list("parceiro_id", flat=True)
    )
    gerentes_por_parceiro = {}
    carteiras_qs = (
        Carteira.objects.filter(empresa=empresa, parceiro_id__in=parceiro_ids)
        .exclude(gerente="")
        .exclude(gerente__iexact="<SEM VENDEDOR>")
        .exclude(gerente__iexact="SEM VENDEDOR")
        .exclude(gerente__iexact="<SEM GERENTE>")
        .exclude(gerente__iexact="SEM GERENTE")
        .select_related("parceiro")
        .order_by("parceiro_id", "-data_cadastro", "-id")
    )
    for carteira_item in carteiras_qs:
        if carteira_item.parceiro_id not in gerentes_por_parceiro:
            gerente = _gerente_valido_ou_vazio(carteira_item.gerente)
            if gerente:
                gerentes_por_parceiro[carteira_item.parceiro_id] = gerente

    gerentes_opcoes = set(gerentes_por_parceiro.values())
    for gerente_valor in pedidos_qs.values_list("gerente", flat=True):
        gerente_limpo = _gerente_valido_ou_vazio(gerente_valor)
        if gerente_limpo:
            gerentes_opcoes.add(gerente_limpo)
    gerentes_opcoes = sorted(gerentes_opcoes, key=lambda item: item.lower())

    arquivos_existentes = [f.name for f in diretorio_importacao.iterdir() if f.is_file()]
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="pedidos_pendentes",
        empresa_id=empresa.id,
        extensoes={".xlsx"},
    )
    pedidos_tabulator = build_pedidos_pendentes_tabulator(
        pedidos_qs,
        empresa.id,
        agendas_por_numero=agendas_por_numero,
        gerentes_por_parceiro=gerentes_por_parceiro,
        permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
    )
    total_pedidos = len(pedidos_tabulator)
    total_atrasados = sum(1 for item in pedidos_tabulator if item.get("status") == "Atrasado")
    total_atencao = sum(1 for item in pedidos_tabulator if item.get("status") == "Atenção")
    total_no_prazo = total_pedidos - total_atrasados - total_atencao

    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["pedidos_pendentes"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "rotas": Rota.objects.filter(empresa=empresa).order_by("codigo_rota", "nome"),
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("codigo", "nome"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("codigo", "nome"),
        "gerentes_opcoes": gerentes_opcoes,
        "pedidos_pendentes_tabulator": pedidos_tabulator,
        "dashboard_total_pedidos": total_pedidos,
        "dashboard_atrasados": total_atrasados,
        "dashboard_atencao": total_atencao,
        "dashboard_no_prazo": total_no_prazo,
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_pedido_pendente_modulo(request, empresa_id, pedido_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Pedidos Pendentes")
    if not permitido:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "pedidos_pendentes")
    if bloqueio:
        return bloqueio

    pedido = (
        PedidoPendente.objects.filter(id=pedido_id, empresa=empresa)
        .select_related("rota", "regiao", "parceiro")
        .first()
    )
    if not pedido:
        messages.error(request, "Pedido pendente não encontrado.")
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_pedido_pendente_por_post(pedido, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_pedido_pendente_modulo", empresa_id=empresa.id, pedido_id=pedido.id)
        messages.success(request, "Pedido pendente atualizado com sucesso.")
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "pedido": pedido,
        "rotas": Rota.objects.filter(empresa=empresa).order_by("codigo_rota"),
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("codigo"),
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("nome"),
        "gerentes_opcoes": sorted(
            {
                gerente
                for gerente in [
                    *Carteira.objects.filter(empresa=empresa).values_list("gerente", flat=True),
                    *PedidoPendente.objects.filter(empresa=empresa).values_list("gerente", flat=True),
                ]
                for gerente in [_gerente_valido_ou_vazio(gerente)]
                if gerente
            }
            | ({_gerente_valido_ou_vazio(pedido.gerente)} if _gerente_valido_ou_vazio(pedido.gerente) else set()),
            key=lambda item: item.lower(),
        ),
    }
    return render(request, "comercial/pedidos_pendentes_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_pedido_pendente_modulo(request, empresa_id, pedido_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Pedidos Pendentes")
    if not permitido:
        return redirect("index")

    if request.method != "POST":
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    pedido = PedidoPendente.objects.filter(id=pedido_id, empresa=empresa).first()
    if not pedido:
        messages.error(request, "Pedido pendente não encontrado.")
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    pedido.excluir_pedido_pendente()
    messages.success(request, "Pedido pendente excluído com sucesso.")
    return redirect("pedidos_pendentes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def agenda(request, empresa_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Pedidos Pendentes")
    if not permitido:
        return redirect("index")

    if request.method == "POST":
        erro = criar_agenda_por_post(empresa, request.POST)
        if erro:
            messages.error(request, erro)
        else:
            messages.success(request, "Agenda criada com sucesso.")
        return redirect("agenda", empresa_id=empresa.id)

    agenda_qs = (
        Agenda.objects.filter(empresa=empresa)
        .select_related("motorista", "transportadora")
        .order_by("-data_registro", "-id")
    )
    numero_unico_prefill = _normalizar_numero_unico_texto(request.GET.get("numero_unico"))
    contexto = {
        "empresa": empresa,
        "numero_unico_prefill": numero_unico_prefill,
        "motoristas": Motorista.objects.filter(empresa=empresa).order_by("nome"),
        "transportadoras": Transportadora.objects.filter(empresa=empresa).order_by("nome"),
        "agenda_tabulator": build_agenda_tabulator(agenda_qs, empresa.id),
    }
    return render(request, "comercial/agenda.html", contexto)


@login_required(login_url="entrar")
def editar_agenda_modulo(request, empresa_id, agenda_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Pedidos Pendentes")
    if not permitido:
        return redirect("index")

    agenda_item = (
        Agenda.objects.filter(id=agenda_id, empresa=empresa)
        .select_related("motorista", "transportadora")
        .first()
    )
    if not agenda_item:
        messages.error(request, "Agenda não encontrada.")
        return redirect("agenda", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_agenda_por_post(agenda_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_agenda_modulo", empresa_id=empresa.id, agenda_id=agenda_item.id)
        messages.success(request, "Agenda atualizada com sucesso.")
        return redirect("agenda", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "agenda_item": agenda_item,
        "motoristas": Motorista.objects.filter(empresa=empresa).order_by("nome"),
        "transportadoras": Transportadora.objects.filter(empresa=empresa).order_by("nome"),
    }
    return render(request, "comercial/agenda_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_agenda_modulo(request, empresa_id, agenda_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Pedidos Pendentes")
    if not permitido:
        return redirect("index")

    if request.method != "POST":
        return redirect("agenda", empresa_id=empresa.id)

    agenda_item = Agenda.objects.filter(id=agenda_id, empresa=empresa).first()
    if not agenda_item:
        messages.error(request, "Agenda não encontrada.")
        return redirect("agenda", empresa_id=empresa.id)

    agenda_item.excluir_agenda()
    messages.success(request, "Agenda excluída com sucesso.")
    return redirect("agenda", empresa_id=empresa.id)


@login_required(login_url="entrar")
def vendas_por_categoria(request, empresa_id):
    modulo = _obter_modulo("Comercial", "Vendas por Categoria")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_venda"},
        ):
            return redirect("vendas_por_categoria", empresa_id=empresa_id)
        if acao == "criar_venda":
            erro = criar_venda_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Venda criada com sucesso.")
        elif acao == "importar_vendas":
            arquivos = request.FILES.getlist("arquivos_vendas")
            ok, mensagem = importar_upload_vendas(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.error(request, "Acao de vendas invalida.")
        return redirect("vendas_por_categoria", empresa_id=empresa_id)

    vendas_qs = (
        Venda.objects.filter(empresa=empresa)
        .annotate(
            valor_venda_num=Cast("valor_venda", FloatField()),
            custo_medio_icms_cmv_num=Cast("custo_medio_icms_cmv", FloatField()),
            lucro_num=Cast("lucro", FloatField()),
            peso_bruto_num=Cast("peso_bruto", FloatField()),
            peso_liquido_num=Cast("peso_liquido", FloatField()),
            margem_num=Cast("margem", FloatField()),
        )
        .values(
            "id",
            "codigo",
            "descricao",
            "valor_venda_num",
            "qtd_notas",
            "custo_medio_icms_cmv_num",
            "lucro_num",
            "peso_bruto_num",
            "peso_liquido_num",
            "margem_num",
            "data_venda",
        )
        .order_by("-data_venda", "-id")
    )

    arquivos_existentes = sorted(
        [f.name for f in diretorio_importacao.iterdir() if f.is_file() and f.suffix.lower() == ".xls"]
    )
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="vendas_por_categoria",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )

    contexto = montar_contexto_vendas(
        empresa=empresa,
        modulo_nome=modulo["nome"],
        arquivo_existente=arquivo_existente_texto,
        tem_arquivo_existente=tem_arquivo_existente,
        vendas_qs=vendas_qs,
        permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
    )
    contexto["bloquear_cadastro_edicao_importacao"] = _empresa_bloqueia_cadastro_edicao_importacao(empresa)
    contexto["tipo_importacao_texto"] = TIPO_IMPORTACAO_POR_MODULO["vendas_por_categoria"]
    contexto["resumo_importacao"] = resumo_importacao
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_venda_modulo(request, empresa_id, venda_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Vendas por Categoria")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "vendas_por_categoria")
    if bloqueio:
        return bloqueio

    venda_item = Venda.objects.filter(id=venda_id, empresa=empresa).first()
    if not venda_item:
        messages.error(request, "Venda nao encontrada.")
        return redirect("vendas_por_categoria", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_venda_por_post(venda_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_venda_modulo", empresa_id=empresa.id, venda_id=venda_item.id)
        messages.success(request, "Venda atualizada com sucesso.")
        return redirect("vendas_por_categoria", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "venda": venda_item,
    }
    return render(request, "comercial/vendas_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_venda_modulo(request, empresa_id, venda_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Vendas por Categoria")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("vendas_por_categoria", empresa_id=empresa.id)

    venda_item = Venda.objects.filter(id=venda_id, empresa=empresa).first()
    if not venda_item:
        messages.error(request, "Venda nao encontrada.")
        return redirect("vendas_por_categoria", empresa_id=empresa.id)

    venda_item.excluir_venda()
    messages.success(request, "Venda excluida com sucesso.")
    return redirect("vendas_por_categoria", empresa_id=empresa.id)


@login_required(login_url="entrar")
def precificacao(request, empresa_id):
    modulo = _obter_modulo("Comercial", "Precificacao")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def controle_de_margem(request, empresa_id):
    modulo = _obter_modulo("Comercial", "Controle de Margem")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_controle_margem(empresa)

    if request.method == "POST":
        acao = (request.POST.get("acao") or "").strip()
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_controle_margem"},
        ):
            return redirect("controle_de_margem", empresa_id=empresa.id)
        if acao == "criar_controle_margem":
            erro = criar_controle_margem_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Controle de margem criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_controle_margem")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_controle_margem(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("controle_de_margem", empresa_id=empresa.id)

    controles_base_qs = (
        ControleMargem.objects.filter(empresa=empresa)
        .select_related("parceiro")
        .order_by("-dt_neg", "-id")
    )

    filtros_disponiveis = {
        "descricao_perfil": sorted(
            [
                valor
                for valor in controles_base_qs.values_list("descricao_perfil", flat=True).distinct()
                if str(valor or "").strip()
            ],
            key=lambda item: item.lower(),
        ),
        "apelido_vendedor": sorted(
            [
                valor
                for valor in controles_base_qs.values_list("apelido_vendedor", flat=True).distinct()
                if str(valor or "").strip()
            ],
            key=lambda item: item.lower(),
        ),
        "nome_empresa": sorted(
            [
                valor
                for valor in controles_base_qs.values_list("nome_empresa", flat=True).distinct()
                if str(valor or "").strip()
            ],
            key=lambda item: item.lower(),
        ),
        "tipo_venda": sorted(
            [
                valor
                for valor in controles_base_qs.values_list("tipo_venda", flat=True).distinct()
                if str(valor or "").strip()
            ],
            key=lambda item: item.lower(),
        ),
    }

    situacao_param = _situacao_controle_margem_param_ou_none(request.GET.get("situacao"))
    situacao_raw = (request.GET.get("situacao") or "").strip()
    if situacao_raw and not situacao_param:
        messages.error(request, "Filtro de situacao invalido.")
        return redirect("controle_de_margem", empresa_id=empresa.id)

    descricao_perfil_selecionados = _normalizar_lista_query(request, "descricao_perfil")
    apelido_vendedor_selecionados = _normalizar_lista_query(request, "apelido_vendedor")
    nome_empresa_selecionados = _normalizar_lista_query(request, "nome_empresa")
    tipo_venda_selecionados = _normalizar_lista_query(request, "tipo_venda")

    if any(item not in filtros_disponiveis["descricao_perfil"] for item in descricao_perfil_selecionados):
        messages.error(request, "Filtro descricao_perfil invalido.")
        return redirect("controle_de_margem", empresa_id=empresa.id)
    if any(item not in filtros_disponiveis["apelido_vendedor"] for item in apelido_vendedor_selecionados):
        messages.error(request, "Filtro apelido_vendedor invalido.")
        return redirect("controle_de_margem", empresa_id=empresa.id)
    if any(item not in filtros_disponiveis["nome_empresa"] for item in nome_empresa_selecionados):
        messages.error(request, "Filtro nome_empresa invalido.")
        return redirect("controle_de_margem", empresa_id=empresa.id)
    if any(item not in filtros_disponiveis["tipo_venda"] for item in tipo_venda_selecionados):
        messages.error(request, "Filtro tipo_venda invalido.")
        return redirect("controle_de_margem", empresa_id=empresa.id)

    controles_qs = controles_base_qs
    if situacao_param:
        controles_qs = _filtrar_controle_margem_por_situacao(controles_qs, situacao_param)
    if descricao_perfil_selecionados:
        controles_qs = controles_qs.filter(descricao_perfil__in=descricao_perfil_selecionados)
    if apelido_vendedor_selecionados:
        controles_qs = controles_qs.filter(apelido_vendedor__in=apelido_vendedor_selecionados)
    if nome_empresa_selecionados:
        controles_qs = controles_qs.filter(nome_empresa__in=nome_empresa_selecionados)
    if tipo_venda_selecionados:
        controles_qs = controles_qs.filter(tipo_venda__in=tipo_venda_selecionados)

    arquivos_existentes = [f.name for f in diretorio_importacao.iterdir() if f.is_file()]
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="controle_de_margem",
        empresa_id=empresa.id,
        extensoes={".xls", ".xlsx"},
    )
    controles_tabulator = build_controle_margem_tabulator(
        controles_qs,
        empresa.id,
        permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
    )

    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["controle_de_margem"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("codigo", "nome"),
        "controle_margem_tabulator": controles_tabulator,
        "filtros_disponiveis": filtros_disponiveis,
        "filtros_aplicados": {
            "situacao": situacao_param,
            "descricao_perfil": descricao_perfil_selecionados,
            "apelido_vendedor": apelido_vendedor_selecionados,
            "nome_empresa": nome_empresa_selecionados,
            "tipo_venda": tipo_venda_selecionados,
        },
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_controle_margem_modulo(request, empresa_id, controle_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Controle de Margem")
    if not permitido:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "controle_de_margem")
    if bloqueio:
        return bloqueio

    controle = (
        ControleMargem.objects.filter(id=controle_id, empresa=empresa)
        .select_related("parceiro")
        .first()
    )
    if not controle:
        messages.error(request, "Controle de margem nao encontrado.")
        return redirect("controle_de_margem", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_controle_margem_por_post(controle, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_controle_margem_modulo", empresa_id=empresa.id, controle_id=controle.id)
        messages.success(request, "Controle de margem atualizado com sucesso.")
        return redirect("controle_de_margem", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "controle": controle,
        "parceiros": Parceiro.objects.filter(empresa=empresa).order_by("codigo", "nome"),
    }
    return render(request, "comercial/controle_de_margem_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_controle_margem_modulo(request, empresa_id, controle_id):
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Controle de Margem")
    if not permitido:
        return redirect("index")

    if request.method != "POST":
        return redirect("controle_de_margem", empresa_id=empresa.id)

    controle = ControleMargem.objects.filter(id=controle_id, empresa=empresa).first()
    if not controle:
        messages.error(request, "Controle de margem nao encontrado.")
        return redirect("controle_de_margem", empresa_id=empresa.id)

    controle.excluir_controle_margem()
    messages.success(request, "Controle de margem excluido com sucesso.")
    return redirect("controle_de_margem", empresa_id=empresa.id)


@login_required(login_url="entrar")
def cargas_em_aberto(request, empresa_id):
    modulo = _obter_modulo("Operacional", "Cargas em Aberto")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_carga"},
        ):
            return redirect("cargas_em_aberto", empresa_id=empresa_id)
        if acao == "criar_carga":
            erro = criar_carga_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Carga criada com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_cargas")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_cargas(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("cargas_em_aberto", empresa_id=empresa_id)

    cargas_qs = (
        Cargas.objects.filter(empresa=empresa)
        .select_related("regiao")
        .order_by("-id")
    )
    cargas_lista = list(cargas_qs)
    dashboard_total_cargas = len(cargas_lista)
    dashboard_fora_prazo = sum(1 for carga in cargas_lista if carga.verificacao)
    dashboard_no_prazo = dashboard_total_cargas - dashboard_fora_prazo
    arquivos_existentes = [f.name for f in diretorio_importacao.iterdir() if f.is_file()]
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="cargas_em_aberto",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )

    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["cargas_em_aberto"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("nome"),
        "dashboard_total_cargas": dashboard_total_cargas,
        "dashboard_no_prazo": dashboard_no_prazo,
        "dashboard_fora_prazo": dashboard_fora_prazo,
        "cargas_tabulator": build_cargas_tabulator(
            cargas_lista,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_carga_modulo(request, empresa_id, carga_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cargas em Aberto")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "cargas_em_aberto")
    if bloqueio:
        return bloqueio

    carga_item = Cargas.objects.filter(id=carga_id, empresa=empresa).first()
    if not carga_item:
        messages.error(request, "Carga nao encontrada.")
        return redirect("cargas_em_aberto", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_carga_por_post(carga_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_carga_modulo", empresa_id=empresa.id, carga_id=carga_item.id)
        messages.success(request, "Carga atualizada com sucesso.")
        return redirect("cargas_em_aberto", empresa_id=empresa.id)

    contexto = {
        "empresa": empresa,
        "carga": carga_item,
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("nome"),
    }
    return render(request, "operacional/cargas_em_aberto_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_carga_modulo(request, empresa_id, carga_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Cargas em Aberto")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("cargas_em_aberto", empresa_id=empresa.id)

    carga_item = Cargas.objects.filter(id=carga_id, empresa=empresa).first()
    if not carga_item:
        messages.error(request, "Carga nao encontrada.")
        return redirect("cargas_em_aberto", empresa_id=empresa.id)

    carga_item.excluir_carga()
    messages.success(request, "Carga excluida com sucesso.")
    return redirect("cargas_em_aberto", empresa_id=empresa.id)


@login_required(login_url="entrar")
def producao(request, empresa_id):
    modulo = _obter_modulo("Operacional", "Producao")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_producao(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_producao"},
        ):
            return redirect("producao", empresa_id=empresa_id)
        if acao == "criar_producao":
            erro = criar_producao_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de produção criado com sucesso.")
        elif acao == "importar_producao":
            arquivos = request.FILES.getlist("arquivos_producao")
            ok, mensagem = importar_upload_producao(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.error(request, "Ação de produção inválida.")
        return redirect("producao", empresa_id=empresa_id)

    producoes_qs = (
        Producao.objects.filter(empresa=empresa)
        .select_related("produto")
        .order_by("-id")
    )
    situacoes_producao = sorted(
        {
            str(valor).strip()
            for valor in Producao.objects.filter(empresa=empresa).values_list("situacao", flat=True)
            if str(valor).strip()
        }
    )
    if not situacoes_producao:
        situacoes_producao = ["Pendente"]

    arquivos_existentes = sorted([f.name for f in diretorio_importacao.iterdir() if f.is_file()])
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="producao",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )
    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["producao"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "produtos": Produto.objects.filter(empresa=empresa).order_by("codigo_produto"),
        "situacoes_producao_opcoes": situacoes_producao,
        "producao_tabulator": build_producao_tabulator(
            producoes_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, "operacional/producao.html", contexto)


@login_required(login_url="entrar")
def editar_producao_modulo(request, empresa_id, producao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Producao")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "producao")
    if bloqueio:
        return bloqueio

    producao_item = Producao.objects.filter(id=producao_id, empresa=empresa).select_related("produto").first()
    if not producao_item:
        messages.error(request, "Registro de produção não encontrado.")
        return redirect("producao", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_producao_por_post(producao_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_producao_modulo", empresa_id=empresa.id, producao_id=producao_item.id)
        messages.success(request, "Registro de produção atualizado com sucesso.")
        return redirect("producao", empresa_id=empresa.id)

    situacoes_producao = sorted(
        {
            str(valor).strip()
            for valor in Producao.objects.filter(empresa=empresa).values_list("situacao", flat=True)
            if str(valor).strip()
        }
    )
    if not situacoes_producao:
        situacoes_producao = ["Pendente"]
    if producao_item.situacao and producao_item.situacao not in situacoes_producao:
        situacoes_producao.append(producao_item.situacao)
        situacoes_producao.sort()

    contexto = {
        "empresa": empresa,
        "producao_item": producao_item,
        "produtos": Produto.objects.filter(empresa=empresa).order_by("codigo_produto"),
        "situacoes_producao_opcoes": situacoes_producao,
    }
    return render(request, "operacional/producao_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_producao_modulo(request, empresa_id, producao_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Producao")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("producao", empresa_id=empresa.id)

    producao_item = Producao.objects.filter(id=producao_id, empresa=empresa).first()
    if not producao_item:
        messages.error(request, "Registro de produção não encontrado.")
        return redirect("producao", empresa_id=empresa.id)

    producao_item.excluir_producao()
    messages.success(request, "Registro de produção excluído com sucesso.")
    return redirect("producao", empresa_id=empresa.id)


@login_required(login_url="entrar")
def operador_logistico(request, empresa_id):
    modulo = _obter_modulo("Operacional", "Operador Logistico")
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def tabela_de_fretes(request, empresa_id):
    modulo = _obter_modulo("Operacional", "Tabela de Fretes")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_fretes(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_frete"},
        ):
            return redirect("tabela_de_fretes", empresa_id=empresa_id)
        if acao == "criar_frete":
            erro = criar_frete_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Frete criado com sucesso.")
        else:
            arquivo = request.FILES.get("arquivo_fretes")
            confirmou_substituicao = request.POST.get("confirmar_substituicao") == "1"
            ok, mensagem = importar_upload_fretes(
                empresa=empresa,
                arquivo=arquivo,
                confirmar_substituicao=confirmou_substituicao,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        return redirect("tabela_de_fretes", empresa_id=empresa_id)

    fretes_qs = (
        Frete.objects.filter(empresa=empresa)
        .select_related("cidade", "regiao", "unidade_federativa")
        .order_by("cidade__nome", "id")
    )
    tipos_frete = sorted(
        {
            str(valor).strip()
            for valor in Frete.objects.filter(empresa=empresa).values_list("tipo_frete", flat=True)
            if str(valor).strip()
        }
    )
    if "CTRC" not in tipos_frete:
        tipos_frete.insert(0, "CTRC")
    arquivos_existentes = [f.name for f in diretorio_importacao.iterdir() if f.is_file()]
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="tabela_de_fretes",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )

    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["tabela_de_fretes"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "cidades": Cidade.objects.filter(empresa=empresa).order_by("nome"),
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("nome"),
        "unidades_federativas": UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo"),
        "tipos_frete_opcoes": tipos_frete,
        "fretes_tabulator": build_fretes_tabulator(
            fretes_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_frete_modulo(request, empresa_id, frete_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Tabela de Fretes")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "tabela_de_fretes")
    if bloqueio:
        return bloqueio

    frete_item = (
        Frete.objects.filter(id=frete_id, empresa=empresa)
        .select_related("cidade", "regiao", "unidade_federativa")
        .first()
    )
    if not frete_item:
        messages.error(request, "Frete não encontrado.")
        return redirect("tabela_de_fretes", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_frete_por_post(frete_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_frete_modulo", empresa_id=empresa.id, frete_id=frete_item.id)
        messages.success(request, "Frete atualizado com sucesso.")
        return redirect("tabela_de_fretes", empresa_id=empresa.id)

    tipos_frete = sorted(
        {
            str(valor).strip()
            for valor in Frete.objects.filter(empresa=empresa).values_list("tipo_frete", flat=True)
            if str(valor).strip()
        }
    )
    if "CTRC" not in tipos_frete:
        tipos_frete.insert(0, "CTRC")
    if frete_item.tipo_frete and frete_item.tipo_frete not in tipos_frete:
        tipos_frete.append(frete_item.tipo_frete)
        tipos_frete.sort()

    contexto = {
        "empresa": empresa,
        "frete_item": frete_item,
        "cidades": Cidade.objects.filter(empresa=empresa).order_by("nome"),
        "regioes": Regiao.objects.filter(empresa=empresa).order_by("nome"),
        "unidades_federativas": UnidadeFederativa.objects.filter(empresa=empresa).order_by("sigla", "codigo"),
        "tipos_frete_opcoes": tipos_frete,
    }
    return render(request, "operacional/tabela_de_fretes_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_frete_modulo(request, empresa_id, frete_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Tabela de Fretes")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("tabela_de_fretes", empresa_id=empresa.id)

    frete_item = Frete.objects.filter(id=frete_id, empresa=empresa).first()
    if not frete_item:
        messages.error(request, "Frete não encontrado.")
        return redirect("tabela_de_fretes", empresa_id=empresa.id)

    frete_item.excluir_frete()
    messages.success(request, "Frete excluído com sucesso.")
    return redirect("tabela_de_fretes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def estoque_pcp(request, empresa_id):
    modulo = _obter_modulo("Operacional", "Estoque - PCP")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_estoque(empresa)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if _bloquear_criar_em_modulo_com_importacao_se_necessario(
            request,
            empresa,
            acao,
            {"criar_estoque"},
        ):
            return redirect("estoque_pcp", empresa_id=empresa_id)
        if acao == "criar_estoque":
            erro = criar_estoque_por_post(empresa, request.POST)
            if erro:
                messages.error(request, erro)
            else:
                messages.success(request, "Registro de estoque criado com sucesso.")
        elif acao == "importar_estoque":
            arquivos = request.FILES.getlist("arquivos_estoque")
            ok, mensagem = importar_upload_estoque(
                empresa=empresa,
                arquivos=arquivos,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
                usuario=request.user,
            )
            if ok:
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.error(request, "Ação de estoque inválida.")
        return redirect("estoque_pcp", empresa_id=empresa_id)

    estoque_qs = (
        Estoque.objects.filter(empresa=empresa)
        .select_related("produto")
        .order_by("-data_contagem", "-id")
    )
    codigos_volume = sorted(
        {
            str(valor).strip()
            for valor in Estoque.objects.filter(empresa=empresa).values_list("codigo_volume", flat=True)
            if str(valor).strip()
        }
    )
    codigos_local = sorted(
        {
            str(valor).strip()
            for valor in Estoque.objects.filter(empresa=empresa).values_list("codigo_local", flat=True)
            if str(valor).strip()
        }
    )
    arquivos_existentes = sorted(
        [
            str(f.relative_to(diretorio_importacao)).replace("\\", "/")
            for f in diretorio_importacao.rglob("*.xls")
            if f.is_file() and diretorio_subscritos not in f.parents
        ]
    )
    arquivo_existente_texto, tem_arquivo_existente = _resumir_arquivos_existentes(arquivos_existentes)
    resumo_importacao = _montar_resumo_importacao(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        modulo="estoque_pcp",
        empresa_id=empresa.id,
        extensoes={".xls"},
    )

    contexto = {
        "empresa": empresa,
        "bloquear_cadastro_edicao_importacao": _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        "modulo_nome": modulo["nome"],
        "tipo_importacao_texto": TIPO_IMPORTACAO_POR_MODULO["estoque_pcp"],
        "resumo_importacao": resumo_importacao,
        "arquivo_existente": arquivo_existente_texto,
        "tem_arquivo_existente": tem_arquivo_existente,
        "produtos": Produto.objects.filter(empresa=empresa).order_by("codigo_produto"),
        "status_opcoes_estoque": ["Ativo", "Inativo", "Pendente"],
        "codigos_volume_estoque": codigos_volume,
        "codigos_local_estoque": codigos_local,
        "estoque_tabulator": build_estoque_tabulator(
            estoque_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, "operacional/estoque_pcp.html", contexto)


@login_required(login_url="entrar")
def editar_estoque_modulo(request, empresa_id, estoque_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Estoque - PCP")
    if not autorizado:
        return redirect("index")
    bloqueio = _bloquear_edicao_em_modulo_com_importacao_se_necessario(request, empresa, "estoque_pcp")
    if bloqueio:
        return bloqueio

    estoque_item = Estoque.objects.filter(id=estoque_id, empresa=empresa).select_related("produto").first()
    if not estoque_item:
        messages.error(request, "Registro de estoque não encontrado.")
        return redirect("estoque_pcp", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_estoque_por_post(estoque_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_estoque_modulo", empresa_id=empresa.id, estoque_id=estoque_item.id)
        messages.success(request, "Registro de estoque atualizado com sucesso.")
        return redirect("estoque_pcp", empresa_id=empresa.id)

    codigos_volume = sorted(
        {
            str(valor).strip()
            for valor in Estoque.objects.filter(empresa=empresa).values_list("codigo_volume", flat=True)
            if str(valor).strip()
        }
    )
    codigos_local = sorted(
        {
            str(valor).strip()
            for valor in Estoque.objects.filter(empresa=empresa).values_list("codigo_local", flat=True)
            if str(valor).strip()
        }
    )
    if estoque_item.codigo_volume and estoque_item.codigo_volume not in codigos_volume:
        codigos_volume.append(estoque_item.codigo_volume)
        codigos_volume.sort()
    if estoque_item.codigo_local and estoque_item.codigo_local not in codigos_local:
        codigos_local.append(estoque_item.codigo_local)
        codigos_local.sort()

    contexto = {
        "empresa": empresa,
        "estoque_item": estoque_item,
        "produtos": Produto.objects.filter(empresa=empresa).order_by("codigo_produto"),
        "status_opcoes_estoque": ["Ativo", "Inativo", "Pendente"],
        "codigos_volume_estoque": codigos_volume,
        "codigos_local_estoque": codigos_local,
    }
    return render(request, "operacional/estoque_pcp_editar.html", contexto)


@login_required(login_url="entrar")
def excluir_estoque_modulo(request, empresa_id, estoque_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Estoque - PCP")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("estoque_pcp", empresa_id=empresa.id)

    estoque_item = Estoque.objects.filter(id=estoque_id, empresa=empresa).first()
    if not estoque_item:
        messages.error(request, "Registro de estoque não encontrado.")
        return redirect("estoque_pcp", empresa_id=empresa.id)

    estoque_item.excluir_estoque()
    messages.success(request, "Registro de estoque excluído com sucesso.")
    return redirect("estoque_pcp", empresa_id=empresa.id)
