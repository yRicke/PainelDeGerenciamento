def _services():
    import importlib

    return importlib.import_module("app.services")


def criar_parceiro_por_dados(empresa, nome, codigo, cidade_id=None):
    return _services().criar_parceiro_por_dados(empresa, nome, codigo, cidade_id=cidade_id)


def atualizar_parceiro_por_dados(parceiro, nome, codigo, empresa, cidade_id=None):
    return _services().atualizar_parceiro_por_dados(parceiro, nome, codigo, empresa, cidade_id=cidade_id)


def criar_empresa_titular_por_dados(empresa, codigo, nome):
    return _services().criar_empresa_titular_por_dados(empresa, codigo, nome)


def atualizar_empresa_titular_por_dados(empresa_titular, empresa, codigo, nome):
    return _services().atualizar_empresa_titular_por_dados(empresa_titular, empresa, codigo, nome)


def excluir_empresa_titular_por_dados(empresa_titular, empresa):
    return _services().excluir_empresa_titular_por_dados(empresa_titular, empresa)


def criar_banco_por_dados(empresa, nome):
    return _services().criar_banco_por_dados(empresa, nome)


def atualizar_banco_por_dados(banco, empresa, nome):
    return _services().atualizar_banco_por_dados(banco, empresa, nome)


def excluir_banco_por_dados(banco, empresa):
    return _services().excluir_banco_por_dados(banco, empresa)


def criar_conta_bancaria_por_dados(empresa, post_data):
    return _services().criar_conta_bancaria_por_dados(empresa, post_data)


def atualizar_conta_bancaria_por_dados(conta_bancaria, empresa, post_data):
    return _services().atualizar_conta_bancaria_por_dados(conta_bancaria, empresa, post_data)


def excluir_conta_bancaria_por_dados(conta_bancaria, empresa):
    return _services().excluir_conta_bancaria_por_dados(conta_bancaria, empresa)


def criar_parametro_margem_vendas(empresa, post_data):
    return _services().criar_parametro_margem_vendas(empresa, post_data)


def atualizar_parametro_margem_vendas(item, empresa, post_data):
    return _services().atualizar_parametro_margem_vendas(item, empresa, post_data)


def excluir_parametro_margem_vendas(item, empresa):
    return _services().excluir_parametro_margem_vendas(item, empresa)


def criar_parametro_margem_logistica(empresa, post_data):
    return _services().criar_parametro_margem_logistica(empresa, post_data)


def atualizar_parametro_margem_logistica(item, empresa, post_data):
    return _services().atualizar_parametro_margem_logistica(item, empresa, post_data)


def excluir_parametro_margem_logistica(item, empresa):
    return _services().excluir_parametro_margem_logistica(item, empresa)


def criar_parametro_margem_financeiro(empresa, post_data):
    return _services().criar_parametro_margem_financeiro(empresa, post_data)


def atualizar_parametro_margem_financeiro(item, empresa, post_data):
    return _services().atualizar_parametro_margem_financeiro(item, empresa, post_data)


def excluir_parametro_margem_financeiro(item, empresa):
    return _services().excluir_parametro_margem_financeiro(item, empresa)


def salvar_parametro_margem_administracao(empresa, post_data):
    return _services().salvar_parametro_margem_administracao(empresa, post_data)


def criar_parametro_negocios(empresa, post_data):
    return _services().criar_parametro_negocios(empresa, post_data)


def atualizar_parametro_negocios(item, empresa, post_data):
    return _services().atualizar_parametro_negocios(item, empresa, post_data)


def excluir_parametro_negocios(item, empresa):
    return _services().excluir_parametro_negocios(item, empresa)


def criar_produto_por_dados(empresa, post_data):
    return _services().criar_produto_por_dados(empresa, post_data)


def atualizar_produto_por_dados(produto, post_data, empresa):
    return _services().atualizar_produto_por_dados(produto, post_data, empresa)


def criar_unidade_federativa_por_dados(empresa, codigo, sigla):
    return _services().criar_unidade_federativa_por_dados(empresa, codigo, sigla)


def atualizar_unidade_federativa_por_dados(unidade_federativa, codigo, sigla, empresa):
    return _services().atualizar_unidade_federativa_por_dados(unidade_federativa, codigo, sigla, empresa)


def criar_motorista_por_dados(empresa, codigo_motorista, nome):
    return _services().criar_motorista_por_dados(empresa, codigo_motorista, nome)


def atualizar_motorista_por_dados(motorista, codigo_motorista, nome, empresa):
    return _services().atualizar_motorista_por_dados(motorista, codigo_motorista, nome, empresa)


def criar_transportadora_por_dados(empresa, codigo_transportadora, nome):
    return _services().criar_transportadora_por_dados(empresa, codigo_transportadora, nome)


def atualizar_transportadora_por_dados(transportadora, codigo_transportadora, nome, empresa):
    return _services().atualizar_transportadora_por_dados(transportadora, codigo_transportadora, nome, empresa)


def criar_rota_por_dados(empresa, codigo_rota, nome, uf_id=None):
    return _services().criar_rota_por_dados(empresa, codigo_rota, nome, uf_id=uf_id)


def atualizar_rota_por_dados(rota, codigo_rota, nome, empresa, uf_id=None):
    return _services().atualizar_rota_por_dados(rota, codigo_rota, nome, empresa, uf_id=uf_id)


def criar_descricao_perfil_por_dados(empresa, descricao):
    return _services().criar_descricao_perfil_por_dados(empresa, descricao)


def atualizar_descricao_perfil_por_dados(item, descricao, empresa):
    return _services().atualizar_descricao_perfil_por_dados(item, descricao, empresa)


def criar_descricao_bp_por_dados(empresa, descricao):
    return _services().criar_descricao_bp_por_dados(empresa, descricao)


def atualizar_descricao_bp_por_dados(item, descricao, empresa):
    return _services().atualizar_descricao_bp_por_dados(item, descricao, empresa)


def criar_parametro_meta_por_dados(empresa, post_data):
    return _services().criar_parametro_meta_por_dados(empresa, post_data)


def atualizar_parametro_meta_por_dados(item, empresa, post_data):
    return _services().atualizar_parametro_meta_por_dados(item, empresa, post_data)
