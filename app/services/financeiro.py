from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import unicodedata

FATURAMENTO_SUBPASTA_DIARIO = "1 - Faturamento diario"
FATURAMENTO_SUBPASTA_PRODUTOS = "2 - Venda por Produto (NF)"


def _services():
    import importlib

    return importlib.import_module("app.services")


def preparar_diretorios_dfc(empresa):
    services = _services()
    return services._preparar_diretorios_importacao(area="financeiro", modulo="dfc", empresa=empresa)


def preparar_diretorios_faturamento(empresa):
    services = _services()
    return services._preparar_diretorios_importacao(area="administrativo", modulo="faturamento", empresa=empresa)


def preparar_diretorios_adiantamentos(empresa):
    services = _services()
    return services._preparar_diretorios_importacao(area="financeiro", modulo="adiantamentos", empresa=empresa)


def preparar_diretorios_contas_a_receber(empresa):
    services = _services()
    return services._preparar_diretorios_importacao(area="financeiro", modulo="contas_a_receber", empresa=empresa)


def preparar_diretorios_orcamento(empresa):
    services = _services()
    return services._preparar_diretorios_importacao(area="financeiro", modulo="orcamento", empresa=empresa)


def importar_upload_dfc(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    if not arquivo:
        return False, "Selecione um arquivo .xls para importar."

    nome_arquivo = Path(arquivo.name).name
    if not nome_arquivo.lower().endswith(".xls"):
        return False, "Formato invalido. Envie apenas arquivo .xls."

    arquivos_existentes = [f for f in diretorio_importacao.iterdir() if f.is_file()]
    if arquivos_existentes and not confirmar_substituicao:
        return False, "Ja existe arquivo na pasta. Confirme a substituicao para continuar."

    for arquivo_antigo in arquivos_existentes:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        arquivo_antigo.rename(destino_subscrito)

    destino = diretorio_importacao / nome_arquivo
    with destino.open("wb+") as file_out:
        for chunk in arquivo.chunks():
            file_out.write(chunk)

    try:
        services = _services()
        resultado = services.importar_dfc_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar DFC: {exc}"

    try:
        services._registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            empresa=empresa,
            modulo="dfc",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = services._detalhe_erro_importacao(resultado, "dfc", "entradas de DFC importadas")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, dfc: {resultado['dfc']}."
        ),
    )


def _normalizar_token_faturamento(valor):
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9]+", "", texto)
    return texto


def _subpasta_faturamento_por_nome_arquivo(nome_arquivo):
    caminho = str(nome_arquivo or "").replace("\\", "/")
    partes = [parte for parte in caminho.split("/") if str(parte).strip()]
    tokens = {_normalizar_token_faturamento(parte) for parte in partes}

    if _normalizar_token_faturamento(FATURAMENTO_SUBPASTA_DIARIO) in tokens:
        return FATURAMENTO_SUBPASTA_DIARIO
    if _normalizar_token_faturamento(FATURAMENTO_SUBPASTA_PRODUTOS) in tokens:
        return FATURAMENTO_SUBPASTA_PRODUTOS

    return None


def _inferir_subpasta_faturamento_por_conteudo(caminho_arquivo: Path):
    aliases_diario = {
        "nome_parceiro_base": {"nomeparceiroparceiro"},
        "numero_nota": {"nronota", "numeronota"},
        "valor_nota": {"vlrnota"},
        "descricao_tipo_operacao": {"descricaotipodeoperacao"},
        "data_faturamento": {"dtdofaturamento", "datafaturamento"},
    }
    aliases_produtos = {
        "produto": {"produto"},
        "nota_fiscal": {"notafiscal", "nronota", "numeronota"},
        "qtd_saida": {"qtdsaida", "qntsaida", "quantidadesaida"},
    }

    try:
        services = _services()
        for idx, linha in enumerate(services._iterar_linhas_xlsx(caminho_arquivo)):
            if idx > 30:
                break
            if not any(str(celula or "").strip() for celula in linha):
                continue

            normalizadas = {_normalizar_token_faturamento(celula) for celula in linha if str(celula or "").strip()}
            if not normalizadas:
                continue

            diario_ok = all(any(alias in normalizadas for alias in aliases) for aliases in aliases_diario.values())
            if diario_ok:
                return FATURAMENTO_SUBPASTA_DIARIO

            produtos_ok = all(any(alias in normalizadas for alias in aliases) for aliases in aliases_produtos.values())
            if produtos_ok:
                return FATURAMENTO_SUBPASTA_PRODUTOS
    except Exception:
        return None

    return None


