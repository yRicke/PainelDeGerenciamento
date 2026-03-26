from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render

from ..models import Empresa, Usuario
from ..services.admin import (
    atualizar_empresa_por_nome,
    atualizar_usuario_por_post,
    criar_empresa_por_nome,
    criar_usuario_por_post,
    excluir_empresa_por_id,
    excluir_usuario_por_id,
    usuarios_com_permissoes_ids,
)
from ..utils.modulos_permissoes import (
    MODULOS_POR_AREA,
    NOMES_EXIBICAO_MODULOS,
    _obter_permissoes_do_form,
    _obter_permissoes_por_modulo,
)


IMPORTACAO_POR_URL_MODULO = {
    "contas_a_receber": ("financeiro", "contas_a_receber"),
    "dfc": ("financeiro", "dfc"),
    "adiantamentos": ("financeiro", "adiantamentos"),
    "orcamento": ("financeiro", "orcamento"),
    "faturamento": ("administrativo", "faturamento"),
    "carteira": ("comercial", "carteira"),
    "pedidos_pendentes": ("comercial", "pedidos_pendentes"),
    "vendas_por_categoria": ("comercial", "vendas"),
    "controle_de_margem": ("comercial", "controle_de_margem"),
    "cargas_em_aberto": ("operacional", "cargas_em_aberto"),
    "tabela_de_fretes": ("operacional", "tabela_de_fretes"),
    "estoque_pcp": ("operacional", "estoque_pcp"),
    "producao": ("operacional", "producao"),
}


def _nome_exibicao_modulo(nome_modulo):
    return NOMES_EXIBICAO_MODULOS.get(nome_modulo, nome_modulo)


def _montar_modulos_subscritos_por_area():
    contexto = []
    for area_nome, modulos in MODULOS_POR_AREA.items():
        modulos_area = []
        for modulo in modulos:
            caminho_importacao = IMPORTACAO_POR_URL_MODULO.get(modulo["url"])
            if not caminho_importacao:
                continue
            area_slug, modulo_slug = caminho_importacao
            modulos_area.append(
                {
                    "chave": f"{area_slug}:{modulo_slug}",
                    "nome": _nome_exibicao_modulo(modulo["nome"]),
                    "area_slug": area_slug,
                    "modulo_slug": modulo_slug,
                }
            )
        if modulos_area:
            contexto.append(
                {
                    "nome": area_nome,
                    "modulos": modulos_area,
                }
            )
    return contexto


MODULOS_SUBSCRITOS_POR_AREA = _montar_modulos_subscritos_por_area()
MODULOS_SUBSCRITOS_POR_CHAVE = {
    modulo["chave"]: modulo
    for area in MODULOS_SUBSCRITOS_POR_AREA
    for modulo in area["modulos"]
}


def _diretorio_subscritos_empresa(*, empresa_id, area_slug, modulo_slug):
    return (
        Path(settings.BASE_DIR)
        / "importacoes"
        / area_slug
        / modulo_slug
        / str(empresa_id)
        / "subscritos"
    )


def _iterar_arquivos_subscritos(diretorio_subscritos):
    if not diretorio_subscritos.exists():
        return
    for arquivo in diretorio_subscritos.rglob("*"):
        if arquivo.is_file():
            yield arquivo


def _contar_arquivos_subscritos(diretorio_subscritos):
    return sum(1 for _ in _iterar_arquivos_subscritos(diretorio_subscritos))


def _montar_contexto_modulos_subscritos(empresa_id):
    contexto = []
    total_modulos = 0
    total_arquivos_subscritos = 0

    for area in MODULOS_SUBSCRITOS_POR_AREA:
        modulos = []
        total_area = 0
        for modulo in area["modulos"]:
            diretorio_subscritos = _diretorio_subscritos_empresa(
                empresa_id=empresa_id,
                area_slug=modulo["area_slug"],
                modulo_slug=modulo["modulo_slug"],
            )
            arquivos_subscritos = _contar_arquivos_subscritos(diretorio_subscritos)
            modulos.append(
                {
                    "chave": modulo["chave"],
                    "nome": modulo["nome"],
                    "arquivos_subscritos": arquivos_subscritos,
                }
            )
            total_modulos += 1
            total_area += arquivos_subscritos
            total_arquivos_subscritos += arquivos_subscritos
        contexto.append(
            {
                "nome": area["nome"],
                "modulos": modulos,
                "arquivos_subscritos_total": total_area,
            }
        )

    return contexto, total_modulos, total_arquivos_subscritos


