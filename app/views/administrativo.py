import json
import unicodedata
from datetime import datetime
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, FloatField, Max, Sum, Value
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Adiantamento,
    Atividade,
    CentroResultado,
    Colaborador,
    ContasAReceber,
    Descritivo,
    DescricaoPerfil,
    Estoque,
    Faturamento,
    Natureza,
    Operacao,
    Orcamento,
    Parceiro,
    ParametroMargemAdministracao,
    ParametroMargemFinanceiro,
    ParametroMargemLogistica,
    ParametroMargemVendas,
    ParametroMeta,
    ParametroNegocios,
    PedidoPendente,
    PlanoCargoSalario,
    Produto,
    Projeto,
    Venda,
)
from ..services.administrativo import (
    atualizar_atividade_por_post,
    atualizar_colaborador_por_nome,
    atualizar_descritivo_por_post,
    atualizar_faturamento_por_post,
    atualizar_plano_cargo_salario_por_post,
    atualizar_projeto_por_dados,
    criar_atividade_por_post,
    criar_colaborador_por_nome,
    criar_descritivo_por_post,
    criar_faturamento_por_post,
    criar_plano_cargo_salario_por_post,
    criar_projeto_por_dados,
    importar_upload_faturamento,
    preparar_diretorios_faturamento,
    semana_iso_input_atividade,
)
from ..tabulator import (
    build_colaboradores_tabulator,
    build_descritivo_tabulator_item,
    build_descritivos_tabulator,
    build_faturamento_tabulator,
    build_plano_cargos_salarios_tabulator,
    build_projetos_tabulator,
)
from ..utils.administrativo_transformers import montar_contexto_tofu_lista
from ..utils.financeiro_importacao import (
    _arquivo_xlsx_visivel,
    _classificar_arquivo_faturamento,
    _importar_base_faturamento_diario,
)
from ..utils.modulos_permissoes import (
    _modulos_com_acesso,
    _obter_empresa_e_validar_permissao_modulo,
    _obter_empresa_e_validar_permissao_tofu,
    _render_modulo_com_permissao,
)
from ..utils.pdf_renderer import render_template_to_pdf_bytes
from .shared import (
    TIPO_IMPORTACAO_POR_MODULO,
    _bloquear_criar_em_modulo_com_importacao_se_necessario,
    _bloquear_edicao_em_modulo_com_importacao_se_necessario,
    _empresa_bloqueia_cadastro_edicao_importacao,
    _ler_metadados_importacao,
    _montar_resumo_importacao,
    _nome_metadados_importacao_por_empresa,
    _normalizar_empresa_id,
    _obter_modulo,
    _resumir_arquivos_existentes,
)


def _normalizar_token_vendedor(valor):
    texto = str(valor or "").strip().lower()
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.split())


def _descricoes_perfil_empresa(empresa):
    return sorted(
        [
            valor
            for valor in DescricaoPerfil.objects.filter(empresa=empresa).values_list("descricao", flat=True)
            if str(valor or "").strip()
        ],
        key=lambda item: item.lower(),
    )


def _texto_filtro_get(request, campo):
    return str(request.GET.get(campo) or "").strip()


def _filtros_planos_cargos_salarios(request):
    return {
        "cadastro": _texto_filtro_get(request, "cadastro"),
        "funcionario": _texto_filtro_get(request, "funcionario"),
        "contrato": _texto_filtro_get(request, "contrato"),
        "genero": _texto_filtro_get(request, "genero"),
        "setor": _texto_filtro_get(request, "setor"),
        "cargo": _texto_filtro_get(request, "cargo"),
        "novo_cargo": _texto_filtro_get(request, "novo_cargo"),
    }


def _aplicar_filtros_planos_cargos_salarios(qs, filtros):
    cadastro = filtros.get("cadastro")
    if cadastro:
        try:
            cadastro_int = int(cadastro)
        except (TypeError, ValueError):
            cadastro_int = None
        if cadastro_int is not None and cadastro_int > 0:
            qs = qs.filter(cadastro=cadastro_int)

    funcionario = filtros.get("funcionario")
    if funcionario:
        qs = qs.filter(funcionario__icontains=funcionario)

    for campo in ("contrato", "genero", "setor", "cargo", "novo_cargo"):
        valor = filtros.get(campo)
        if valor:
            qs = qs.filter(**{campo: valor})

    return qs


def _opcoes_filtros_planos_cargos_salarios(empresa):
    def _valores(campo):
        return list(
            PlanoCargoSalario.objects.filter(empresa=empresa)
            .exclude(**{campo: ""})
            .values_list(campo, flat=True)
            .distinct()
            .order_by(campo)
        )

    return {
        "contratos": _valores("contrato"),
        "generos": _valores("genero"),
        "setores": _valores("setor"),
        "cargos": _valores("cargo"),
        "novos_cargos": _valores("novo_cargo"),
    }


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _payload_plano_cargo_salario(item):
    return {
        "id": item.id,
        "cadastro": item.cadastro,
        "funcionario": item.funcionario or "",
        "contrato": item.contrato or "",
        "genero": item.genero or "",
        "setor": item.setor or "",
        "cargo": item.cargo or "",
        "novo_cargo": item.novo_cargo or "",
        "data_admissao_iso": item.data_admissao.strftime("%Y-%m-%d") if item.data_admissao else "",
        "salario_carteira": float(item.salario_carteira) if item.salario_carteira is not None else None,
        "piso_categoria": float(item.piso_categoria) if item.piso_categoria is not None else None,
        "jr": float(item.jr) if item.jr is not None else None,
        "pleno": float(item.pleno) if item.pleno is not None else None,
        "senior": float(item.senior) if item.senior is not None else None,
        "editar_url": reverse(
            "editar_plano_cargo_salario_modulo",
            kwargs={"empresa_id": item.empresa_id, "plano_cargo_salario_id": item.id},
        ),
        "excluir_url": reverse(
            "excluir_plano_cargo_salario_modulo",
            kwargs={"empresa_id": item.empresa_id, "plano_cargo_salario_id": item.id},
        ),
    }


def _payload_descritivo(item):
    return build_descritivo_tabulator_item(item, item.empresa_id)


