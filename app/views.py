from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_tables2 import RequestConfig
from django.utils import timezone
from datetime import timedelta

from .models import Empresa, Usuario, Permissao, Colaborador, Projeto, Atividade
from .tables import AtividadeTable
from .utils import MODULOS_POR_AREA, _modulos_com_acesso, _obter_permissoes_por_modulo, _obter_permissoes_do_form, _obter_empresa_e_validar_permissao_tofu, _obter_empresa_e_validar_permissao_modulo, _to_int_or_none, _to_date_or_none, _render_modulo_com_permissao

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
        nome = request.POST.get("nome")
        if nome:
            Empresa.criar_empresa(nome=nome)
            messages.success(request, "Empresa criada com sucesso!")
            return redirect("painel_admin")
        messages.error(request, "O nome da empresa e obrigatorio.")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def editar_empresa(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
    if request.method == "POST":
        novo_nome = request.POST.get("nome")
        if novo_nome:
            empresa.atualizar_nome(novo_nome=novo_nome)
            messages.success(request, "Empresa atualizada com sucesso!")
            return redirect("painel_admin")
        messages.error(request, "O nome da empresa e obrigatorio.")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def excluir_empresa(request, empresa_id):
    try:
        empresa = Empresa.objects.get(id=empresa_id)
        empresa.excluir_empresa()
        messages.success(request, "Empresa excluida com sucesso!")
    except Empresa.DoesNotExist as exc:
        messages.error(request, f"Empresa nao encontrada. {exc}")
    return redirect("painel_admin")


@staff_member_required(login_url="entrar")
def usuarios_permissoes(request, empresa_id):
    empresa = Empresa.objects.get(id=empresa_id)
    usuarios = Usuario.objects.filter(empresa=empresa).prefetch_related("permissoes")

    for usuario in usuarios:
        usuario.permissoes_ids = set(usuario.permissoes.values_list("id", flat=True))

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
        nome = request.POST.get("nome")
        senha = request.POST.get("senha")
        permissoes = _obter_permissoes_do_form(request)

        Usuario.criar_usuario(
            empresa=empresa,
            username=nome,
            password=senha,
            permissoes=permissoes,
        )
        messages.success(request, "Usuario criado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)

    messages.error(request, "Empresa nao encontrada.")
    return redirect("usuarios_permissoes", empresa_id=empresa_id)


@staff_member_required(login_url="entrar")
def editar_usuario(request, usuario_id):
    usuario = Usuario.objects.get(id=usuario_id)
    if usuario and request.method == "POST":
        nome = request.POST.get("nome")
        senha = request.POST.get("senha")
        permissoes = _obter_permissoes_do_form(request)

        usuario.atualizar_usuario(
            username=nome,
            password=senha,
            permissoes=permissoes,
        )
        messages.success(request, "Usuario atualizado com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=usuario.empresa.id)

    messages.error(request, "Usuario nao encontrado.")
    return redirect("usuarios_permissoes", empresa_id=usuario.empresa.id)


@staff_member_required(login_url="entrar")
def excluir_usuario(request, usuario_id):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        empresa_id = usuario.empresa.id
        usuario.excluir_usuario()
        messages.success(request, "Usuario excluido com sucesso!")
        return redirect("usuarios_permissoes", empresa_id=empresa_id)
    except Usuario.DoesNotExist as exc:
        messages.error(request, f"Usuario nao encontrado. {exc}")
        return redirect("painel_admin")

@login_required(login_url="entrar")
def tofu_lista_de_atividades(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    atividades_qs = (
        Atividade.objects.filter(projeto__empresa=empresa)
        .select_related("projeto", "gestor", "responsavel")
        .order_by("-id")
    )
    filtro_busca = (request.GET.get("q") or "").strip()
    filtro_projeto_id = request.GET.get("projeto_id") or ""
    filtro_gestor_id = request.GET.get("gestor_id") or ""
    filtro_responsavel_id = request.GET.get("responsavel_id") or ""
    filtro_progresso = request.GET.get("progresso") or ""
    filtro_indicador = request.GET.get("indicador") or ""
    hoje = timezone.localdate()
    limite_atencao = hoje + timedelta(days=3)

    if filtro_busca:
        atividades_qs = atividades_qs.filter(
            Q(interlocutor__icontains=filtro_busca)
            | Q(historico__icontains=filtro_busca)
            | Q(tarefa__icontains=filtro_busca)
            | Q(projeto__nome__icontains=filtro_busca)
            | Q(projeto__codigo__icontains=filtro_busca)
        )
    if filtro_projeto_id:
        atividades_qs = atividades_qs.filter(projeto_id=filtro_projeto_id)
    if filtro_gestor_id:
        atividades_qs = atividades_qs.filter(gestor_id=filtro_gestor_id)
    if filtro_responsavel_id:
        atividades_qs = atividades_qs.filter(responsavel_id=filtro_responsavel_id)
    if filtro_progresso:
        atividades_qs = atividades_qs.filter(progresso=filtro_progresso)
    if filtro_indicador == "concluido":
        atividades_qs = atividades_qs.filter(progresso__gte=100)
    elif filtro_indicador == "atrasado":
        atividades_qs = atividades_qs.filter(
            progresso__lt=100,
            data_previsao_termino__lt=hoje,
        )
    elif filtro_indicador == "atencao":
        atividades_qs = atividades_qs.filter(
            progresso__lt=100,
            data_previsao_termino__gte=hoje,
            data_previsao_termino__lte=limite_atencao,
        )
    elif filtro_indicador == "em_andamento":
        atividades_qs = atividades_qs.filter(
            progresso__lt=100
        ).filter(
            Q(data_previsao_termino__isnull=True)
            | Q(data_previsao_termino__gt=limite_atencao)
        )

    atividades_table = AtividadeTable(atividades_qs)
    RequestConfig(request, paginate={"per_page": 10}).configure(atividades_table)

    projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
    colaboradores = Colaborador.objects.filter(empresa=empresa).order_by("nome")

    contexto = {
        "empresa": empresa,
        "atividades_table": atividades_table,
        "projetos": projetos,
        "colaboradores": colaboradores,
        "filtro_busca": filtro_busca,
        "filtro_projeto_id": filtro_projeto_id,
        "filtro_gestor_id": filtro_gestor_id,
        "filtro_responsavel_id": filtro_responsavel_id,
        "filtro_progresso": filtro_progresso,
        "filtro_indicador": filtro_indicador,
    }
    return render(request, "administrativo/tofu_lista_de_atividades.html", contexto)




@login_required(login_url="entrar")
def criar_atividade_tofu(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_tofu(request, empresa_id)
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    projeto = Projeto.objects.filter(id=request.POST.get("projeto_id"), empresa=empresa).first()
    if not projeto:
        messages.error(request, "Projeto invalido para esta empresa.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    gestor = Colaborador.objects.filter(
        id=_to_int_or_none(request.POST.get("gestor_id")),
        empresa=empresa,
    ).first()
    responsavel = Colaborador.objects.filter(
        id=_to_int_or_none(request.POST.get("responsavel_id")),
        empresa=empresa,
    ).first()

    try:
        Atividade.criar_atividade(
            projeto=projeto,
            gestor=gestor,
            responsavel=responsavel,
            interlocutor=request.POST.get("interlocutor", ""),
            data_previsao_inicio=_to_date_or_none(request.POST.get("data_previsao_inicio")),
            data_previsao_termino=_to_date_or_none(request.POST.get("data_previsao_termino")),
            data_finalizada=_to_date_or_none(request.POST.get("data_finalizada")),
            historico=request.POST.get("historico", ""),
            tarefa=request.POST.get("tarefa", ""),
            progresso=_to_int_or_none(request.POST.get("progresso")) or 0,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
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
        projeto = Projeto.objects.filter(id=request.POST.get("projeto_id"), empresa=empresa).first()
        if not projeto:
            messages.error(request, "Projeto invalido para esta empresa.")
            return redirect("editar_atividade_tofu", empresa_id=empresa.id, atividade_id=atividade.id)

        gestor = Colaborador.objects.filter(
            id=_to_int_or_none(request.POST.get("gestor_id")),
            empresa=empresa,
        ).first()
        responsavel = Colaborador.objects.filter(
            id=_to_int_or_none(request.POST.get("responsavel_id")),
            empresa=empresa,
        ).first()

        try:
            atividade.atualizar_atividade(
                projeto=projeto,
                gestor=gestor,
                responsavel=responsavel,
                interlocutor=request.POST.get("interlocutor", ""),
                data_previsao_inicio=_to_date_or_none(request.POST.get("data_previsao_inicio")),
                data_previsao_termino=_to_date_or_none(request.POST.get("data_previsao_termino")),
                data_finalizada=_to_date_or_none(request.POST.get("data_finalizada")),
                historico=request.POST.get("historico", ""),
                tarefa=request.POST.get("tarefa", ""),
                progresso=_to_int_or_none(request.POST.get("progresso")) or 0,
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("editar_atividade_tofu", empresa_id=empresa.id, atividade_id=atividade.id)
        messages.success(request, "Atividade atualizada com sucesso.")
        return redirect("tofu_lista_de_atividades", empresa_id=empresa.id)

    projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
    colaboradores = Colaborador.objects.filter(empresa=empresa).order_by("nome")
    contexto = {
        "empresa": empresa,
        "atividade": atividade,
        "projetos": projetos,
        "colaboradores": colaboradores,
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
    contexto = {
        "empresa": empresa,
        "colaboradores": colaboradores,
    }
    return render(request, "administrativo/colaboradores.html", contexto)


@login_required(login_url="entrar")
def criar_colaborador_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Colaboradores")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("colaboradores", empresa_id=empresa.id)

    nome = (request.POST.get("nome") or "").strip()
    if not nome:
        messages.error(request, "Nome do colaborador e obrigatorio.")
        return redirect("colaboradores", empresa_id=empresa.id)

    Colaborador.criar_colaborador(nome=nome, empresa=empresa)
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

    nome = (request.POST.get("nome") or "").strip()
    if not nome:
        messages.error(request, "Nome do colaborador e obrigatorio.")
        return redirect("colaboradores", empresa_id=empresa.id)

    colaborador.atualizar_colaborador(novo_nome=nome)
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
    contexto = {
        "empresa": empresa,
        "projetos": projetos,
    }
    return render(request, "administrativo/projetos.html", contexto)


@login_required(login_url="entrar")
def criar_projeto_modulo(request, empresa_id):
    empresa, autorizado = _obter_empresa_e_validar_permissao_modulo(request, empresa_id, "Projetos")
    if not autorizado:
        return redirect("index")

    if request.method != "POST":
        return redirect("projetos", empresa_id=empresa.id)

    nome = (request.POST.get("nome") or "").strip()
    codigo = (request.POST.get("codigo") or "").strip()
    if not nome:
        messages.error(request, "Nome do projeto e obrigatorio.")
        return redirect("projetos", empresa_id=empresa.id)

    Projeto.criar_projeto(nome=nome, empresa=empresa, codigo=codigo)
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

    nome = (request.POST.get("nome") or "").strip()
    codigo = (request.POST.get("codigo") or "").strip()
    if not nome:
        messages.error(request, "Nome do projeto e obrigatorio.")
        return redirect("projetos", empresa_id=empresa.id)

    projeto.atualizar_projeto(novo_nome=nome, novo_codigo=codigo)
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
    modulo = MODULOS_POR_AREA["Comercial"][0]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def pedidos_pendentes(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][1]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def vendas_por_categoria(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][2]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def precificacao(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][3]
    return _render_modulo_com_permissao(request, empresa_id, modulo["nome"], modulo["template"])


@login_required(login_url="entrar")
def controle_de_margem(request, empresa_id):
    modulo = MODULOS_POR_AREA["Comercial"][4]
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
