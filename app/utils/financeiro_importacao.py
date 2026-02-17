from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import unicodedata

from django.db import transaction

from ..models import FluxoDeCaixaDFC, Natureza, Operacao, Parceiro, Titulo

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

    mapeamento_colunas = {
        "data_negociacao": ["dtnegociacao"],
        "data_vencimento": ["dtvencimento"],
        "valor_liquido": ["valorliquido"],
        "numero_nota": ["nronota", "numnota", "numeronota"],
        "titulo_codigo": ["tipodetitulo", "tipotitulo"],
        "titulo_descricao": ["descricaotipodetitulo"],
        "descricao_centro_resultado": ["descricaocentroderesultado"],
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

            titulo = None
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

            objetos.append(
                FluxoDeCaixaDFC(
                    empresa=empresa,
                    data_negociacao=data_negociacao,
                    data_vencimento=data_vencimento,
                    valor_liquido=_to_decimal(_valor_por_indice("valor_liquido")),
                    numero_nota=_normalizar_codigo(_valor_por_indice("numero_nota")),
                    titulo=titulo,
                    descricao_centro_resultado=_normalizar_texto(_valor_por_indice("descricao_centro_resultado")),
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
    }