def _chave_vendedor_total_legado(valor):
    token = _normalizar_token_vendedor(valor)
    if not token:
        return ""

    if token in {"sem gerente", "<sem gerente>"}:
        return ""
    if token in {"sem vendedor", "<sem vendedor>"}:
        return "<SEM VENDEDOR>"

    # Compatibilidade com comportamento legado do dashboard.
    if token == "a distribuir":
        return ""
    if "corret" in token:
        return ""
    if token.startswith("novo go "):
        return ""
    return token


def _calcular_total_vendedores_legado_faturamento(diretorio_importacao, diretorio_subscritos):
    arquivos = sorted(
        [
            arquivo
            for arquivo in diretorio_importacao.rglob("*")
            if arquivo.is_file()
            and diretorio_subscritos not in arquivo.parents
            and _arquivo_xlsx_visivel(arquivo)
        ]
    )
    if not arquivos:
        return 0

    arquivos_diario = [
        arquivo
        for arquivo in arquivos
        if _classificar_arquivo_faturamento(diretorio_importacao, arquivo) == "diario"
    ]
    if not arquivos_diario:
        return 0

    resultado_diario = _importar_base_faturamento_diario(arquivos_diario)
    registros = resultado_diario.get("registros", [])
    vendedores = set()
    for item in registros:
        chave = _chave_vendedor_total_legado(item.get("apelido_vendedor"))
        if chave:
            vendedores.add(chave)
    return len(vendedores)


def _obter_total_vendedores_legado_faturamento(diretorio_importacao, diretorio_subscritos, empresa_id):
    metadados = _ler_metadados_importacao(
        diretorio_importacao=diretorio_importacao,
        modulo="faturamento",
        empresa_id=empresa_id,
    )
    total_salvo = metadados.get("faturamento_vendedores_total_legacy")
    try:
        total_salvo_int = int(total_salvo)
    except (TypeError, ValueError):
        total_salvo_int = 0
    if total_salvo_int > 0:
        return total_salvo_int

    try:
        total_calculado = _calcular_total_vendedores_legado_faturamento(
            diretorio_importacao=diretorio_importacao,
            diretorio_subscritos=diretorio_subscritos,
        )
    except Exception:
        return 0

    if total_calculado <= 0:
        return 0

    nome_metadados = _nome_metadados_importacao_por_empresa(empresa_id)
    if nome_metadados:
        caminho_metadados = diretorio_importacao / nome_metadados
        payload = dict(metadados) if isinstance(metadados, dict) else {}
        payload["empresa_id"] = _normalizar_empresa_id(empresa_id)
        payload["modulo"] = "faturamento"
        payload["faturamento_vendedores_total_legacy"] = int(total_calculado)
        try:
            caminho_metadados.parent.mkdir(parents=True, exist_ok=True)
            caminho_metadados.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    return int(total_calculado)


def _texto_pdf_faturamento(valor, fallback="-", limite=180):
    texto = str(valor or "").strip()
    if not texto:
        return fallback
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


def _linhas_pdf_faturamento(lista):
    if not isinstance(lista, (list, tuple)):
        return ["- Nenhum filtro ativo."]
    linhas = []
    for item in lista:
        texto = _texto_pdf_faturamento(item, fallback="", limite=220)
        if texto:
            linhas.append(texto)
    return linhas or ["- Nenhum filtro ativo."]


def _carregar_payload_dashboard_pdf_faturamento(request):
    bruto = request.POST.get("payload_json")
    if not bruto:
        return {}
    try:
        payload = json.loads(bruto)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _montar_contexto_dashboard_pdf_faturamento(empresa, payload):
    dados = payload if isinstance(payload, dict) else {}
    dashboard = dados.get("dashboard") if isinstance(dados.get("dashboard"), dict) else {}
    graficos_payload = dados.get("graficos") if isinstance(dados.get("graficos"), dict) else {}

    ordem_graficos = [
        ("tipo_venda", "Tipo da Venda"),
        ("vendedores_resumo", "Vendedores"),
        ("faturamento_loja", "Faturamento Loja"),
        ("faturamento_mensal", "Faturamento Mensal"),
        ("faturamento_vendedores", "Faturamento Vendedores"),
        ("top10_dias", "TOP 10 DIAS"),
        ("top10_produtos", "TOP 10 PRODUTOS"),
        ("faturamento_cidade", "Faturamento por Cidade"),
        ("perfil_clientes", "Perfil Clientes"),
    ]
    graficos = []
    for chave, titulo_padrao in ordem_graficos:
        item = graficos_payload.get(chave) if isinstance(graficos_payload.get(chave), dict) else {}
        img_uri = str(item.get("img_uri") or "").strip()
        if not img_uri.startswith("data:image/"):
            img_uri = ""
        graficos.append(
            {
                "chave": chave,
                "titulo": _texto_pdf_faturamento(item.get("titulo"), titulo_padrao, limite=80),
                "img_uri": img_uri,
            }
        )

    return {
        "empresa": empresa,
        "gerado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        "dashboard": {
            "valor_faturamento": _texto_pdf_faturamento(dashboard.get("valor_faturamento"), "R$ 0,00"),
            "meta_geral": _texto_pdf_faturamento(dashboard.get("meta_geral"), "R$ 0,00"),
            "gap_faturamento": _texto_pdf_faturamento(dashboard.get("gap_faturamento"), "R$ 0,00"),
            "prazo_medio": _texto_pdf_faturamento(dashboard.get("prazo_medio"), "0"),
            "dias_uteis": _texto_pdf_faturamento(dashboard.get("dias_uteis"), "0"),
            "meta_diaria": _texto_pdf_faturamento(dashboard.get("meta_diaria"), "R$ 0,00"),
            "pedidos_pendentes": _texto_pdf_faturamento(dashboard.get("pedidos_pendentes"), "R$ 0,00 / 0 dias uteis"),
            "qtd_clientes": _texto_pdf_faturamento(dashboard.get("qtd_clientes"), "0"),
            "participacao_venda_geral": _texto_pdf_faturamento(
                dashboard.get("participacao_venda_geral"),
                "0,00%",
            ),
            "incluir_pedidos_pendentes": _texto_pdf_faturamento(
                dashboard.get("incluir_pedidos_pendentes"),
                "Nao",
            ),
            "reloginho_meta": _texto_pdf_faturamento(dashboard.get("reloginho_meta"), "R$ 0,00"),
            "reloginho_real": _texto_pdf_faturamento(dashboard.get("reloginho_real"), "R$ 0,00"),
            "reloginho_percentual": _texto_pdf_faturamento(dashboard.get("reloginho_percentual"), "0,00%"),
            "vendedores_com_venda_total": _texto_pdf_faturamento(
                dashboard.get("vendedores_com_venda_total"),
                "0",
            ),
            "vendedores_sem_venda_total": _texto_pdf_faturamento(
                dashboard.get("vendedores_sem_venda_total"),
                "0",
            ),
            "registros_ativos": _texto_pdf_faturamento(dashboard.get("registros_ativos"), "0"),
        },
        "filtros_ativos": _linhas_pdf_faturamento(dados.get("filtros_ativos")),
        "graficos": graficos,
        "graficos_exportados": sum(1 for item in graficos if item.get("img_uri")),
    }


