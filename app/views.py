from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import FloatField
from django.db.models.functions import Cast

from .models import Atividade, Carteira, Cidade, Colaborador, Empresa, Projeto, Regiao, Usuario
from .utils.administrativo_transformers import montar_contexto_tofu_lista
from .utils.comercial_transformers import montar_contexto_carteira
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
    importar_upload_carteira,
    usuarios_com_permissoes_ids,
    criar_empresa_por_nome,
    atualizar_empresa_por_nome,
    excluir_empresa_por_id,
    criar_usuario_por_post,
    atualizar_usuario_por_post,
    excluir_usuario_por_id,
    criar_colaborador_por_nome,
    atualizar_colaborador_por_nome,
    criar_carteira_por_post,
    atualizar_carteira_por_post,
    criar_cidade_por_dados,
    atualizar_cidade_por_dados,
    criar_projeto_por_dados,
    criar_regiao_por_dados,
    atualizar_projeto_por_dados,
    atualizar_regiao_por_dados,
)
from .tabulator import (
    build_cidades_tabulator,
    build_colaboradores_tabulator,
    build_projetos_tabulator,
    build_regioes_tabulator,
)

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


@staff_member_required(login_url="entrar")
def painel_admin(request):
    empresas = Empresa.objects.all()
    return render(request, "admin/painel_admin.html", {"empresas": empresas})


@staff_member_required(login_url="entrar")
def criar_empresa(request):
    if request.method == "POST":
        erro = criar_empresa_por_nome(request.POST.get("nome"))
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa criada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def editar_empresa(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
    if request.method == "POST":
        erro = atualizar_empresa_por_nome(empresa, request.POST.get("nome"))
        if erro:
            messages.error(request, erro)
            return redirect("painel_admin")
        messages.success(request, "Empresa atualizada com sucesso!")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def excluir_empresa(request, empresa_id):
    ok, mensagem = excluir_empresa_por_id(empresa_id)
    if ok:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def usuarios_permissoes(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
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
    empresa = Empresa.objects.get(id=empresa_id)
    if empresa and request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        criar_usuario_por_post(empresa, request.POST, permissoes)
        messages.success(request, "Usuario criado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    messages.error(request, "Empresa nao encontrada.")
    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def editar_usuario(request, usuario_id):
    usuario = Usuario.objects.get(id=usuario_id)
    if usuario and request.method == "POST":
        permissoes = _obter_permissoes_do_form(request)
        atualizar_usuario_por_post(usuario, request.POST, permissoes)
        messages.success(request, "Usuario atualizado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=usuario.empresa.id)

    messages.error(request, "Usuario nao encontrado.")
    return redirect("usuarios_permissoes", empresa_id=usuario.empresa.id)


@staff_member_required(login_url="entrar")
def excluir_usuario(request, usuario_id):
    ok, empresa_id, mensagem = excluir_usuario_por_id(usuario_id)
    if ok:
        messages.success(request, mensagem)
        return redirect("usuarios_permissoes", empresa_id=empresa_id)
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
        .select_related("projeto", "gestor", "responsavel")
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

    erro = criar_atividade_por_post(request.POST, empresa)
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
    modulo = MODULOS_POR_AREA["Financeiro"][0]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def balanco_patrimonial(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][1]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def dre(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][2]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def contas_a_receber(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][3]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def dfc(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][4]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def adiantamentos(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][5]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def contratos_redes(request, empresa_id):
    modulo = MODULOS_POR_AREA["Financeiro"][6]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def plano_de_cargos_e_salarios(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][0]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def descritivos(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][1]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def fiscal_e_contabil(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][3]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def faturamento(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][4]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def apuracao_de_resultados(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][5]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def orcamento_x_realizado(request, empresa_id):
    modulo = MODULOS_POR_AREA["Administrativo"][6]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def colaboradores(request, empresa_id):
    return colaboradores_modulo(request, empresa_id)


@login_required(login_url="entrar")
def projetos(request, empresa_id):
    return projetos_modulo(request, empresa_id)


@login_required(login_url="entrar")
def carteira(request, empresa_id):
    # 1) Autorizacao
    modulo = MODULOS_POR_AREA["Comercial"][0]
    empresa, permitido = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, modulo["nome"])
    if not permitido:
        return redirect("index")

    diretorio_importacao, diretorio_subscritos = preparar_diretorios_carteira()

    if request.method == "POST":
        acao = request.POST.get("acao")
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
            "nome_parceiro",
            "gerente",
            "vendedor",
            "valor_faturado_num",
            "limite_credito_num",
            "ultima_venda",
            "qtd_dias_sem_venda",
            "intervalo",
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

    # 3) Transformacao
    contexto = montar_contexto_carteira(
        empresa=empresa,
        modulo_nome=modulo["nome"],
        arquivo_existente=arquivos_existentes[0] if arquivos_existentes else "",
        tem_arquivo_existente=bool(arquivos_existentes),
        carteiras_qs=carteiras_qs,
        cidades=cidades,
        regioes=regioes,
        carteiras_dashboard_qs=carteiras_dashboard_qs,
    )

    # 4) Render
    return render(request, modulo["template"], contexto)


@login_required(login_url="entrar")
def editar_carteira_modulo(request, empresa_id, carteira_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Carteira")
    if not autorizado:
        return redirect("index")

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
    contexto = {
        "empresa": empresa,
        "carteira": carteira_item,
        "cidades": cidades,
        "regioes": regioes,
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
    messages.success(request, "Regiao criada com sucesso.")
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
        messages.error(request, "Regiao nao encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    erro = atualizar_regiao_por_dados(regiao, request.POST.get("nome"), request.POST.get("codigo"), empresa)
    if erro:
        messages.error(request, erro)
        return redirect("regioes", empresa_id=empresa.id)
    messages.success(request, "Regiao atualizada com sucesso.")
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
        messages.error(request, "Regiao nao encontrada.")
        return redirect("regioes", empresa_id=empresa.id)

    regiao.excluir_regiao()
    messages.success(request, "Regiao excluida com sucesso.")
    return redirect("regioes", empresa_id=empresa.id)


@login_required(login_url="entrar")
def pedidos_pendentes(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][3]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def vendas_por_categoria(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][4]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def precificacao(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][5]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def controle_de_margem(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][6]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def cargas_em_aberto(request, empresa_id):
    modulo = MODULOS_POR_AREA["Operacional"][0]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def operador_logistico(request, empresa_id):
    modulo = MODULOS_POR_AREA["Operacional"][1]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def tabela_de_fretes(request, empresa_id):
    modulo = MODULOS_POR_AREA["Operacional"][2]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def estoque_pcp(request, empresa_id):
    modulo = MODULOS_POR_AREA["Operacional"][3]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def producao(request, empresa_id):
    modulo = MODULOS_POR_AREA["Operacional"][4]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])