def _destino_unico(destino_pasta: Path, nome_arquivo: str) -> Path:
    destino = destino_pasta / nome_arquivo
    if not destino.exists():
        return destino

    stem = Path(nome_arquivo).stem
    suffix = Path(nome_arquivo).suffix
    indice = 2
    while True:
        candidato = destino_pasta / f"{stem}_{indice}{suffix}"
        if not candidato.exists():
            return candidato
        indice += 1


def importar_upload_faturamento(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    arquivos_xlsx = []
    for idx, arquivo in enumerate(arquivos or [], start=1):
        nome_original = str(getattr(arquivo, "name", "") or "")
        nome_base = Path(nome_original).name
        if not nome_base.lower().endswith(".xlsx"):
            continue
        if nome_base.startswith("~$") or nome_base.startswith("."):
            continue
        subpasta_hint = _subpasta_faturamento_por_nome_arquivo(nome_original)
        arquivos_xlsx.append((idx, arquivo, nome_original, nome_base, subpasta_hint))

    if not arquivos_xlsx:
        return False, "Selecione uma pasta com arquivos .xlsx para importar."

    for item_antigo in [f for f in diretorio_importacao.iterdir() if f.name != diretorio_subscritos.name]:
        destino_subscrito = diretorio_subscritos / item_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{item_antigo.stem}_{timestamp}{item_antigo.suffix}"
        shutil.move(str(item_antigo), str(destino_subscrito))

    diretorio_tmp = diretorio_importacao / "_tmp_classificacao"
    if diretorio_tmp.exists():
        shutil.rmtree(diretorio_tmp)
    diretorio_tmp.mkdir(parents=True, exist_ok=True)

    arquivos_staged = []
    for indice, arquivo_upload, nome_original, nome_base, subpasta_hint in arquivos_xlsx:
        nome_temp = f"{indice:04d}__{nome_base}"
        destino_temp = diretorio_tmp / nome_temp
        with destino_temp.open("wb+") as file_out:
            for chunk in arquivo_upload.chunks():
                file_out.write(chunk)
        arquivos_staged.append((destino_temp, nome_original, nome_base, subpasta_hint))

    nomes_lote = []
    possui_diario = False
    possui_produtos = False

    for caminho_temp, nome_original, nome_arquivo, subpasta_hint in arquivos_staged:
        subpasta = subpasta_hint or _inferir_subpasta_faturamento_por_conteudo(caminho_temp)
        if not subpasta:
            # Fallback minimo quando o navegador nao envia caminho relativo.
            if re.match(r"^\d{2}\.\d{2}\.\d{4}\.xlsx$", nome_arquivo, flags=re.IGNORECASE):
                subpasta = FATURAMENTO_SUBPASTA_DIARIO
            else:
                subpasta = FATURAMENTO_SUBPASTA_PRODUTOS

        if subpasta == FATURAMENTO_SUBPASTA_DIARIO:
            possui_diario = True
        if subpasta == FATURAMENTO_SUBPASTA_PRODUTOS:
            possui_produtos = True

        destino_pasta = diretorio_importacao / subpasta
        destino_pasta.mkdir(parents=True, exist_ok=True)
        destino = _destino_unico(destino_pasta, nome_arquivo)
        shutil.move(str(caminho_temp), str(destino))
        nomes_lote.append(str(Path(subpasta) / destino.name))

    if diretorio_tmp.exists():
        shutil.rmtree(diretorio_tmp)

    if not possui_diario or not possui_produtos:
        return (
            False,
            (
                "Estrutura invalida. Selecione a pasta mae contendo as subpastas "
                "'1 - Faturamento diario' e '2 - Venda por Produto (NF)'."
            ),
        )

    try:
        services = _services()
        resultado = services.importar_faturamento_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Faturamento: {exc}"

    try:
        services._registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            empresa=empresa,
            modulo="faturamento",
            usuario=usuario,
            arquivos=nomes_lote,
        )
    except Exception:
        pass

    detalhe = services._detalhe_erro_importacao(resultado, "faturamento", "registros de faturamento importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, faturamento: {resultado['faturamento']}."
        ),
    )


