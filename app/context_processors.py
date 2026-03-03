from .utils.modulos_permissoes import MODULOS_POR_AREA, NOMES_EXIBICAO_MODULOS


CATEGORY_LABELS = {
    "index": "Inicio",
    "financeiro": "Financeiro",
    "administrativo": "Administrativo",
    "comercial": "Comercial",
    "operacional": "Operacional",
    "parametros": "Parametros",
    "admin": "Admin",
}

CATEGORY_SEGMENTS = {
    "financeiro": "financeiro",
    "administrativo": "administrativo",
    "comercial": "comercial",
    "operacional": "operacional",
    "parametros": "parametros",
}

ADMIN_SEGMENTS = {
    "admin",
    "painel_admin",
    "criar_empresa",
    "editar_empresa",
    "excluir_empresa",
    "usuarios_permissoes",
    "cadastrar_usuario",
    "editar_usuario",
    "excluir_usuario",
}


def _display_module_name(module_name):
    return NOMES_EXIBICAO_MODULOS.get(module_name, module_name)


def _build_module_context_by_segment():
    mapping = {}
    for area, modules in MODULOS_POR_AREA.items():
        category_slug = area.lower()
        for module in modules:
            mapping[module["url"]] = {
                "category_slug": category_slug,
                "category_label": area,
                "module_label": _display_module_name(module["nome"]),
            }

    # Rotas auxiliares do modulo de Orcamento x Realizado.
    budget_ctx = mapping.get("orcamento")
    if budget_ctx:
        mapping["orcamentos"] = budget_ctx
        mapping["orcamentos_realizados"] = budget_ctx
        mapping["orcamento_x_realizado"] = budget_ctx

    # Rotas legadas ainda usadas no Comercial.
    if "agenda" not in mapping:
        mapping["agenda"] = {
            "category_slug": "comercial",
            "category_label": "Comercial",
            "module_label": "Agenda",
        }

    return mapping


MODULE_CONTEXT_BY_SEGMENT = _build_module_context_by_segment()


def _first_path_segment(path):
    value = (path or "").strip("/")
    if not value:
        return ""
    return value.split("/", 1)[0]


def navbar_context(request):
    path_segment = _first_path_segment(getattr(request, "path", ""))

    active_category = None
    current_category = None
    current_module = None

    if not path_segment:
        active_category = "index"
        current_category = CATEGORY_LABELS["index"]
    elif path_segment in CATEGORY_SEGMENTS:
        active_category = CATEGORY_SEGMENTS[path_segment]
        current_category = CATEGORY_LABELS.get(active_category)
    elif path_segment in ADMIN_SEGMENTS:
        active_category = "admin"
        current_category = CATEGORY_LABELS["admin"]
    elif path_segment in MODULE_CONTEXT_BY_SEGMENT:
        module_context = MODULE_CONTEXT_BY_SEGMENT[path_segment]
        active_category = module_context["category_slug"]
        current_category = module_context["category_label"]
        current_module = module_context["module_label"]

    return {
        "nav_active_category": active_category,
        "nav_current_category": current_category,
        "nav_current_module": current_module,
    }