def _usuario_pode_gerenciar_atividade(usuario, atividade):
    return atividade.pode_ser_editada_por(usuario)


@login_required(login_url="entrar")
def administrativo(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Administrativo"),
    }
    return render(request, "administrativo/administrativo.html", contexto)


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
def plano_de_cargos_e_salarios(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Plano de Cargos e Salarios")
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not autorizado:
        return redirect("index")

    filtros = _filtros_planos_cargos_salarios(request)
    planos_qs_base = PlanoCargoSalario.objects.filter(empresa=empresa)
    planos_qs = _aplicar_filtros_planos_cargos_salarios(
        planos_qs_base,
        filtros,
    ).order_by("funcionario", "cadastro")

    contexto = {
        "empresa": empresa,
        "filtros": filtros,
        "filtros_opcoes": _opcoes_filtros_planos_cargos_salarios(empresa),
        "planos_cargos_salarios": planos_qs,
        "planos_cargos_salarios_tabulator": build_plano_cargos_salarios_tabulator(planos_qs, empresa.id),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def criar_plano_cargo_salario_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Plano de Cargos e Salarios",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    erro = criar_plano_cargo_salario_por_post(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    if _is_ajax_request(request):
        cadastro_raw = str(request.POST.get("cadastro") or "").strip()
        item = None
        try:
            cadastro = int(cadastro_raw)
        except (TypeError, ValueError):
            cadastro = 0
        if cadastro > 0:
            item = (
                PlanoCargoSalario.objects.filter(empresa=empresa, cadastro=cadastro)
                .order_by("-id")
                .first()
            )
        if item is None:
            item = PlanoCargoSalario.objects.filter(empresa=empresa).order_by("-id").first()
        if item is None:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Registro criado, mas nao foi possivel recarregar os dados.",
                },
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_plano_cargo_salario(item),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_plano_cargo_salario_modulo(request, empresa_id, plano_cargo_salario_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Plano de Cargos e Salarios",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    item = PlanoCargoSalario.objects.filter(id=plano_cargo_salario_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    erro = atualizar_plano_cargo_salario_por_post(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_plano_cargo_salario(item),
            }
        )
    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_plano_cargo_salario_modulo(request, empresa_id, plano_cargo_salario_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Plano de Cargos e Salarios",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    item = PlanoCargoSalario.objects.filter(id=plano_cargo_salario_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)

    item_id = item.id
    item.excluir_plano_cargo_salario()
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro excluido com sucesso.",
                "id": item_id,
            }
        )
    messages.success(request, "Registro excluido com sucesso.")
    return redirect("plano_de_cargos_e_salarios", empresa_id=empresa.id)


@login_required(login_url="entrar")
def descritivos(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Descritivos")
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not autorizado:
        return redirect("index")

    descritivos_qs = Descritivo.objects.filter(empresa=empresa).order_by("inicio", "termino", "id")
    contexto = {
        "empresa": empresa,
        "descritivos": descritivos_qs,
        "descritivos_tabulator": build_descritivos_tabulator(descritivos_qs, empresa.id),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def criar_descritivo_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Descritivos",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("descritivos", empresa_id=empresa.id)

    erro = criar_descritivo_por_post(empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("descritivos", empresa_id=empresa.id)

    if _is_ajax_request(request):
        inicio = str(request.POST.get("inicio") or "").strip()
        termino = str(request.POST.get("termino") or "").strip()
        item = (
            Descritivo.objects.filter(empresa=empresa, inicio=inicio, termino=termino)
            .order_by("-id")
            .first()
        )
        if item is None:
            item = Descritivo.objects.filter(empresa=empresa).order_by("-id").first()
        if item is None:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Registro criado, mas nao foi possivel recarregar os dados.",
                },
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro criado com sucesso.",
                "registro": _payload_descritivo(item),
            }
        )

    messages.success(request, "Registro criado com sucesso.")
    return redirect("descritivos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def editar_descritivo_modulo(request, empresa_id, descritivo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Descritivos",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("descritivos", empresa_id=empresa.id)

    item = Descritivo.objects.filter(id=descritivo_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("descritivos", empresa_id=empresa.id)

    erro = atualizar_descritivo_por_post(item, empresa, request.POST)
    if erro:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": erro}, status=400)
        messages.error(request, erro)
        return redirect("descritivos", empresa_id=empresa.id)

    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro atualizado com sucesso.",
                "registro": _payload_descritivo(item),
            }
        )

    messages.success(request, "Registro atualizado com sucesso.")
    return redirect("descritivos", empresa_id=empresa.id)