def importar_upload_adiantamentos(
    *,
    empresa,
    arquivo,
    confirmar_substituicao,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    if not arquivo:
        return False, "Selecione um arquivo .xls para importar."

    nome_arquivo = Path(arquivo.name).name
    if not nome_arquivo.lower().endswith(".xls"):
        return False, "Formato invalido. Envie apenas arquivo .xls."

    arquivos_existentes = [f for f in diretorio_importacao.iterdir() if f.is_file()]
    if arquivos_existentes and not confirmar_substituicao:
        return False, "Ja existe arquivo na pasta. Confirme a substituicao para continuar."

    for arquivo_antigo in arquivos_existentes:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        arquivo_antigo.rename(destino_subscrito)

    destino = diretorio_importacao / nome_arquivo
    with destino.open("wb+") as file_out:
        for chunk in arquivo.chunks():
            file_out.write(chunk)

    try:
        services = _services()
        resultado = services.importar_adiantamentos_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Adiantamentos: {exc}"

    try:
        services._registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            empresa=empresa,
            modulo="adiantamentos",
            usuario=usuario,
            arquivos=[nome_arquivo],
        )
    except Exception:
        pass

    detalhe = services._detalhe_erro_importacao(resultado, "adiantamentos", "registros de Adiantamentos importados")
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, adiantamentos: {resultado['adiantamentos']}."
        ),
    )


def importar_upload_contas_a_receber(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    arquivos_xls = []
    for arquivo in arquivos or []:
        nome_arquivo = Path(arquivo.name).name
        if nome_arquivo.lower().endswith(".xls"):
            arquivos_xls.append((arquivo, nome_arquivo))

    if not arquivos_xls:
        return False, "Selecione ao menos um arquivo .xls para importar."

    for arquivo_antigo in [f for f in diretorio_importacao.iterdir() if f.is_file()]:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        shutil.move(str(arquivo_antigo), str(destino_subscrito))

    for arquivo_upload, nome_arquivo in arquivos_xls:
        destino = diretorio_importacao / nome_arquivo
        with destino.open("wb+") as file_out:
            for chunk in arquivo_upload.chunks():
                file_out.write(chunk)

    try:
        services = _services()
        resultado = services.importar_contas_a_receber_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Contas a Receber: {exc}"

    try:
        services._registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            empresa=empresa,
            modulo="contas_a_receber",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = services._detalhe_erro_importacao(
        resultado,
        "contas_a_receber",
        "contas a receber importadas",
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado['arquivos']}, "
            f"linhas: {resultado['linhas']}, contas: {resultado['contas_a_receber']}."
        ),
    )


def importar_upload_orcamento(
    *,
    empresa,
    arquivos,
    diretorio_importacao,
    diretorio_subscritos,
    usuario=None,
):
    arquivos_xls = []
    for arquivo in arquivos or []:
        nome_arquivo = Path(arquivo.name).name
        if nome_arquivo.lower().endswith(".xls"):
            arquivos_xls.append((arquivo, nome_arquivo))

    if not arquivos_xls:
        return False, "Selecione ao menos um arquivo .xls para importar."

    for arquivo_antigo in [f for f in diretorio_importacao.iterdir() if f.is_file()]:
        destino_subscrito = diretorio_subscritos / arquivo_antigo.name
        if destino_subscrito.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino_subscrito = diretorio_subscritos / f"{arquivo_antigo.stem}_{timestamp}{arquivo_antigo.suffix}"
        shutil.move(str(arquivo_antigo), str(destino_subscrito))

    for arquivo_upload, nome_arquivo in arquivos_xls:
        destino = diretorio_importacao / nome_arquivo
        with destino.open("wb+") as file_out:
            for chunk in arquivo_upload.chunks():
                file_out.write(chunk)

    try:
        services = _services()
        resultado_realizados = services.importar_orcamento_do_diretorio(
            empresa=empresa,
            diretorio=str(diretorio_importacao),
            limpar_antes=True,
        )
    except Exception as exc:
        return False, f"Falha ao importar Orcamento: {exc}"

    try:
        services._registrar_metadados_importacao(
            diretorio_subscritos=diretorio_subscritos,
            empresa=empresa,
            modulo="orcamento",
            usuario=usuario,
            arquivos=[nome_arquivo for _, nome_arquivo in arquivos_xls],
        )
    except Exception:
        pass

    detalhe = services._detalhe_erro_importacao(
        resultado_realizados,
        "orcamentos",
        "orcamentos importados",
    )
    if detalhe:
        return False, detalhe

    return (
        True,
        (
            f"Importacao concluida. Arquivos: {resultado_realizados['arquivos']}, "
            f"linhas realizados: {resultado_realizados['linhas']}, "
            f"orcamentos realizados: {resultado_realizados['orcamentos']}."
        ),
    )


