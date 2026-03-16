def _services():
    import importlib

    return importlib.import_module("app.services")


def preparar_diretorios_carteira(empresa):
    return _services().preparar_diretorios_carteira(empresa)


def preparar_diretorios_vendas(empresa):
    return _services().preparar_diretorios_vendas(empresa)


def preparar_diretorios_pedidos_pendentes(empresa):
    return _services().preparar_diretorios_pedidos_pendentes(empresa)


def preparar_diretorios_controle_margem(empresa):
    return _services().preparar_diretorios_controle_margem(empresa)


def importar_upload_carteira(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_carteira(
        empresa=empresa,
        arquivo=arquivo,
        confirmar_substituicao=confirmar_substituicao,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_vendas(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_vendas(
        empresa=empresa,
        arquivos=arquivos,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_pedidos_pendentes(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_pedidos_pendentes(
        empresa=empresa,
        arquivo=arquivo,
        confirmar_substituicao=confirmar_substituicao,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def importar_upload_controle_margem(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    return _services().importar_upload_controle_margem(
        empresa=empresa,
        arquivo=arquivo,
        confirmar_substituicao=confirmar_substituicao,
        diretorio_importacao=diretorio_importacao,
        diretorio_subscritos=diretorio_subscritos,
        usuario=usuario,
    )


def criar_carteira_por_post(empresa, post_data):
    return _services().criar_carteira_por_post(empresa, post_data)


def atualizar_carteira_por_post(carteira, empresa, post_data):
    return _services().atualizar_carteira_por_post(carteira, empresa, post_data)


def criar_venda_por_post(empresa, post_data):
    return _services().criar_venda_por_post(empresa, post_data)


def atualizar_venda_por_post(venda, empresa, post_data):
    return _services().atualizar_venda_por_post(venda, empresa, post_data)


def criar_cidade_por_dados(empresa, nome, codigo):
    return _services().criar_cidade_por_dados(empresa, nome, codigo)


def atualizar_cidade_por_dados(cidade, nome, codigo, empresa):
    return _services().atualizar_cidade_por_dados(cidade, nome, codigo, empresa)


def criar_regiao_por_dados(empresa, nome, codigo):
    return _services().criar_regiao_por_dados(empresa, nome, codigo)


def atualizar_regiao_por_dados(regiao, nome, codigo, empresa):
    return _services().atualizar_regiao_por_dados(regiao, nome, codigo, empresa)


def criar_pedido_pendente_por_post(empresa, post_data):
    return _services().criar_pedido_pendente_por_post(empresa, post_data)


def atualizar_pedido_pendente_por_post(pedido, empresa, post_data):
    return _services().atualizar_pedido_pendente_por_post(pedido, empresa, post_data)


def criar_agenda_por_post(empresa, post_data):
    return _services().criar_agenda_por_post(empresa, post_data)


def atualizar_agenda_por_post(agenda, empresa, post_data):
    return _services().atualizar_agenda_por_post(agenda, empresa, post_data)


def criar_controle_margem_por_post(empresa, post_data):
    return _services().criar_controle_margem_por_post(empresa, post_data)


def atualizar_controle_margem_por_post(controle, empresa, post_data):
    return _services().atualizar_controle_margem_por_post(controle, empresa, post_data)
