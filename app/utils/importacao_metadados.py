from pathlib import Path


IMPORTACAO_METADATA_FILE_PREFIX = "_ultimo_import_empresa_"


def nome_metadados_importacao_por_empresa_id(empresa_id):
    return f"{IMPORTACAO_METADATA_FILE_PREFIX}{int(empresa_id)}.json"


def caminho_metadados_importacao(diretorio_importacao, empresa_id):
    return Path(diretorio_importacao) / nome_metadados_importacao_por_empresa_id(empresa_id)
