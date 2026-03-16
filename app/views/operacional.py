from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import Cargas, Cidade, Estoque, Frete, Producao, Produto, Regiao, UnidadeFederativa
from ..services.operacional import (
    atualizar_carga_por_post,
    atualizar_estoque_por_post,
    atualizar_frete_por_post,
    atualizar_producao_por_post,
    criar_carga_por_post,
    criar_estoque_por_post,
    criar_frete_por_post,
    criar_producao_por_post,
    importar_upload_cargas,
    importar_upload_estoque,
    importar_upload_fretes,
    importar_upload_producao,
    preparar_diretorios_cargas,
    preparar_diretorios_estoque,
    preparar_diretorios_fretes,
    preparar_diretorios_producao,
)
from ..tabulator import (
    build_cargas_tabulator,
    build_estoque_tabulator,
    build_fretes_tabulator,
    build_producao_tabulator,
)
from ..utils.modulos_permissoes import (
    _modulos_com_acesso,
    _obter_empresa_e_validar_permissao_modulo,
    _render_modulo_com_permissao,
)
from .shared import (
    TIPO_IMPORTACAO_POR_MODULO,
    _bloquear_criar_em_modulo_com_importacao_se_necessario,
    _bloquear_edicao_em_modulo_com_importacao_se_necessario,
    _empresa_bloqueia_cadastro_edicao_importacao,
    _montar_resumo_importacao,
    _obter_modulo,
    _resumir_arquivos_existentes,
)


@login_required(login_url="entrar")
def operacional(request):
    contexto = {
        "modulos": _modulos_com_acesso(request.user, "Operacional"),
    }
    return render(request, "operacional/operacional.html", contexto)


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
                messages.success(request, "Registro de produÃ§Ã£o criado com sucesso.")
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
            messages.error(request, "AÃ§Ã£o de produÃ§Ã£o invÃ¡lida.")
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
        messages.error(request, "Registro de produÃ§Ã£o nÃ£o encontrado.")
        return redirect("producao", empresa_id=empresa.id)

    if request.method == "POST":
        erro = atualizar_producao_por_post(producao_item, empresa, request.POST)
        if erro:
            messages.error(request, erro)
            return redirect("editar_producao_modulo", empresa_id=empresa.id, producao_id=producao_item.id)
        messages.success(request, "Registro de produÃ§Ã£o atualizado com sucesso.")
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
        messages.error(request, "Registro de produÃ§Ã£o nÃ£o encontrado.")
        return redirect("producao", empresa_id=empresa.id)

    producao_item.excluir_producao()
    messages.success(request, "Registro de produÃ§Ã£o excluÃ­do com sucesso.")
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
        messages.error(request, "Frete nÃ£o encontrado.")
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
        messages.error(request, "Frete nÃ£o encontrado.")
        return redirect("tabela_de_fretes", empresa_id=empresa.id)

    frete_item.excluir_frete()
    messages.success(request, "Frete excluÃ­do com sucesso.")
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
            messages.error(request, "AÃ§Ã£o de estoque invÃ¡lida.")
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
        messages.error(request, "Registro de estoque nÃ£o encontrado.")
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
        messages.error(request, "Registro de estoque nÃ£o encontrado.")
        return redirect("estoque_pcp", empresa_id=empresa.id)

    estoque_item.excluir_estoque()
    messages.success(request, "Registro de estoque excluÃ­do com sucesso.")
    return redirect("estoque_pcp", empresa_id=empresa.id)

