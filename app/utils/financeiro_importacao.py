from __future__ import annotations

import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from django.db import transaction
from django.db.models import Max
from django.db.models.functions import ExtractMonth, ExtractYear

from ..models import (
    Adiantamento,
    CentroResultado,
    ContasAReceber,
    FluxoDeCaixaDFC,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
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


def _descricao_textual_ou_vazio(valor) -> str:
    texto = _normalizar_texto(valor)
    if not texto:
        return ""
    # Centro de resultado deve ser descritivo; ignora valores apenas numericos/simbolos.
    if not any(ch.isalpha() for ch in texto):
        return ""
    return texto


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


def _to_int64(valor) -> int:
    decimal_valor = _to_decimal(valor, decimal_places=6)
    try:
        inteiro = decimal_valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return 0
    try:
        return int(inteiro)
    except (TypeError, ValueError):
        return 0


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


def _rotulo_coluna(coluna) -> str:
    texto = _normalizar_texto(coluna)
    if "_" in texto:
        texto = texto.replace("_", " ")
    return texto


def _colunas_nao_identificadas(indices: dict | None, colunas_esperadas) -> list[str]:
    if not indices:
        return [str(coluna) for coluna in colunas_esperadas]
    return [str(coluna) for coluna in colunas_esperadas if indices.get(coluna) is None]


def _registrar_aviso_colunas(
    avisos: list[str],
    *,
    nome_arquivo: str,
    faltantes: list[str],
    obrigatorias=None,
):
    if not faltantes:
        return

    obrigatorias_set = set(obrigatorias or [])
    obrigatorias_faltantes = [coluna for coluna in faltantes if coluna in obrigatorias_set]
    opcionais_faltantes = [coluna for coluna in faltantes if coluna not in obrigatorias_set]

    partes = []
    if obrigatorias_faltantes:
        obrigatorias_fmt = ", ".join(_rotulo_coluna(coluna) for coluna in obrigatorias_faltantes)
        partes.append(f"obrigatorias: {obrigatorias_fmt}")
    if opcionais_faltantes:
        opcionais_fmt = ", ".join(_rotulo_coluna(coluna) for coluna in opcionais_faltantes)
        partes.append(f"opcionais: {opcionais_fmt}")

    detalhe = "; ".join(partes)
    mensagem = f"Arquivo '{nome_arquivo}': colunas nao identificadas ({detalhe})."
    if mensagem not in avisos:
        avisos.append(mensagem)


MESES_PT_TO_FIELD = {
    "janeiro": "janeiro",
    "fevereiro": "fevereiro",
    "marco": "marco",
    "abril": "abril",
    "maio": "maio",
    "junho": "junho",
    "julho": "julho",
    "agosto": "agosto",
    "setembro": "setembro",
    "outubro": "outubro",
    "novembro": "novembro",
    "dezembro": "dezembro",
}

CENTRO_RESULTADO_PADRAO = "<SEM CENTRO DE RESULTADO>"
MES_NUMERO_TO_FIELD = {indice + 1: campo for indice, campo in enumerate(MESES_PT_TO_FIELD.values())}


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
            "avisos": [],
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
    avisos: list[str] = []

    mapeamento_colunas = {
        "data_negociacao": ["dtnegociacao"],
        "data_vencimento": ["dtvencimento"],
        "valor_liquido": ["valorliquido"],
        "numero_nota": ["nronota", "numnota", "numeronota"],
        "titulo_codigo": ["tipodetitulo", "tipotitulo"],
        "titulo_descricao": ["descricaotipodetitulo"],
        "centro_resultado_descricao": ["descricaocentroderesultado", "centroresultado"],
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
        melhor_idx_map = None
        melhor_score = -1
        obrigatorias = {"data_negociacao", "data_vencimento", "valor_liquido"}
        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                score = sum(1 for idx in idx_map.values() if idx is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if (
                    idx_map["data_negociacao"] is not None
                    and idx_map["data_vencimento"] is not None
                    and idx_map["valor_liquido"] is not None
                ):
                    indices = idx_map
                    faltantes = _colunas_nao_identificadas(indices, mapeamento_colunas.keys())
                    _registrar_aviso_colunas(
                        avisos,
                        nome_arquivo=arquivo.name,
                        faltantes=faltantes,
                        obrigatorias=obrigatorias,
                    )
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
            centro_descricao = _descricao_textual_ou_vazio(_valor_por_indice("centro_resultado_descricao"))

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

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

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
        "avisos": avisos,
    }


@transaction.atomic
def importar_adiantamentos_do_diretorio(
    empresa,
    diretorio: str = "importacoes/financeiro/adiantamentos",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "adiantamentos": 0,
            "avisos": [],
        }

    if limpar_antes:
        Adiantamento.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_adiantamentos = 0
    objetos: list[Adiantamento] = []
    avisos: list[str] = []

    mapeamento_colunas = {
        "moeda": ["moeda"],
        "saldo_banco_em_reais": ["saldobancoemreais"],
        "saldo_real_em_reais": ["saldorealemreais"],
        "conta_descricao": ["conta"],
        "saldo_real": ["saldoreal"],
        "saldo_banco": ["saldobanco"],
        "banco": ["banco"],
        "agencia": ["agencia"],
        "conta_bancaria": ["contabancaria"],
        "empresa_descricao": ["empresa"],
    }
    obrigatorias = set(mapeamento_colunas.keys())

    for arquivo in arquivos:
        if xlrd is None:
            raise RuntimeError("Dependencia 'xlrd' nao encontrada. Instale com: pip install xlrd==2.0.1")

        workbook = xlrd.open_workbook(str(arquivo))
        if workbook.nsheets <= 0:
            continue

        planilha = None
        for nome_planilha in workbook.sheet_names():
            if _normalizar_nome_coluna(nome_planilha) == "newsheet":
                planilha = workbook.sheet_by_name(nome_planilha)
                break
        if planilha is None:
            planilha = workbook.sheet_by_index(0)

        if planilha.nrows <= 2:
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=list(mapeamento_colunas.keys()),
                obrigatorias=obrigatorias,
            )
            continue

        cabecalho = planilha.row_values(2)
        cabecalho_normalizado = [_normalizar_nome_coluna(coluna) for coluna in cabecalho]
        indices = {}
        for chave, aliases in mapeamento_colunas.items():
            indices[chave] = next((i for i, token in enumerate(cabecalho_normalizado) if token in aliases), None)

        faltantes = _colunas_nao_identificadas(indices, mapeamento_colunas.keys())
        _registrar_aviso_colunas(
            avisos,
            nome_arquivo=arquivo.name,
            faltantes=faltantes,
            obrigatorias=obrigatorias,
        )
        if any(indices.get(chave) is None for chave in obrigatorias):
            continue

        def _valor_por_indice(linha_valores, chave):
            idx = indices.get(chave)
            if idx is None or idx >= len(linha_valores):
                return ""
            return linha_valores[idx]

        for row_idx in range(3, planilha.nrows):
            linha = planilha.row_values(row_idx)
            if not any(_normalizar_texto(valor) for valor in linha):
                continue

            conta_descricao = _normalizar_texto(_valor_por_indice(linha, "conta_descricao"))
            # Power Query: filtra apenas linhas com "Conta" preenchida.
            if not conta_descricao:
                continue

            objetos.append(
                Adiantamento(
                    empresa=empresa,
                    moeda=_normalizar_texto(_valor_por_indice(linha, "moeda")),
                    saldo_banco_em_reais=_to_decimal(_valor_por_indice(linha, "saldo_banco_em_reais")),
                    saldo_real_em_reais=_to_decimal(_valor_por_indice(linha, "saldo_real_em_reais")),
                    saldo_real=_to_decimal(_valor_por_indice(linha, "saldo_real")),
                    conta_descricao=conta_descricao,
                    saldo_banco=_to_int64(_valor_por_indice(linha, "saldo_banco")),
                    banco=_normalizar_texto(_valor_por_indice(linha, "banco")),
                    agencia=_normalizar_texto(_valor_por_indice(linha, "agencia")),
                    conta_bancaria=_normalizar_texto(_valor_por_indice(linha, "conta_bancaria")),
                    empresa_descricao=_normalizar_texto(_valor_por_indice(linha, "empresa_descricao")),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Adiantamento.objects.bulk_create(objetos, batch_size=1000)
                total_adiantamentos += len(objetos)
                objetos = []

    if objetos:
        Adiantamento.objects.bulk_create(objetos, batch_size=1000)
        total_adiantamentos += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "adiantamentos": total_adiantamentos,
        "avisos": avisos,
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
            "avisos": [],
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
    avisos: list[str] = []

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
        melhor_idx_map = None
        melhor_score = -1
        obrigatorias = {"data_negociacao", "data_vencimento"}
        data_arquivo = _data_arquivo_nao_nula(arquivo)

        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                score = sum(1 for idx in idx_map.values() if idx is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if (
                    idx_map["data_negociacao"] is not None
                    and idx_map["data_vencimento"] is not None
                    and (idx_map["valor_desdobramento"] is not None or idx_map["valor_liquido"] is not None)
                ):
                    indices = idx_map
                    faltantes = _colunas_nao_identificadas(indices, mapeamento_colunas.keys())
                    _registrar_aviso_colunas(
                        avisos,
                        nome_arquivo=arquivo.name,
                        faltantes=faltantes,
                        obrigatorias=obrigatorias,
                    )
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
            centro_descricao = _descricao_textual_ou_vazio(_valor_por_indice("centro_resultado_descricao"))

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

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            obrigatorias_dinamicas = set(obrigatorias)
            if (
                melhor_idx_map is None
                or (
                    melhor_idx_map.get("valor_desdobramento") is None
                    and melhor_idx_map.get("valor_liquido") is None
                )
            ):
                faltantes.append("valor_desdobramento/valor_liquido")
                obrigatorias_dinamicas.add("valor_desdobramento/valor_liquido")
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias_dinamicas,
            )

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
        "avisos": avisos,
    }


@transaction.atomic
def importar_orcamento_do_diretorio(
    empresa,
    diretorio: str = "importacoes/financeiro/orcamento",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "orcamentos": 0,
            "titulos": 0,
            "naturezas": 0,
            "operacoes": 0,
            "parceiros": 0,
            "centros_resultado": 0,
            "avisos": [],
        }

    if limpar_antes:
        Orcamento.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_orcamentos = 0
    objetos: list[Orcamento] = []

    cache_titulos: dict[str, Titulo] = {}
    cache_naturezas: dict[str, Natureza] = {}
    cache_operacoes: dict[str, Operacao] = {}
    cache_parceiros: dict[str, Parceiro] = {}
    cache_centros: dict[str, CentroResultado] = {}
    avisos: list[str] = []

    mapeamento_colunas = {
        "empresa_codigo": ["empresa"],
        "empresa_nome_fantasia": ["nomefantasiaempresa"],
        "data_vencimento": ["dtvencimento"],
        "data_baixa": ["databaixa", "dtbaixa"],
        "valor_baixa": ["vlrbaixa", "valorbaixa"],
        "valor_liquido": ["valorliquido"],
        "valor_desdobramento": ["valordesdobramento", "vlrdodesdobramento", "valordesd"],
        "titulo_descricao": ["descricaotipodetitulo"],
        "natureza_codigo": ["natureza"],
        "natureza_descricao": ["descricaonatureza"],
        "centro_resultado_descricao": ["descricaocentroderesultado", "centroresultado"],
        "parceiro_codigo": ["parceiro"],
        "parceiro_nome": ["nomeparceiroparceiro", "nomeparceiro"],
        "operacao_codigo": ["tipooperacao"],
        "operacao_descricao": ["receitadespesa", "descricaotipooperacao"],
        "receita_despesa": ["receitadespesa"],
    }

    for arquivo in arquivos:
        indices = None
        melhor_idx_map = None
        melhor_score = -1
        obrigatorias = {"data_vencimento", "data_baixa", "valor_baixa"}
        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                score = sum(1 for idx in idx_map.values() if idx is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if (
                    idx_map["data_vencimento"] is not None
                    and idx_map["data_baixa"] is not None
                    and idx_map["valor_baixa"] is not None
                ):
                    indices = idx_map
                    faltantes = _colunas_nao_identificadas(indices, mapeamento_colunas.keys())
                    _registrar_aviso_colunas(
                        avisos,
                        nome_arquivo=arquivo.name,
                        faltantes=faltantes,
                        obrigatorias=obrigatorias,
                    )
                continue

            if indices is None:
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            data_vencimento = _excel_date(_valor_por_indice("data_vencimento"))
            data_baixa = _excel_date(_valor_por_indice("data_baixa"))
            if not data_vencimento or not data_baixa:
                continue

            titulo_descricao = _normalizar_texto(_valor_por_indice("titulo_descricao"))
            natureza_codigo = _normalizar_codigo(_valor_por_indice("natureza_codigo"))
            natureza_descricao = _normalizar_texto(_valor_por_indice("natureza_descricao"))
            operacao_codigo = _normalizar_codigo(_valor_por_indice("operacao_codigo"))
            operacao_descricao = _normalizar_texto(_valor_por_indice("operacao_descricao"))
            receita_despesa = _normalizar_texto(_valor_por_indice("receita_despesa")).lower()
            parceiro_codigo = _normalizar_codigo(_valor_por_indice("parceiro_codigo"))
            parceiro_nome = _normalizar_texto(_valor_por_indice("parceiro_nome"))
            centro_descricao = _descricao_textual_ou_vazio(_valor_por_indice("centro_resultado_descricao"))
            if not centro_descricao:
                centro_descricao = CENTRO_RESULTADO_PADRAO
            empresa_codigo = _normalizar_codigo(_valor_por_indice("empresa_codigo"))
            empresa_nome_fantasia = _normalizar_texto(_valor_por_indice("empresa_nome_fantasia"))

            if receita_despesa and receita_despesa != "despesa":
                continue

            titulo = None
            titulo_codigo = _codigo_a_partir_descricao("DESC_", titulo_descricao, 50) if titulo_descricao else ""
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

            centro_resultado = cache_centros.get(centro_descricao)
            if centro_resultado is None:
                centro_resultado = CentroResultado.obter_ou_criar_por_descricao(
                    empresa=empresa,
                    descricao=centro_descricao,
                )
                cache_centros[centro_descricao] = centro_resultado

            valor_desdobramento = abs(_to_decimal(_valor_por_indice("valor_desdobramento")))
            valor_liquido = abs(_to_decimal(_valor_por_indice("valor_liquido")))
            if indices.get("valor_liquido") is None:
                valor_liquido = valor_desdobramento
            valor_baixa = abs(_to_decimal(_valor_por_indice("valor_baixa")))

            if empresa_codigo and empresa_nome_fantasia:
                nome_empresa = f"{empresa_codigo} - {empresa_nome_fantasia}"
            elif empresa_nome_fantasia:
                nome_empresa = empresa_nome_fantasia
            elif empresa_codigo:
                nome_empresa = empresa_codigo
            else:
                nome_empresa = empresa.nome

            objetos.append(
                Orcamento(
                    empresa=empresa,
                    nome_empresa=nome_empresa,
                    data_vencimento=data_vencimento,
                    data_baixa=data_baixa,
                    valor_baixa=valor_baixa,
                    valor_liquido=valor_liquido,
                    valor_desdobramento=valor_desdobramento,
                    natureza=natureza,
                    titulo=titulo,
                    centro_resultado=centro_resultado,
                    operacao=operacao,
                    parceiro=parceiro,
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Orcamento.objects.bulk_create(objetos, batch_size=1000)
                total_orcamentos += len(objetos)
                objetos = []

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

    if objetos:
        Orcamento.objects.bulk_create(objetos, batch_size=1000)
        total_orcamentos += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "orcamentos": total_orcamentos,
        "titulos": len(cache_titulos),
        "naturezas": len(cache_naturezas),
        "operacoes": len(cache_operacoes),
        "parceiros": len(cache_parceiros),
        "centros_resultado": len(cache_centros),
        "avisos": avisos,
    }


@transaction.atomic
def importar_orcamento_planejado_do_diretorio(
    empresa,
    diretorio: str = "importacoes/financeiro/orcamentos",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "orcamentos_planejados": 0,
            "naturezas": 0,
            "centros_resultado": 0,
            "avisos": [],
        }

    total_linhas = 0
    total_orcamentos = 0
    objetos: list[OrcamentoPlanejado] = []
    cache_naturezas: dict[str, Natureza] = {}
    cache_centros: dict[str, CentroResultado] = {}
    layout_mensal_detectado = False
    base_limpa = False
    fallback_gerado = False
    avisos: list[str] = []

    mapeamento_colunas = {
        "centro_resultado_descricao": ["descricaocentroderesultado", "centroresultado"],
        "natureza_descricao": ["descricaonatureza", "natureza"],
        "nome_empresa": ["nomeempresa"],
        "ano": ["ano"],
        "janeiro": ["janeiro"],
        "fevereiro": ["fevereiro"],
        "marco": ["marco", "marcoo"],
        "abril": ["abril"],
        "maio": ["maio"],
        "junho": ["junho"],
        "julho": ["julho"],
        "agosto": ["agosto"],
        "setembro": ["setembro"],
        "outubro": ["outubro"],
        "novembro": ["novembro"],
        "dezembro": ["dezembro"],
    }

    for arquivo in arquivos:
        indices = None
        melhor_idx_map = None
        melhor_score = -1
        obrigatorias = {"centro_resultado_descricao", "natureza_descricao", "ano"}
        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                score = sum(1 for idx in idx_map.values() if idx is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if (
                    idx_map["centro_resultado_descricao"] is not None
                    and idx_map["natureza_descricao"] is not None
                    and idx_map["ano"] is not None
                ):
                    indices = idx_map
                    layout_mensal_detectado = True
                    faltantes = _colunas_nao_identificadas(indices, mapeamento_colunas.keys())
                    _registrar_aviso_colunas(
                        avisos,
                        nome_arquivo=arquivo.name,
                        faltantes=faltantes,
                        obrigatorias=obrigatorias,
                    )
                    if limpar_antes and not base_limpa:
                        OrcamentoPlanejado.objects.filter(empresa=empresa).delete()
                        base_limpa = True
                continue

            if indices is None:
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            centro_descricao = _descricao_textual_ou_vazio(_valor_por_indice("centro_resultado_descricao"))
            if not centro_descricao or centro_descricao.lower() == "total":
                continue

            natureza_descricao = _normalizar_texto(_valor_por_indice("natureza_descricao"))
            nome_empresa = _normalizar_texto(_valor_por_indice("nome_empresa")) or empresa.nome
            ano_texto = _normalizar_texto(_valor_por_indice("ano"))
            try:
                ano = int(float(ano_texto))
            except (TypeError, ValueError):
                continue

            centro_resultado = cache_centros.get(centro_descricao)
            if centro_resultado is None:
                centro_resultado = CentroResultado.obter_ou_criar_por_descricao(empresa=empresa, descricao=centro_descricao)
                cache_centros[centro_descricao] = centro_resultado

            natureza = None
            if natureza_descricao:
                natureza_codigo = _codigo_a_partir_descricao("DESC_", natureza_descricao, 50)
                natureza = cache_naturezas.get(natureza_codigo)
                if natureza is None:
                    natureza = Natureza.obter_ou_criar_por_codigo_descricao(
                        empresa=empresa,
                        codigo=natureza_codigo,
                        descricao=natureza_descricao,
                    )
                    cache_naturezas[natureza_codigo] = natureza

            valores_meses = {
                campo: abs(_to_decimal(_valor_por_indice(chave)))
                for chave, campo in MESES_PT_TO_FIELD.items()
            }

            objetos.append(
                OrcamentoPlanejado(
                    empresa=empresa,
                    nome_empresa=nome_empresa,
                    ano=ano,
                    natureza=natureza,
                    centro_resultado=centro_resultado,
                    **valores_meses,
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                OrcamentoPlanejado.objects.bulk_create(objetos, batch_size=1000)
                total_orcamentos += len(objetos)
                objetos = []

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

    if objetos:
        OrcamentoPlanejado.objects.bulk_create(objetos, batch_size=1000)
        total_orcamentos += len(objetos)

    if not layout_mensal_detectado:
        if limpar_antes:
            OrcamentoPlanejado.objects.filter(empresa=empresa).delete()

        # Fallback para manter a tabela de Orcamentos preenchida quando so houver
        # arquivos de realizados: usa o maior valor_desdobramento por chave/mês.
        linhas_fallback = (
            Orcamento.objects.filter(empresa=empresa, data_baixa__isnull=False)
            .annotate(ano=ExtractYear("data_baixa"), mes=ExtractMonth("data_baixa"))
            .values(
                "nome_empresa",
                "ano",
                "mes",
                "centro_resultado__descricao",
                "natureza__descricao",
            )
            .annotate(valor_orcamento=Max("valor_desdobramento"))
            .order_by()
        )

        agregados = {}
        for linha in linhas_fallback:
            ano = int(linha.get("ano") or 0)
            mes = int(linha.get("mes") or 0)
            if not ano or not mes:
                continue

            nome_empresa = _normalizar_texto(linha.get("nome_empresa")) or empresa.nome
            centro_descricao = _descricao_textual_ou_vazio(linha.get("centro_resultado__descricao"))
            if not centro_descricao:
                centro_descricao = CENTRO_RESULTADO_PADRAO
            natureza_descricao = _normalizar_texto(linha.get("natureza__descricao")) or "<SEM NATUREZA>"
            campo_mes = MES_NUMERO_TO_FIELD.get(mes)
            if not campo_mes:
                continue

            chave = (nome_empresa, ano, centro_descricao, natureza_descricao)
            if chave not in agregados:
                agregados[chave] = {campo: Decimal("0") for campo in MESES_PT_TO_FIELD.values()}
            agregados[chave][campo_mes] = max(
                agregados[chave][campo_mes],
                _to_decimal(linha.get("valor_orcamento") or 0),
            )

        fallback_objetos = []
        for (nome_empresa, ano, centro_descricao, natureza_descricao), valores_meses in agregados.items():
            centro_resultado = cache_centros.get(centro_descricao)
            if centro_resultado is None:
                centro_resultado = CentroResultado.obter_ou_criar_por_descricao(
                    empresa=empresa,
                    descricao=centro_descricao,
                )
                cache_centros[centro_descricao] = centro_resultado

            natureza_codigo = _codigo_a_partir_descricao("DESC_", natureza_descricao, 50)
            natureza = cache_naturezas.get(natureza_codigo)
            if natureza is None:
                natureza = Natureza.obter_ou_criar_por_codigo_descricao(
                    empresa=empresa,
                    codigo=natureza_codigo,
                    descricao=natureza_descricao,
                )
                cache_naturezas[natureza_codigo] = natureza

            fallback_objetos.append(
                OrcamentoPlanejado(
                    empresa=empresa,
                    nome_empresa=nome_empresa,
                    ano=ano,
                    natureza=natureza,
                    centro_resultado=centro_resultado,
                    **valores_meses,
                )
            )

        if fallback_objetos:
            OrcamentoPlanejado.objects.bulk_create(fallback_objetos, batch_size=1000)
            total_orcamentos = len(fallback_objetos)
            total_linhas = len(linhas_fallback)
            fallback_gerado = True

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "orcamentos_planejados": total_orcamentos,
        "naturezas": len(cache_naturezas),
        "centros_resultado": len(cache_centros),
        "layout_mensal_detectado": layout_mensal_detectado,
        "fallback_gerado": fallback_gerado,
        "avisos": avisos,
    }
