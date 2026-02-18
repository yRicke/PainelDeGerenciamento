from __future__ import annotations

import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction

from ..models import (
    CentroResultado,
    ContasAReceber,
    FluxoDeCaixaDFC,
    Natureza,
    Operacao,
    Parceiro,
    Titulo,
)

try:
    import xlrd
except ModuleNotFoundError:  # pragma: no cover - dependencia opcional em tempo de execucao
    xlrd = None


def _normalizar_texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _normalizar_codigo(valor) -> str:
    texto = _normalizar_texto(valor)
    if not texto:
        return ""
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def _to_decimal(valor, decimal_places: int = 2) -> Decimal:
    texto = _normalizar_texto(valor)
    if not texto:
        return Decimal("0")

    texto = texto.replace("R$", "").replace(" ", "")
    texto_lower = texto.lower()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1 and "e" not in texto_lower:
        texto = texto.replace(".", "")

    try:
        decimal_valor = Decimal(texto)
    except InvalidOperation:
        return Decimal("0")

    escala = Decimal("1").scaleb(-decimal_places)
    try:
        decimal_valor = decimal_valor.quantize(escala)
    except InvalidOperation:
        return Decimal("0")
    return decimal_valor


def _excel_date(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return None

    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass

    try:
        serial = float(texto.replace(",", "."))
    except ValueError:
        return None

    if serial <= 0:
        return None
    return (datetime(1899, 12, 30) + timedelta(days=serial)).date()


def _normalizar_nome_coluna(valor: str) -> str:
    texto = _normalizar_texto(valor).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return "".join(ch for ch in texto if ch.isalnum())

def _codigo_a_partir_descricao(prefixo: str, descricao: str, tamanho_max: int = 50) -> str:
    texto = _normalizar_texto(descricao)
    if not texto:
        return ""
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    base = "".join(ch for ch in base.upper() if ch.isalnum())
    if not base:
        return ""
    codigo = f"{prefixo}{base}"
    return codigo[:tamanho_max]


def _iterar_linhas_xls(caminho: Path):
    if xlrd is None:
        raise RuntimeError("Dependencia 'xlrd' nao encontrada. Instale com: pip install xlrd==2.0.1")

    workbook = xlrd.open_workbook(str(caminho))
    if workbook.nsheets <= 0:
        return

    sheet = workbook.sheet_by_index(0)
    for row_idx in range(sheet.nrows):
        linha = []
        for col_idx in range(sheet.ncols):
            valor = sheet.cell_value(row_idx, col_idx)
            if isinstance(valor, float) and valor.is_integer():
                valor = int(valor)
            linha.append(valor)
        yield linha


def _extrair_data_do_nome_arquivo(nome_arquivo: str):
    base = Path(nome_arquivo).stem
    padroes = [
        r"(\d{1,2})[._\-/\s](\d{1,2})[._\-/\s](\d{4})",
        r"(\d{4})[._\-/\s](\d{1,2})[._\-/\s](\d{1,2})",
        r"(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)",
        r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)",
    ]
    for padrao in padroes:
        match = re.search(padrao, base)
        if not match:
            continue
        grupos = match.groups()
        try:
            if len(grupos[0]) == 4:
                return date(int(grupos[0]), int(grupos[1]), int(grupos[2]))
            return date(int(grupos[2]), int(grupos[1]), int(grupos[0]))
        except ValueError:
            continue
    return None


def _data_arquivo_nao_nula(caminho_arquivo: Path):
    data_arquivo = _extrair_data_do_nome_arquivo(caminho_arquivo.name)
    if data_arquivo:
        return data_arquivo
    # Fallback para evitar nulo quando o nome vier fora do padrao esperado.
    return datetime.fromtimestamp(os.path.getmtime(caminho_arquivo)).date()