def _normalizar_chaves_modulos(chaves_modulos):
    chaves_validas = [chave for chave in chaves_modulos if chave in MODULOS_SUBSCRITOS_POR_CHAVE]
    return list(dict.fromkeys(chaves_validas))


def _limpar_diretorio_subscritos(diretorio_subscritos):
    diretorio_subscritos.mkdir(parents=True, exist_ok=True)

    arquivos = list(_iterar_arquivos_subscritos(diretorio_subscritos))
    for arquivo in arquivos:
        arquivo.unlink(missing_ok=True)

    pastas = sorted(
        [pasta for pasta in diretorio_subscritos.rglob("*") if pasta.is_dir()],
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for pasta in pastas:
        try:
            pasta.rmdir()
        except OSError:
            # Ignora pasta nao vazia caso surja arquivo paralelo durante a limpeza.
            pass

    return len(arquivos)


def _limpar_subscritos_por_modulos(empresa_id, chaves_modulos):
    modulos_limpos = []
    total_arquivos_removidos = 0
    for chave in chaves_modulos:
        modulo = MODULOS_SUBSCRITOS_POR_CHAVE.get(chave)
        if not modulo:
            continue

        diretorio_subscritos = _diretorio_subscritos_empresa(
            empresa_id=empresa_id,
            area_slug=modulo["area_slug"],
            modulo_slug=modulo["modulo_slug"],
        )
        arquivos_removidos = _limpar_diretorio_subscritos(diretorio_subscritos)

        modulos_limpos.append(
            {
                "nome": modulo["nome"],
                "arquivos_removidos": arquivos_removidos,
            }
        )
        total_arquivos_removidos += arquivos_removidos
    return modulos_limpos, total_arquivos_removidos


def _valor_checkbox_possui_sistema(post_data):
    return str(post_data.get("possui_sistema", "")).strip().lower() in {"1", "true", "on", "sim", "yes"}


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
def arquivos_subscritos(request, empresa_id):
    empresa = _obter_empresa_admin_autorizada(request, empresa_id)
    if not empresa:
        return redirect("painel_admin")

    if request.method == "POST":
        chaves_unicas = _normalizar_chaves_modulos(request.POST.getlist("modulos"))

        if not chaves_unicas:
            messages.error(request, "Selecione ao menos um modulo para limpar os arquivos subscritos.")
            return redirect("arquivos_subscritos", empresa_id=empresa.id)

        modulos_limpos, total_arquivos_removidos = _limpar_subscritos_por_modulos(
            empresa.id,
            chaves_unicas,
        )
        if not modulos_limpos:
            messages.error(request, "Nenhum modulo valido foi selecionado para limpeza.")
            return redirect("arquivos_subscritos", empresa_id=empresa.id)

        nomes_modulos = ", ".join(modulo["nome"] for modulo in modulos_limpos)
        rotulo_modulos = "modulo" if len(modulos_limpos) == 1 else "modulos"
        rotulo_arquivos = "arquivo" if total_arquivos_removidos == 1 else "arquivos"
        messages.success(
            request,
            (
                f"Arquivos subscritos limpos com sucesso. {rotulo_modulos.capitalize()}: {nomes_modulos}. "
                f"{rotulo_arquivos.capitalize()} removidos: {total_arquivos_removidos}."
            ),
        )
        return redirect("arquivos_subscritos", empresa_id=empresa.id)

    modulos_por_area, total_modulos, total_arquivos_subscritos = _montar_contexto_modulos_subscritos(empresa.id)
    contexto = {
        "empresa": empresa,
        "modulos_por_area": modulos_por_area,
        "total_modulos": total_modulos,
        "total_arquivos_subscritos": total_arquivos_subscritos,
    }
    return render(request, "admin/arquivos_subscritos.html", contexto)


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

