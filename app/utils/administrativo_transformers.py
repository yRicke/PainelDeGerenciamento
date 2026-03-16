from ..services.administrativo import calcular_dashboard_tofu
from ..tabulator import build_atividades_tabulator


def montar_contexto_tofu_lista(*, empresa, atividades_qs, projetos, colaboradores, usuario_logado):
    return {
        "empresa": empresa,
        "dashboard": calcular_dashboard_tofu(atividades_qs),
        "atividades_tabulator": build_atividades_tabulator(
            atividades_qs,
            empresa.id,
            usuario_logado=usuario_logado,
        ),
        "projetos": projetos,
        "colaboradores": colaboradores,
    }
