from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import FloatField
from django.db.models.functions import Cast
from django.shortcuts import redirect, render

from ..models import (
    Agenda,
    Carteira,
    Cidade,
    ControleMargem,
    DescricaoPerfil,
    Motorista,
    Parceiro,
    PedidoPendente,
    Regiao,
    Rota,
    Transportadora,
    Venda,
)
from ..services.comercial import (
    atualizar_agenda_por_post,
    atualizar_carteira_por_post,
    atualizar_cidade_por_dados,
    atualizar_controle_margem_por_post,
    atualizar_pedido_pendente_por_post,
    atualizar_regiao_por_dados,
    atualizar_venda_por_post,
    criar_agenda_por_post,
    criar_carteira_por_post,
    criar_cidade_por_dados,
    criar_controle_margem_por_post,
    criar_pedido_pendente_por_post,
    criar_regiao_por_dados,
    criar_venda_por_post,
    importar_upload_carteira,
    importar_upload_controle_margem,
    importar_upload_pedidos_pendentes,
    importar_upload_vendas,
    preparar_diretorios_carteira,
    preparar_diretorios_controle_margem,
    preparar_diretorios_pedidos_pendentes,
    preparar_diretorios_vendas,
)
from ..tabulator import (
    build_agenda_tabulator,
    build_cidades_tabulator,
    build_controle_margem_tabulator,
    build_pedidos_pendentes_tabulator,
    build_regioes_tabulator,
)
from ..utils.comercial_transformers import montar_contexto_carteira, montar_contexto_vendas
from ..utils.modulos_permissoes import _obter_empresa_e_validar_permissao_modulo, _render_modulo_com_permissao
from ..utils.comercial import (
    _filtrar_controle_margem_por_situacao,
    _gerente_valido_ou_vazio,
    _normalizar_numero_unico_texto,
    _situacao_controle_margem_param_ou_none,
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


def _normalizar_lista_query(request, chave):
    valores = [str(v or "").strip() for v in request.GET.getlist(chave)]
    return [v for v in valores if v]


def _descricoes_perfil_empresa(empresa):
    return sorted(
        [
            valor
            for valor in DescricaoPerfil.objects.filter(empresa=empresa).values_list("descricao", flat=True)
            if str(valor or "").strip()
        ],
        key=lambda item: item.lower(),
    )


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
    descricoes_perfil = _descricoes_perfil_empresa(empresa)
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
    contexto["descricoes_perfil"] = descricoes_perfil

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
        "descricoes_perfil": _descricoes_perfil_empresa(empresa),
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
    messages.success(request, "RegiÃ£o criada com sucesso.")
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
        messages.error(request, "RegiÃ£o nÃ£o encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    erro = atualizar_regiao_por_dados(regiao, request.POST.get("nome"), request.POST.get("codigo"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("regioes", empresa_id=empresa.id)
    messages.success(request, "RegiÃ£o atualizada com sucesso.")
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
        messages.error(request, "RegiÃ£o nÃ£o encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    regiao.excluir_regiao()
    messages.success(request, "RegiÃ£o excluÃ­da com sucesso.")
    return redirect("regioes", empresa_id=empresa.id)


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
    total_atencao = sum(1 for item in pedidos_tabulator if item.get("status") == "AtenÃ§Ã£o")
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
        messages.error(request, "Pedido pendente nÃ£o encontrado.")
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
        messages.error(request, "Pedido pendente nÃ£o encontrado.")
        return redirect("pedidos_pendentes", empresa_id=empresa.id)

    pedido.excluir_pedido_pendente()
    messages.success(request, "Pedido pendente excluÃ­do com sucesso.")
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
        messages.error(request, "Agenda nÃ£o encontrada.")
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
        messages.error(request, "Agenda nÃ£o encontrada.")
        return redirect("agenda", empresa_id=empresa.id)

    agenda_item.excluir_agenda()
    messages.success(request, "Agenda excluÃ­da com sucesso.")
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
    descricoes_perfil = _descricoes_perfil_empresa(empresa)

    filtros_disponiveis = {
        "descricao_perfil": descricoes_perfil,
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
        "descricoes_perfil": descricoes_perfil,
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
        "descricoes_perfil": _descricoes_perfil_empresa(empresa),
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