def criar_titulo_por_dados(empresa, tipo_titulo_codigo, descricao):
    return _services().criar_titulo_por_dados(empresa, tipo_titulo_codigo, descricao)


def atualizar_titulo_por_dados(titulo, tipo_titulo_codigo, descricao, empresa):
    return _services().atualizar_titulo_por_dados(titulo, tipo_titulo_codigo, descricao, empresa)


def criar_natureza_por_dados(empresa, codigo, descricao):
    return _services().criar_natureza_por_dados(empresa, codigo, descricao)


def atualizar_natureza_por_dados(natureza, codigo, descricao, empresa):
    return _services().atualizar_natureza_por_dados(natureza, codigo, descricao, empresa)


def criar_operacao_por_dados(empresa, tipo_operacao_codigo, descricao_receita_despesa):
    return _services().criar_operacao_por_dados(empresa, tipo_operacao_codigo, descricao_receita_despesa)


def atualizar_operacao_por_dados(operacao, tipo_operacao_codigo, descricao_receita_despesa, empresa):
    return _services().atualizar_operacao_por_dados(
        operacao,
        tipo_operacao_codigo,
        descricao_receita_despesa,
        empresa,
    )


def criar_centro_resultado_por_dados(empresa, descricao):
    return _services().criar_centro_resultado_por_dados(empresa, descricao)


def atualizar_centro_resultado_por_dados(centro_resultado, descricao, empresa):
    return _services().atualizar_centro_resultado_por_dados(centro_resultado, descricao, empresa)


def criar_contrato_rede_por_post(empresa, post_data):
    return _services().criar_contrato_rede_por_post(empresa, post_data)


def atualizar_contrato_rede_por_post(contrato, empresa, post_data):
    return _services().atualizar_contrato_rede_por_post(contrato, empresa, post_data)


def criar_dfc_por_post(empresa, post_data):
    return _services().criar_dfc_por_post(empresa, post_data)


def atualizar_dfc_por_post(dfc_item, empresa, post_data):
    return _services().atualizar_dfc_por_post(dfc_item, empresa, post_data)


def construir_payload_tabela_saldo_dfc(empresa, dfc_registros, hoje=None, dias_periodo=10):
    return _services().construir_payload_tabela_saldo_dfc(
        empresa,
        dfc_registros,
        hoje=hoje,
        dias_periodo=dias_periodo,
    )


def salvar_dfc_saldo_manual_por_post(empresa, post_data):
    return _services().salvar_dfc_saldo_manual_por_post(empresa, post_data)


def criar_adiantamento_por_post(empresa, post_data):
    return _services().criar_adiantamento_por_post(empresa, post_data)


def atualizar_adiantamento_por_post(adiantamento_item, post_data):
    return _services().atualizar_adiantamento_por_post(adiantamento_item, post_data)


def criar_contas_a_receber_por_post(empresa, post_data):
    return _services().criar_contas_a_receber_por_post(empresa, post_data)


def atualizar_contas_a_receber_por_post(conta_item, empresa, post_data):
    return _services().atualizar_contas_a_receber_por_post(conta_item, empresa, post_data)


def criar_orcamento_por_post(empresa, post_data):
    return _services().criar_orcamento_por_post(empresa, post_data)


def atualizar_orcamento_por_post(orcamento_item, empresa, post_data):
    return _services().atualizar_orcamento_por_post(orcamento_item, empresa, post_data)


def criar_orcamento_planejado_por_post(empresa, post_data):
    return _services().criar_orcamento_planejado_por_post(empresa, post_data)


def atualizar_orcamento_planejado_por_post(orcamento_planejado_item, empresa, post_data):
    return _services().atualizar_orcamento_planejado_por_post(
        orcamento_planejado_item,
        empresa,
        post_data,
    )


def criar_parametro_margem_financeiro(empresa, post_data):
    return _services().criar_parametro_margem_financeiro(empresa, post_data)


def atualizar_parametro_margem_financeiro(item, empresa, post_data):
    return _services().atualizar_parametro_margem_financeiro(item, empresa, post_data)


def excluir_parametro_margem_financeiro(item, empresa):
    return _services().excluir_parametro_margem_financeiro(item, empresa)
