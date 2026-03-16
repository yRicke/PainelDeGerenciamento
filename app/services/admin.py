def _services():
    import importlib

    return importlib.import_module("app.services")


def usuarios_com_permissoes_ids(usuarios_qs):
    return _services().usuarios_com_permissoes_ids(usuarios_qs)


def criar_empresa_por_nome(nome, possui_sistema=False):
    return _services().criar_empresa_por_nome(nome, possui_sistema=possui_sistema)


def atualizar_empresa_por_nome(empresa, novo_nome, possui_sistema=False):
    return _services().atualizar_empresa_por_nome(empresa, novo_nome, possui_sistema=possui_sistema)


def excluir_empresa_por_id(empresa_id):
    return _services().excluir_empresa_por_id(empresa_id)


def criar_usuario_por_post(empresa, post_data, permissoes):
    return _services().criar_usuario_por_post(empresa, post_data, permissoes)


def atualizar_usuario_por_post(usuario, post_data, permissoes, usuario_logado=None):
    return _services().atualizar_usuario_por_post(usuario, post_data, permissoes, usuario_logado=usuario_logado)


def excluir_usuario_por_id(usuario_id):
    return _services().excluir_usuario_por_id(usuario_id)