@login_required(login_url="entrar")
def excluir_descritivo_modulo(request, empresa_id, descritivo_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(
        request,
        empresa_id,
        "Descritivos",
    )
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("descritivos", empresa_id=empresa.id)

    item = Descritivo.objects.filter(id=descritivo_id, empresa=empresa).first()
    if not item:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "message": "Registro nao encontrado."}, status=404)
        messages.error(request, "Registro nao encontrado.")
        return redirect("descritivos", empresa_id=empresa.id)

    item_id = item.id
    item.excluir_descritivo()
    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "message": "Registro excluido com sucesso.",
                "id": item_id,
            }
        )

    messages.success(request, "Registro excluido com sucesso.")
    return redirect("descritivos", empresa_id=empresa.id)


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
    parametro_negocios_qs = ParametroNegocios.objects.filter(empresa=empresa).order_by("-id")
    parametro_negocios_faturamento = (
        parametro_negocios_qs.filter(direcao__icontains="faturamento", compromisso_unidade="valor").first()
        or parametro_negocios_qs.filter(direcao__icontains="faturamento").first()
        or parametro_negocios_qs.filter(compromisso_unidade="valor").first()
        or parametro_negocios_qs.first()
    )
    faturamento_meta_config = {
        "compromisso": (
            float(parametro_negocios_faturamento.compromisso or 0)
            if parametro_negocios_faturamento
            else 0.0
        ),
        "gerente_pa_e_outros": (
            float(parametro_negocios_faturamento.gerente_pa_e_outros or 0)
            if parametro_negocios_faturamento
            else 0.0
        ),
        "gerente_mp_e_gerente_luciano": (
            float(parametro_negocios_faturamento.gerente_mp_e_gerente_luciano or 0)
            if parametro_negocios_faturamento
            else 0.0
        ),
    }
    pedidos_pendentes_por_gerente_qs = (
        PedidoPendente.objects.filter(empresa=empresa)
        .values("gerente")
        .annotate(
            total_vlr_nota=Coalesce(
                Sum("vlr_nota"),
                Value(0, output_field=DecimalField(max_digits=16, decimal_places=2)),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )
        .order_by()
    )
    faturamento_pedidos_pendentes = [
        {
            "gerente": item.get("gerente") or "",
            "total_vlr_nota": float(item.get("total_vlr_nota") or 0),
        }
        for item in pedidos_pendentes_por_gerente_qs
    ]
    faturamento_parametros_metas = [
        {
            "descricao_perfil": (item.descricao_perfil.descricao if item.descricao_perfil else ""),
            "valor_meta_pd_acabado": (
                float(item.valor_meta_pd_acabado)
                if item.valor_meta_pd_acabado is not None
                else None
            ),
        }
        for item in (
            ParametroMeta.objects.filter(empresa=empresa)
            .select_related("descricao_perfil")
            .order_by("id")
        )
    ]

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
    total_vendedores_legado = _obter_total_vendedores_legado_faturamento(
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        empresa_id=empresa.id,
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
        "descricoes_perfil": _descricoes_perfil_empresa(empresa),
        "faturamento_meta_config": faturamento_meta_config,
        "faturamento_pedidos_pendentes": faturamento_pedidos_pendentes,
        "faturamento_parametros_metas": faturamento_parametros_metas,
        "faturamento_vendedores_resumo_base": {
            "total_vendedores": int(total_vendedores_legado or 0),
        },
        "faturamento_dashboard_pdf_url": reverse(
            "faturamento_dashboard_pdf",
            kwargs={"empresa_id": empresa.id},
        ),
        "faturamento_tabulator": build_faturamento_tabulator(
            faturamento_qs,
            empresa.id,
            permitir_edicao=not _empresa_bloqueia_cadastro_edicao_importacao(empresa),
        ),
    }
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def faturamento_dashboard_pdf(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Faturamento")
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Metodo nao permitido."}, status=405)

    payload = _carregar_payload_dashboard_pdf_faturamento(request)
    contexto = _montar_contexto_dashboard_pdf_faturamento(empresa, payload)
    texto_relatorio = render_to_string(
        "dashboards_pdf/administrativo/faturamento_texto.txt",
        contexto,
        request=request,
    )
    contexto_pdf = dict(contexto)
    contexto_pdf["texto_relatorio"] = texto_relatorio

    try:
        pdf_bytes = render_template_to_pdf_bytes(
            "dashboards_pdf/administrativo/faturamento.html",
            context=contexto_pdf,
            request=request,
        )
    except RuntimeError as erro:
        return JsonResponse({"detail": str(erro)}, status=500)

    resposta = HttpResponse(pdf_bytes, content_type="application/pdf")
    sufixo = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    resposta["Content-Disposition"] = f'attachment; filename="dashboard-faturamento-{sufixo}.pdf"'
    return resposta


_APURACAO_COLUNAS_SETORIAIS = (
    ("compras", "Compras"),
    ("vendas", "Vendas"),
    ("producao", "Producao"),
    ("logistica", "Logistica"),
    ("administracao", "Administracao"),
    ("financeiro", "Financeiro"),
)

_APURACAO_PERCENTUAL_CMV_AJUSTADO = Decimal("0.89")
_APURACAO_QUERY_PARAM_CMV_AJUSTADO = "cmv_ajustado_percentual"
_APURACAO_CENTRO_ALIASES = {
    "cmv": ("CMV",),
    "administracao": ("ADMINISTRACAO",),
    "comercial": ("COMERCIAL",),
    "financeiro": ("FINANCEIRO",),
    "industria": ("INDUSTRIA(ACUCAREIRA)",),
    "logistica": ("LOGISTICA",),
}
_APURACAO_ORDEM_PARAMETROS = (
    "parametros_vendas",
    "produtos",
    "parametros_logistica",
    "parametros_administracao",
    "parametros_financeiro",
    "parametros_negocios",
)
_APURACAO_ROTULOS_PARAMETROS = {
    "parametros_vendas": "Parametros Vendas",
    "produtos": "Parametros Produtos",
    "parametros_logistica": "Parametros Logistica",
    "parametros_administracao": "Parametros Administracao",
    "parametros_financeiro": "Parametros Financeiro",
    "parametros_negocios": "Parametros do Negocio",
}


def _parse_data_iso(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_percentual_apuracao_para_ratio(valor, default_ratio):
    texto = str(valor or "").strip()
    if not texto:
        return Decimal(default_ratio)

    tem_percentual = "%" in texto
    texto = texto.replace("%", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        numero = Decimal(texto)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default_ratio)

    if numero < 0:
        return Decimal("0")
    if tem_percentual or numero > 1:
        return numero / Decimal("100")
    return numero


def _datas_default_apuracao(empresa):
    max_faturamento = Faturamento.objects.filter(empresa=empresa).aggregate(data=Max("data_faturamento")).get("data")
    max_orcamento = Orcamento.objects.filter(empresa=empresa).aggregate(data=Max("data_baixa")).get("data")

    datas_validas = [data for data in (max_faturamento, max_orcamento) if data is not None]
    if not datas_validas:
        hoje = timezone.localdate()
        return hoje, hoje

    data_ref = max(datas_validas)
    return data_ref, data_ref


def _resolver_periodo_apuracao(empresa, data_inicial_raw, data_final_raw):
    data_inicial = _parse_data_iso(data_inicial_raw)
    data_final = _parse_data_iso(data_final_raw)

    if data_inicial is None and data_final is None:
        return _datas_default_apuracao(empresa)
    if data_inicial is None:
        return data_final, data_final
    if data_final is None:
        return data_inicial, data_inicial
    if data_inicial > data_final:
        return data_final, data_inicial
    return data_inicial, data_final


def _normalizar_chave_apuracao(valor):
    texto = unicodedata.normalize("NFD", str(valor or "").strip().upper())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.split())


def _decimal_2(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def _sum_decimal(qs, campo, *, max_digits=18, decimal_places=2):
    agregado = qs.aggregate(
        total=Coalesce(
            Sum(campo),
            Value(Decimal("0"), output_field=DecimalField(max_digits=max_digits, decimal_places=decimal_places)),
        )
    )
    return Decimal(agregado.get("total") or 0)


def _texto_moeda_apuracao(valor):
    if valor is None:
        return ""
    numero = _decimal_2(valor)
    prefixo = "R$ "
    if numero < 0:
        numero = abs(numero)
        prefixo = "-R$ "
    texto = f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{prefixo}{texto}"


def _texto_percentual_apuracao(valor):
    if valor is None:
        return ""
    numero = Decimal(valor) * Decimal("100")
    texto = f"{numero:.2f}".replace(".", ",")
    return f"{texto}%"


def _linha_feedback_parametro_apuracao(data_ref, valor):
    return {
        "data": data_ref.strftime("%d/%m/%Y") if data_ref else "",
        "valor": _texto_moeda_apuracao(valor),
    }


def _totais_apuracao_por_data(qs, campo_data, campo_valor, *, max_digits=20, decimal_places=2):
    return {
        item[campo_data]: Decimal(item.get("total") or 0)
        for item in (
            qs.values(campo_data).annotate(
                total=Coalesce(
                    Sum(campo_valor),
                    Value(Decimal("0"), output_field=DecimalField(max_digits=max_digits, decimal_places=decimal_places)),
                )
            )
        )
    }


def _somar_demonstrativo_diario_apuracao(totais_por_data, data_inicial, data_final, remuneracao):
    datas_disponiveis = sorted(totais_por_data.keys())
    saldo_dia = Decimal("0")
    for data_ref in datas_disponiveis:
        if data_ref < data_inicial:
            saldo_dia = totais_por_data.get(data_ref, Decimal("0"))
        else:
            break

    total = Decimal("0")
    linhas_feedback = []
    data_cursor = data_inicial
    while data_cursor <= data_final:
        if data_cursor in totais_por_data:
            saldo_dia = totais_por_data[data_cursor]
        valor_dia = saldo_dia * Decimal(remuneracao or 0)
        linhas_feedback.append(_linha_feedback_parametro_apuracao(data_cursor, _decimal_2(valor_dia)))
        total += valor_dia
        data_cursor += timedelta(days=1)
    return _decimal_2(total), linhas_feedback


def _linha_apuracao(
    descricao,
    classe,
    valores_por_coluna=None,
    percentuais_por_coluna=None,
    percentuais_editaveis_por_coluna=None,
):
    valores_por_coluna = valores_por_coluna or {}
    percentuais_por_coluna = percentuais_por_coluna or {}
    percentuais_editaveis_por_coluna = percentuais_editaveis_por_coluna or {}
    celulas = []
    for chave, _ in _APURACAO_COLUNAS_SETORIAIS:
        config_edicao = percentuais_editaveis_por_coluna.get(chave) or {}
        celulas.append(
            {
                "valor": _texto_moeda_apuracao(valores_por_coluna.get(chave)),
                "percentual": _texto_percentual_apuracao(percentuais_por_coluna.get(chave)),
                "percentual_editavel": bool(config_edicao.get("editavel")),
                "percentual_input_name": str(config_edicao.get("name") or ""),
                "percentual_valor_edicao": str(config_edicao.get("valor") or ""),
            }
        )
    return {
        "descricao": descricao,
        "classe": classe,
        "celulas": celulas,
    }


def _somar_remuneracao_total_vendas(empresa, data_inicial, data_final):
    vendas = list(
        Venda.objects.filter(
            empresa=empresa,
            data_venda__gte=data_inicial,
            data_venda__lte=data_final,
        ).values("codigo", "peso_liquido")
    )
    codigos = {(item.get("codigo") or "").strip() for item in vendas if (item.get("codigo") or "").strip()}
    produtos_por_codigo = {}
    if codigos:
        produtos_por_codigo = {
            item["codigo_produto"]: {
                "kg": Decimal(item.get("kg") or 0),
                "remuneracao_por_fardo": Decimal(item.get("remuneracao_por_fardo") or 0),
            }
            for item in Produto.objects.filter(empresa=empresa, codigo_produto__in=codigos).values(
                "codigo_produto",
                "kg",
                "remuneracao_por_fardo",
            )
        }

    total = Decimal("0")
    for venda in vendas:
        codigo = (venda.get("codigo") or "").strip()
        produto = produtos_por_codigo.get(codigo) or {}
        kg = Decimal(produto.get("kg") or 0)
        remuneracao_por_fardo = Decimal(produto.get("remuneracao_por_fardo") or 0)
        if kg <= 0:
            continue
        peso_liquido = Decimal(venda.get("peso_liquido") or 0)
        quantidade_fardos = peso_liquido / kg
        total += quantidade_fardos * remuneracao_por_fardo
    return total


def _total_por_alias(mapa, *aliases):
    chave_alias = {_normalizar_chave_apuracao(alias) for alias in aliases}
    total = Decimal("0")
    for chave, valor in mapa.items():
        if chave in chave_alias:
            total += Decimal(valor or 0)
    return total


def _somar_custo_total_estoque_por_data(empresa, data_referencia):
    return _sum_decimal(
        Estoque.objects.filter(empresa=empresa, data_contagem=data_referencia),
        "custo_total",
        max_digits=20,
        decimal_places=3,
    )


def _obter_parametro_logistica_operador(empresa):
    parametro_operador = (
        ParametroMargemLogistica.objects.filter(empresa=empresa, parametro__icontains="operador")
        .order_by("id")
        .first()
    )
    if parametro_operador:
        return parametro_operador
    return ParametroMargemLogistica.objects.filter(empresa=empresa).order_by("id").first()


def _obter_valor_parametro_financeiro(empresa, campo, *aliases):
    aliases_normalizados = [
        _normalizar_chave_apuracao(alias)
        for alias in aliases
        if str(alias or "").strip()
    ]
    if not aliases_normalizados:
        return Decimal("0")

    parametros = (
        ParametroMargemFinanceiro.objects.filter(empresa=empresa)
        .order_by("id")
        .values("parametro", campo)
    )
    for item in parametros:
        parametro_norm = _normalizar_chave_apuracao(item.get("parametro") or "")
        if any(alias in parametro_norm for alias in aliases_normalizados):
            return Decimal(item.get(campo) or 0)
    return Decimal("0")


def _calcular_kpi_parametros_financeiros(empresa, data_inicial, data_final):
    remuneracao_financeiro = _obter_valor_parametro_financeiro(
        empresa,
        "remuneracao_percentual",
        "contas a receber",
        "contas receber",
        "financeiro",
    )
    remuneracao_adiantamentos = _obter_valor_parametro_financeiro(
        empresa,
        "remuneracao_percentual",
        "adiantamentos",
        "adiantamento",
    )
    remuneracao_estoque = _obter_valor_parametro_financeiro(empresa, "remuneracao_percentual", "estoque")

    totais_contas_receber_por_data = _totais_apuracao_por_data(
        ContasAReceber.objects.filter(empresa=empresa, data_arquivo__isnull=False),
        "data_arquivo",
        "valor_liquido",
    )
    resultado_demonstrativo_financeiro, feedback_financeiro = _somar_demonstrativo_diario_apuracao(
        totais_contas_receber_por_data,
        data_inicial,
        data_final,
        remuneracao_financeiro,
    )

    totais_adiantamentos_por_data = _totais_apuracao_por_data(
        Adiantamento.objects.filter(empresa=empresa, data_arquivo__isnull=False),
        "data_arquivo",
        "saldo_real_em_reais",
    )
    resultado_demonstrativo_adiantamentos, feedback_adiantamentos = _somar_demonstrativo_diario_apuracao(
        totais_adiantamentos_por_data,
        data_inicial,
        data_final,
        remuneracao_adiantamentos,
    )

    totais_estoque_por_data = _totais_apuracao_por_data(
        Estoque.objects.filter(empresa=empresa),
        "data_contagem",
        "custo_total",
        decimal_places=3,
    )
    resultado_demonstrativo_estoque, feedback_estoque = _somar_demonstrativo_diario_apuracao(
        totais_estoque_por_data,
        data_inicial,
        data_final,
        remuneracao_estoque,
    )
    valor = _decimal_2(
        resultado_demonstrativo_financeiro
        + resultado_demonstrativo_adiantamentos
        + resultado_demonstrativo_estoque
    )

    return {
        "valor": valor,
        "resultado_demonstrativo_financeiro": resultado_demonstrativo_financeiro,
        "resultado_demonstrativo_adiantamentos": resultado_demonstrativo_adiantamentos,
        "resultado_demonstrativo_estoque": resultado_demonstrativo_estoque,
        "feedback": [
            {
                "titulo": "Resultado Demonstrativo Financeiro",
                "total": _texto_moeda_apuracao(resultado_demonstrativo_financeiro),
                "linhas": feedback_financeiro,
            },
            {
                "titulo": "Resultado Demonstrativo Adiantamentos",
                "total": _texto_moeda_apuracao(resultado_demonstrativo_adiantamentos),
                "linhas": feedback_adiantamentos,
            },
            {
                "titulo": "Resultado Demonstrativo Estoque",
                "total": _texto_moeda_apuracao(resultado_demonstrativo_estoque),
                "linhas": feedback_estoque,
            },
        ],
    }


def _valor_parametro_negocios_por_direcao(empresa, direcao_alvo, base_percentual=None):
    alvo_norm = _normalizar_chave_apuracao(direcao_alvo)
    itens = (
        ParametroNegocios.objects.filter(empresa=empresa)
        .order_by("-id")
        .values("direcao", "compromisso", "compromisso_unidade")
    )
    for item in itens:
        direcao_norm = _normalizar_chave_apuracao(item.get("direcao") or "")
        if alvo_norm not in direcao_norm:
            continue
        compromisso = Decimal(item.get("compromisso") or 0)
        unidade = str(item.get("compromisso_unidade") or ParametroNegocios.UNIDADE_VALOR)
        if unidade == ParametroNegocios.UNIDADE_PERCENTUAL:
            if base_percentual is None:
                return Decimal("0")
            return Decimal(base_percentual or 0) * (compromisso / Decimal("100"))
        return compromisso
    return Decimal("0")


def _agrupar_despesas_por_centro(orcamento_despesas_qs):
    despesas = {}
    totais_por_centro = orcamento_despesas_qs.values("centro_resultado__descricao").annotate(
        total=Coalesce(
            Sum("valor_baixa"),
            Value(Decimal("0"), output_field=DecimalField(max_digits=20, decimal_places=2)),
        )
    )
    for item in totais_por_centro:
        chave_centro = _normalizar_chave_apuracao(item.get("centro_resultado__descricao") or "")
        despesas[chave_centro] = despesas.get(chave_centro, Decimal("0")) + Decimal(item.get("total") or 0)
    return despesas


def _calcular_dashboard_apuracao(faturamento_total, lucro_liquido):
    lucro_liquido_compras = _decimal_2(lucro_liquido.get("compras") or 0)
    lucro_setorial_total = _decimal_2(
        (lucro_liquido.get("vendas") or 0)
        + (lucro_liquido.get("producao") or 0)
        + (lucro_liquido.get("logistica") or 0)
        + (lucro_liquido.get("administracao") or 0)
        + (lucro_liquido.get("financeiro") or 0)
    )
    margem_liquida_compras = (
        lucro_liquido_compras / faturamento_total if Decimal(faturamento_total or 0) != 0 else Decimal("0")
    )
    saldo_apos_setores = _decimal_2(lucro_liquido_compras - lucro_setorial_total)
    indice_saldo_apos_setores = (
        saldo_apos_setores / faturamento_total if Decimal(faturamento_total or 0) != 0 else Decimal("0")
    )

    return {
        "lucro_setorial_total": _texto_moeda_apuracao(lucro_setorial_total),
        "margem_liquida_compras": _texto_percentual_apuracao(margem_liquida_compras),
        "saldo_apos_setores": _texto_moeda_apuracao(saldo_apos_setores),
        "indice_saldo_apos_setores": _texto_percentual_apuracao(indice_saldo_apos_setores),
    }


def _montar_modulos_parametros_apuracao(usuario):
    modulos_parametros = {
        item["url"]: item
        for item in _modulos_com_acesso(usuario, "Parametros")
        if item.get("url") in _APURACAO_ORDEM_PARAMETROS
    }
    modulos_ordenados = []
    for url in _APURACAO_ORDEM_PARAMETROS:
        modulo_param = modulos_parametros.get(url)
        if not modulo_param:
            continue
        modulos_ordenados.append(
            {
                "url": url,
                "nome": _APURACAO_ROTULOS_PARAMETROS.get(url, modulo_param.get("nome") or ""),
                "permitido": bool(modulo_param.get("permitido")),
            }
        )
    return modulos_ordenados


def _contexto_tabela_apuracao_resultados(empresa, data_inicial, data_final, cmv_ajustado_percentual_ratio):
    faturamento_qs = Faturamento.objects.filter(
        empresa=empresa,
        data_faturamento__gte=data_inicial,
        data_faturamento__lte=data_final,
    )
    orcamento_despesas_qs = Orcamento.objects.filter(
        empresa=empresa,
        data_baixa__gte=data_inicial,
        data_baixa__lte=data_final,
        operacao__descricao_receita_despesa__icontains="Despesa",
    )

    faturamento_total = _sum_decimal(faturamento_qs, "valor_nota_unico", max_digits=20, decimal_places=2)
    peso_bruto_total = _sum_decimal(faturamento_qs, "peso_bruto_unico", max_digits=20, decimal_places=2)
    valor_frete_total = _sum_decimal(faturamento_qs, "valor_frete", max_digits=20, decimal_places=2)

    parametros_vendas = ParametroMargemVendas.objects.filter(empresa=empresa).order_by("id").first()
    parametros_adm = ParametroMargemAdministracao.objects.filter(empresa=empresa).order_by("id").first()
    parametros_logistica = _obter_parametro_logistica_operador(empresa)

    taxa_vendas = Decimal(getattr(parametros_vendas, "remuneracao_percentual", 0) or 0)
    taxa_adm = Decimal(getattr(parametros_adm, "remuneracao_percentual", 0) or 0)
    taxa_logistica_operador = Decimal(getattr(parametros_logistica, "remuneracao_rs", 0) or 0)
    kpi_parametros_financeiros = _calcular_kpi_parametros_financeiros(empresa, data_inicial, data_final)

    vendas_receita = _decimal_2(faturamento_total * taxa_vendas)
    producao_receita = _decimal_2(_somar_remuneracao_total_vendas(empresa, data_inicial, data_final))
    logistica_receita = _decimal_2((peso_bruto_total / Decimal("1000")) * taxa_logistica_operador + valor_frete_total)
    administracao_receita = _decimal_2(faturamento_total * taxa_adm)
    financeiro_receita = _decimal_2(kpi_parametros_financeiros.get("valor") or 0)

    despesas_por_centro = _agrupar_despesas_por_centro(orcamento_despesas_qs)

    cmv = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["cmv"])
    estoque_inicial_total = _somar_custo_total_estoque_por_data(empresa, data_inicial)
    estoque_final_total = _somar_custo_total_estoque_por_data(empresa, data_final)
    cmv_real = _decimal_2(estoque_final_total - estoque_inicial_total + cmv)
    cmv_ajustado_percentual = Decimal(cmv_ajustado_percentual_ratio)
    cmv_ajustado = _decimal_2(faturamento_total * cmv_ajustado_percentual)

    lucro_bruto_compras = _decimal_2(faturamento_total - cmv_ajustado)

    despesa_admin_total = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["administracao"])
    despesa_comercial_total = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["comercial"])
    despesa_financeiro_total = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["financeiro"])
    despesa_industria_total = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["industria"])
    despesa_logistica_total = _total_por_alias(despesas_por_centro, *_APURACAO_CENTRO_ALIASES["logistica"])

    compras_vendas = _decimal_2(-vendas_receita)
    compras_producao = _decimal_2(-producao_receita)
    compras_logistica = _decimal_2(-logistica_receita)
    compras_administracao = _decimal_2(-administracao_receita)
    compras_financeiro = _decimal_2(-financeiro_receita)
    despesas_compras = _decimal_2(
        compras_vendas + compras_producao + compras_logistica + compras_administracao + compras_financeiro
    )
    despesas_vendas = _decimal_2(despesa_comercial_total)
    despesas_producao = _decimal_2(despesa_industria_total)
    despesas_logistica = _decimal_2(despesa_logistica_total)
    despesas_administracao = _decimal_2(despesa_admin_total)
    despesas_financeiro = _decimal_2(despesa_financeiro_total)

    lucro_liquido = {
        "compras": _decimal_2(lucro_bruto_compras + despesas_compras),
        "vendas": _decimal_2(vendas_receita - despesas_vendas),
        "producao": _decimal_2(producao_receita - despesas_producao),
        "logistica": _decimal_2(logistica_receita - despesas_logistica),
        "administracao": _decimal_2(administracao_receita - despesas_administracao),
        "financeiro": _decimal_2(financeiro_receita - despesas_financeiro),
    }

    cmv_real_percentual = (cmv_real / faturamento_total) if faturamento_total else None

    linhas = [
        _linha_apuracao(
            "1 - Receita Bruta Interna",
            "secao-receita",
            {
                "compras": faturamento_total,
                "vendas": vendas_receita,
                "producao": producao_receita,
                "logistica": logistica_receita,
                "administracao": administracao_receita,
                "financeiro": financeiro_receita,
            },
        ),
        _linha_apuracao("FATURAMENTO", "item", {"compras": faturamento_total}),
        _linha_apuracao("CMV", "item", {"compras": cmv}),
        _linha_apuracao(
            "CMV Real",
            "item",
            {"compras": cmv_real},
            {"compras": cmv_real_percentual},
        ),
        _linha_apuracao(
            "CMV Ajustado",
            "item",
            {"compras": cmv_ajustado},
            {"compras": cmv_ajustado_percentual},
            {
                "compras": {
                    "editavel": True,
                    "name": "cmv_ajustado_percentual",
                    "valor": f"{(cmv_ajustado_percentual * Decimal('100')):.2f}",
                }
            },
        ),
        _linha_apuracao("2 - Lucro Bruto", "secao-lucro", {"compras": lucro_bruto_compras}),
        _linha_apuracao(
            "COMPRAS",
            "item",
            {
                "vendas": vendas_receita,
                "producao": producao_receita,
                "logistica": logistica_receita,
                "financeiro": financeiro_receita,
            },
        ),
        _linha_apuracao("VENDAS", "item", {"compras": compras_vendas}),
        _linha_apuracao("PRODUCAO", "item", {"compras": compras_producao}),
        _linha_apuracao("LOGISTICA", "item", {"compras": compras_logistica}),
        _linha_apuracao(
            "ADMINISTRACAO",
            "item",
            {
                "compras": compras_administracao,
                "administracao": administracao_receita,
            },
        ),
        _linha_apuracao("FINANCEIRO", "item", {"compras": compras_financeiro}),
        _linha_apuracao(
            "3 - Despesas",
            "secao-despesas",
            {
                "compras": despesas_compras,
                "vendas": despesas_vendas,
                "producao": despesas_producao,
                "logistica": despesas_logistica,
                "administracao": despesas_administracao,
                "financeiro": despesas_financeiro,
            },
        ),
        _linha_apuracao("ADMINISTRACAO", "item", {"administracao": despesas_administracao}),
        _linha_apuracao("COMERCIAL", "item", {"vendas": despesas_vendas}),
        _linha_apuracao("FINANCEIRO", "item", {"financeiro": despesas_financeiro}),
        _linha_apuracao("INDUSTRIA(ACUCAREIRA)", "item", {"producao": despesas_producao}),
        _linha_apuracao("LOGISTICA", "item", {"logistica": despesas_logistica}),
        _linha_apuracao("Lucro Liquido", "secao-final", lucro_liquido),
    ]

    dashboard = _calcular_dashboard_apuracao(faturamento_total, lucro_liquido)
    dashboard["parametros_financeiros"] = _texto_moeda_apuracao(kpi_parametros_financeiros.get("valor"))
    dashboard["parametros_financeiros_financeiro"] = _texto_moeda_apuracao(
        kpi_parametros_financeiros.get("resultado_demonstrativo_financeiro")
    )
    dashboard["parametros_financeiros_adiantamentos"] = _texto_moeda_apuracao(
        kpi_parametros_financeiros.get("resultado_demonstrativo_adiantamentos")
    )
    dashboard["parametros_financeiros_estoque"] = _texto_moeda_apuracao(
        kpi_parametros_financeiros.get("resultado_demonstrativo_estoque")
    )
    dashboard["parametros_financeiros_feedback"] = kpi_parametros_financeiros.get("feedback") or []

    return {
        "colunas": [{"chave": chave, "nome": nome} for chave, nome in _APURACAO_COLUNAS_SETORIAIS],
        "linhas": linhas,
        "dashboard": dashboard,
        "cmv_ajustado_percentual_ratio": cmv_ajustado_percentual,
    }