@transaction.atomic
def importar_dfc_do_diretorio(
    empresa,
    diretorio: str = "importacoes/financeiro/dfc",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "dfc": 0,
            "titulos": 0,
            "naturezas": 0,
            "operacoes": 0,
            "parceiros": 0,
            "centros_resultado": 0,
        }

    if limpar_antes:
        FluxoDeCaixaDFC.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_fluxos = 0
    objetos: list[FluxoDeCaixaDFC] = []

    cache_titulos: dict[str, Titulo] = {}
    cache_naturezas: dict[str, Natureza] = {}
    cache_operacoes: dict[str, Operacao] = {}
    cache_parceiros: dict[str, Parceiro] = {}
    cache_centros: dict[str, CentroResultado] = {}

    mapeamento_colunas = {
        "data_negociacao": ["dtnegociacao"],
        "data_vencimento": ["dtvencimento"],
        "valor_liquido": ["valorliquido"],
        "numero_nota": ["nronota", "numnota", "numeronota"],
        "titulo_codigo": ["tipodetitulo", "tipotitulo"],
        "titulo_descricao": ["descricaotipodetitulo"],
        "centro_resultado_descricao": ["descricaocentroderesultado", "centroresultado"],
        "descricao_tipo_operacao": ["descricaotipooperacao"],
        "natureza_codigo": ["natureza"],
        "natureza_descricao": ["descricaonatureza"],
        "historico": ["historico"],
        "parceiro_codigo": ["parceiro"],
        "parceiro_nome": ["nomeparceiroparceiro", "nomeparceiro"],
        "operacao_codigo": ["tipooperacao"],
        "operacao_descricao": ["receitadespesa"],
        "tipo_movimento": ["tipodemovimento"],
    }

    for arquivo in arquivos:
        indices = None
        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                if (
                    idx_map["data_negociacao"] is not None
                    and idx_map["data_vencimento"] is not None
                    and idx_map["valor_liquido"] is not None
                ):
                    indices = idx_map
                continue

            if indices is None:
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            data_negociacao = _excel_date(_valor_por_indice("data_negociacao"))
            data_vencimento = _excel_date(_valor_por_indice("data_vencimento"))
            if not data_negociacao or not data_vencimento:
                continue

            titulo_codigo = _normalizar_codigo(_valor_por_indice("titulo_codigo"))
            titulo_descricao = _normalizar_texto(_valor_por_indice("titulo_descricao"))
            natureza_codigo = _normalizar_codigo(_valor_por_indice("natureza_codigo"))
            natureza_descricao = _normalizar_texto(_valor_por_indice("natureza_descricao"))
            operacao_codigo = _normalizar_codigo(_valor_por_indice("operacao_codigo"))
            operacao_descricao = _normalizar_texto(_valor_por_indice("operacao_descricao"))
            parceiro_codigo = _normalizar_codigo(_valor_por_indice("parceiro_codigo"))
            parceiro_nome = _normalizar_texto(_valor_por_indice("parceiro_nome"))
            centro_descricao = _normalizar_texto(_valor_por_indice("centro_resultado_descricao"))

            titulo = None
            if not titulo_codigo and titulo_descricao:
                titulo_codigo = _codigo_a_partir_descricao("DESC_", titulo_descricao, 50)
            if titulo_codigo:
                titulo = cache_titulos.get(titulo_codigo)
                if titulo is None:
                    titulo = Titulo.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        tipo_titulo_codigo=titulo_codigo,
                        descricao=titulo_descricao,
                    )
                    cache_titulos[titulo_codigo] = titulo

            natureza = None
            if not natureza_codigo and natureza_descricao:
                natureza_codigo = _codigo_a_partir_descricao("DESC_", natureza_descricao, 50)
            if natureza_codigo:
                natureza = cache_naturezas.get(natureza_codigo)
                if natureza is None:
                    natureza = Natureza.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        codigo=natureza_codigo,
                        descricao=natureza_descricao,
                    )
                    cache_naturezas[natureza_codigo] = natureza

            operacao = None
            if not operacao_codigo and operacao_descricao:
                operacao_codigo = _codigo_a_partir_descricao("DESC_", operacao_descricao, 50)
            if operacao_codigo:
                operacao = cache_operacoes.get(operacao_codigo)
                if operacao is None:
                    operacao = Operacao.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        tipo_operacao_codigo=operacao_codigo,
                        descricao_receita_despesa=operacao_descricao,
                    )
                    cache_operacoes[operacao_codigo] = operacao

            parceiro = None
            if parceiro_codigo:
                parceiro = cache_parceiros.get(parceiro_codigo)
                if parceiro is None:
                    parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                        empresa=empresa,
                        codigo=parceiro_codigo,
                        nome=parceiro_nome,
                    )
                    cache_parceiros[parceiro_codigo] = parceiro

            centro_resultado = None
            if centro_descricao:
                centro_resultado = cache_centros.get(centro_descricao)
                if centro_resultado is None:
                    centro_resultado = CentroResultado.obter_ou_criar_por_descricao(empresa=empresa, descricao=centro_descricao)
                    cache_centros[centro_descricao] = centro_resultado

            objetos.append(
                FluxoDeCaixaDFC(
                    empresa=empresa,
                    data_negociacao=data_negociacao,
                    data_vencimento=data_vencimento,
                    valor_liquido=_to_decimal(_valor_por_indice("valor_liquido")),
                    numero_nota=_normalizar_codigo(_valor_por_indice("numero_nota")),
                    titulo=titulo,
                    centro_resultado=centro_resultado,
                    descricao_tipo_operacao=_normalizar_texto(_valor_por_indice("descricao_tipo_operacao")),
                    natureza=natureza,
                    historico=_normalizar_texto(_valor_por_indice("historico")),
                    parceiro=parceiro,
                    operacao=operacao,
                    tipo_movimento=_normalizar_texto(_valor_por_indice("tipo_movimento")),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                FluxoDeCaixaDFC.objects.bulk_create(objetos, batch_size=1000)
                total_fluxos += len(objetos)
                objetos = []

    if objetos:
        FluxoDeCaixaDFC.objects.bulk_create(objetos, batch_size=1000)
        total_fluxos += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "dfc": total_fluxos,
        "titulos": len(cache_titulos),
        "naturezas": len(cache_naturezas),
        "operacoes": len(cache_operacoes),
        "parceiros": len(cache_parceiros),
        "centros_resultado": len(cache_centros),
    }


@transaction.atomic
def importar_contas_a_receber_do_diretorio(
    empresa,
    diretorio: str = "importacoes/financeiro/contas_a_receber",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "contas_a_receber": 0,
            "titulos": 0,
            "naturezas": 0,
            "operacoes": 0,
            "parceiros": 0,
            "centros_resultado": 0,
        }

    if limpar_antes:
        ContasAReceber.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_contas = 0
    objetos: list[ContasAReceber] = []

    cache_titulos: dict[str, Titulo] = {}
    cache_naturezas: dict[str, Natureza] = {}
    cache_operacoes: dict[str, Operacao] = {}
    cache_parceiros: dict[str, Parceiro] = {}
    cache_centros: dict[str, CentroResultado] = {}

    mapeamento_colunas = {
        "data_negociacao": ["dtnegociacao"],
        "data_vencimento": ["dtvencimento"],
        "nome_fantasia_empresa": ["nomefantasiaempresa", "nomefantasia"],
        "parceiro_codigo": ["parceiro"],
        "parceiro_nome": ["nomeparceiroparceiro", "nomeparceiro"],
        "numero_nota": ["nronota", "numnota", "numeronota"],
        "valor_desdobramento": ["valordesdobramento", "vlrdodesdobramento", "valordesd", "valor"],
        "valor_liquido": ["valorliquido", "valor"],
        "titulo_codigo": ["tipodetitulo", "tipotitulo"],
        "titulo_descricao": ["descricaotipodetitulo"],
        "natureza_codigo": ["natureza"],
        "natureza_descricao": ["descricaonatureza"],
        "centro_resultado_descricao": ["descricaocentroderesultado", "centroresultado"],
        "operacao_codigo": ["tipooperacao"],
        "operacao_descricao": ["receitadespesa", "descricaotipooperacao"],
        "vendedor": ["vendedor"],
    }

    for arquivo in arquivos:
        indices = None
        data_arquivo = _data_arquivo_nao_nula(arquivo)

        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                if (
                    idx_map["data_negociacao"] is not None
                    and idx_map["data_vencimento"] is not None
                    and (idx_map["valor_desdobramento"] is not None or idx_map["valor_liquido"] is not None)
                ):
                    indices = idx_map
                continue

            if indices is None:
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            data_negociacao = _excel_date(_valor_por_indice("data_negociacao"))
            data_vencimento = _excel_date(_valor_por_indice("data_vencimento"))
            if not data_negociacao or not data_vencimento:
                continue

            titulo_codigo = _normalizar_codigo(_valor_por_indice("titulo_codigo"))
            titulo_descricao = _normalizar_texto(_valor_por_indice("titulo_descricao"))
            natureza_codigo = _normalizar_codigo(_valor_por_indice("natureza_codigo"))
            natureza_descricao = _normalizar_texto(_valor_por_indice("natureza_descricao"))
            operacao_codigo = _normalizar_codigo(_valor_por_indice("operacao_codigo"))
            operacao_descricao = _normalizar_texto(_valor_por_indice("operacao_descricao"))
            parceiro_codigo = _normalizar_codigo(_valor_por_indice("parceiro_codigo"))
            parceiro_nome = _normalizar_texto(_valor_por_indice("parceiro_nome"))
            centro_descricao = _normalizar_texto(_valor_por_indice("centro_resultado_descricao"))

            titulo = None
            if not titulo_codigo and titulo_descricao:
                titulo_codigo = _codigo_a_partir_descricao("DESC_", titulo_descricao, 50)
            if titulo_codigo:
                titulo = cache_titulos.get(titulo_codigo)
                if titulo is None:
                    titulo = Titulo.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        tipo_titulo_codigo=titulo_codigo,
                        descricao=titulo_descricao,
                    )
                    cache_titulos[titulo_codigo] = titulo

            natureza = None
            if not natureza_codigo and natureza_descricao:
                natureza_codigo = _codigo_a_partir_descricao("DESC_", natureza_descricao, 50)
            if natureza_codigo:
                natureza = cache_naturezas.get(natureza_codigo)
                if natureza is None:
                    natureza = Natureza.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        codigo=natureza_codigo,
                        descricao=natureza_descricao,
                    )
                    cache_naturezas[natureza_codigo] = natureza

            operacao = None
            if not operacao_codigo and operacao_descricao:
                operacao_codigo = _codigo_a_partir_descricao("DESC_", operacao_descricao, 50)
            if operacao_codigo:
                operacao = cache_operacoes.get(operacao_codigo)
                if operacao is None:
                    operacao = Operacao.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        tipo_operacao_codigo=operacao_codigo,
                        descricao_receita_despesa=operacao_descricao,
                    )
                    cache_operacoes[operacao_codigo] = operacao

            parceiro = None
            if parceiro_codigo:
                parceiro = cache_parceiros.get(parceiro_codigo)
                if parceiro is None:
                    parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                        empresa=empresa,
                        codigo=parceiro_codigo,
                        nome=parceiro_nome,
                    )
                    cache_parceiros[parceiro_codigo] = parceiro

            centro_resultado = None
            if centro_descricao:
                centro_resultado = cache_centros.get(centro_descricao)
                if centro_resultado is None:
                    centro_resultado = CentroResultado.obter_ou_criar_por_descricao(empresa=empresa, descricao=centro_descricao)
                    cache_centros[centro_descricao] = centro_resultado

            valor_desdobramento = _to_decimal(_valor_por_indice("valor_desdobramento"))
            valor_liquido = _to_decimal(_valor_por_indice("valor_liquido"))
            if indices.get("valor_liquido") is None:
                valor_liquido = valor_desdobramento

            objetos.append(
                ContasAReceber(
                    empresa=empresa,
                    data_negociacao=data_negociacao,
                    data_vencimento=data_vencimento,
                    data_arquivo=data_arquivo,
                    nome_fantasia_empresa=_normalizar_texto(_valor_por_indice("nome_fantasia_empresa")),
                    parceiro=parceiro,
                    numero_nota=_normalizar_codigo(_valor_por_indice("numero_nota")),
                    vendedor=_normalizar_texto(_valor_por_indice("vendedor")),
                    valor_desdobramento=valor_desdobramento,
                    valor_liquido=valor_liquido,
                    titulo=titulo,
                    natureza=natureza,
                    centro_resultado=centro_resultado,
                    operacao=operacao,
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                ContasAReceber.objects.bulk_create(objetos, batch_size=1000)
                total_contas += len(objetos)
                objetos = []

    if objetos:
        ContasAReceber.objects.bulk_create(objetos, batch_size=1000)
        total_contas += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "contas_a_receber": total_contas,
        "titulos": len(cache_titulos),
        "naturezas": len(cache_naturezas),
        "operacoes": len(cache_operacoes),
        "parceiros": len(cache_parceiros),
        "centros_resultado": len(cache_centros),
    }
