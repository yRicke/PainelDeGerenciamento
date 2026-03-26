def _services():
    import importlib

    return importlib.import_module("app.services")


def criar_atividade_por_post(post_data, empresa, usuario=None):
    return _services().criar_atividade_por_post(post_data, empresa, usuario=usuario)


def atualizar_atividade_por_post(atividade, post_data, empresa):
    return _services().atualizar_atividade_por_post(atividade, post_data, empresa)


def semana_iso_input_atividade(atividade):
    return _services().semana_iso_input_atividade(atividade)


def criar_colaborador_por_nome(empresa, nome):
    return _services().criar_colaborador_por_nome(empresa, nome)


def atualizar_colaborador_por_nome(colaborador, nome):
    return _services().atualizar_colaborador_por_nome(colaborador, nome)


def criar_projeto_por_dados(empresa, nome, codigo):
    return _services().criar_projeto_por_dados(empresa, nome, codigo)


def atualizar_projeto_por_dados(projeto, nome, codigo):
    return _services().atualizar_projeto_por_dados(projeto, nome, codigo)


def criar_plano_cargo_salario_por_post(empresa, post_data):
    return _services().criar_plano_cargo_salario_por_post(empresa, post_data)


def atualizar_plano_cargo_salario_por_post(item, empresa, post_data):
    return _services().atualizar_plano_cargo_salario_por_post(item, empresa, post_data)


def criar_descritivo_por_post(empresa, post_data):
    return _services().criar_descritivo_por_post(empresa, post_data)


def atualizar_descritivo_por_post(item, empresa, post_data):
    return _services().atualizar_descritivo_por_post(item, empresa, post_data)


def preparar_diretorios_faturamento(empresa):
    return _services().preparar_diretorios_faturamento(empresa)


def importar_upload_faturamento(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_faturamento(
        empresa=empresa,
        arquivos=arquivos,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def criar_faturamento_por_post(empresa, post_data):
    return _services().criar_faturamento_por_post(empresa, post_data)


def atualizar_faturamento_por_post(faturamento_item, post_data):
    return _services().atualizar_faturamento_por_post(faturamento_item, post_data)


def calcular_dashboard_tofu(atividades_qs):
    return _services().calcular_dashboard_tofu(atividades_qs)