def _contexto_cards_estoque_apuracao(empresa, data_inicial, data_final):
    estoque_inicial_total = _somar_custo_total_estoque_por_data(empresa, data_inicial)
    estoque_final_total = _somar_custo_total_estoque_por_data(empresa, data_final)
    return {
        "estoque_data_inicial": data_inicial.strftime("%d/%m/%Y"),
        "estoque_data_final": data_final.strftime("%d/%m/%Y"),
        "estoque_valor_inicial": _texto_moeda_apuracao(estoque_inicial_total),
        "estoque_valor_final": _texto_moeda_apuracao(estoque_final_total),
    }


@login_required(login_url="entrar")
def apuracao_de_resultados(request, empresa_id):
    modulo = _obter_modulo("Administrativo", "Apuracao de Resultados")
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not autorizado:
        return redirect("index")

    parametros_apuracao_modulos = _montar_modulos_parametros_apuracao(request.user)

    cmv_ajustado_percentual_ratio = _parse_percentual_apuracao_para_ratio(
        request.GET.get(_APURACAO_QUERY_PARAM_CMV_AJUSTADO),
        _APURACAO_PERCENTUAL_CMV_AJUSTADO,
    )

    data_inicial_raw = request.GET.get("data_inicial")
    data_final_raw = request.GET.get("data_final")
    if not data_inicial_raw and not data_final_raw:
        data_inicial_raw = request.COOKIES.get(f"apuracao_data_inicial_{empresa.id}")
        data_final_raw = request.COOKIES.get(f"apuracao_data_final_{empresa.id}")

    data_inicial, data_final = _resolver_periodo_apuracao(
        empresa,
        data_inicial_raw,
        data_final_raw,
    )

    tabela_apuracao = _contexto_tabela_apuracao_resultados(
        empresa,
        data_inicial,
        data_final,
        cmv_ajustado_percentual_ratio,
    )
    cards_estoque = _contexto_cards_estoque_apuracao(empresa, data_inicial, data_final)

    contexto = {
        "empresa": empresa,
        "modulo_nome": modulo["nome"],
        "parametros_apuracao_modulos": parametros_apuracao_modulos,
        "data_inicial_iso": data_inicial.isoformat(),
        "data_final_iso": data_final.isoformat(),
        "apuracao_dashboard": tabela_apuracao["dashboard"],
        "apuracao_colunas": tabela_apuracao["colunas"],
        "apuracao_linhas": tabela_apuracao["linhas"],
        **cards_estoque,
    }
    resposta = render(request, modulo["template"], contexto)
    cookie_kwargs = {"max_age": 60 * 60 * 24 * 365, "samesite": "Lax"}
    resposta.set_cookie(f"apuracao_data_inicial_{empresa.id}", data_inicial.isoformat(), **cookie_kwargs)
    resposta.set_cookie(f"apuracao_data_final_{empresa.id}", data_final.isoformat(), **cookie_kwargs)
    return resposta


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
        "descricoes_perfil": _descricoes_perfil_empresa(empresa),
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

