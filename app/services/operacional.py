def _services():
    import importlib

    return importlib.import_module("app.services")


def preparar_diretorios_cargas(empresa):
    return _services().preparar_diretorios_cargas(empresa)


def preparar_diretorios_producao(empresa):
    return _services().preparar_diretorios_producao(empresa)


def preparar_diretorios_fretes(empresa):
    return _services().preparar_diretorios_fretes(empresa)


def preparar_diretorios_estoque(empresa):
    return _services().preparar_diretorios_estoque(empresa)


def importar_upload_cargas(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_cargas(
        empresa=empresa,
        arquivo=arquivo,
        confirmar_substituicao=confirmar_substituicao,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_fretes(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_fretes(
        empresa=empresa,
        arquivo=arquivo,
        confirmar_substituicao=confirmar_substituicao,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_estoque(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_estoque(
        empresa=empresa,
        arquivos=arquivos,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_producao(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_producao(
        empresa=empresa,
        arquivos=arquivos,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def criar_carga_por_post(empresa, post_data):
    return _services().criar_carga_por_post(empresa, post_data)


def atualizar_carga_por_post(carga, empresa, post_data):
    return _services().atualizar_carga_por_post(carga, empresa, post_data)


def criar_frete_por_post(empresa, post_data):
    return _services().criar_frete_por_post(empresa, post_data)


def atualizar_frete_por_post(frete, empresa, post_data):
    return _services().atualizar_frete_por_post(frete, empresa, post_data)


def criar_estoque_por_post(empresa, post_data):
    return _services().criar_estoque_por_post(empresa, post_data)


def atualizar_estoque_por_post(estoque, empresa, post_data):
    return _services().atualizar_estoque_por_post(estoque, empresa, post_data)


def criar_producao_por_post(empresa, post_data):
    return _services().criar_producao_por_post(empresa, post_data)


def atualizar_producao_por_post(producao_item, empresa, post_data):
    return _services().atualizar_producao_por_post(producao_item, empresa, post_data)
