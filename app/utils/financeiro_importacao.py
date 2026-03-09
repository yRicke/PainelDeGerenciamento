from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from django.db import transaction
from django.db.models import Max
from django.db.models.functions import ExtractMonth, ExtractYear

from ..models import (
    Adiantamento,
    Carteira,
    CentroResultado,
    Cidade,
    ContasAReceber,
    Faturamento,
    Frete,
    FluxoDeCaixaDFC,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
    Parceiro,
    Produto,
    Titulo,
)
from .comercial_importacao import _iterar_linhas_xlsx

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


def _eh_zero_explicito(valor) -> bool:
    texto = _normalizar_texto(valor)
    if not texto:
        return False
    texto = texto.replace(" ", "")
    return bool(re.fullmatch(r"0+([.,]0+)?", texto))


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
        # dd-mm-aaaa ou dd.mm.aaaa
        ("dmy4", r"(?<!\d)(\d{1,2})[._\-/\s](\d{1,2})[._\-/\s](\d{4})(?!\d)"),
        # aaaa-mm-dd
        ("ymd4", r"(?<!\d)(\d{4})[._\-/\s](\d{1,2})[._\-/\s](\d{1,2})(?!\d)"),
        # dd-mm-aa (ex.: 25-02-26)
        ("dmy2", r"(?<!\d)(\d{1,2})[._\-/\s](\d{1,2})[._\-/\s](\d{2})(?!\d)"),
        # aa-mm-dd
        ("ymd2", r"(?<!\d)(\d{2})[._\-/\s](\d{1,2})[._\-/\s](\d{1,2})(?!\d)"),
        # ddmmaaaa
        ("dmy4_compacto", r"(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)"),
        # aaaammdd
        ("ymd4_compacto", r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)"),
        # ddmmaa
        ("dmy2_compacto", r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)"),
        # aammdd
        ("ymd2_compacto", r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)"),
    ]

    def _normalizar_ano(ano_bruto: str) -> int:
        ano_int = int(ano_bruto)
        if len(str(ano_bruto)) == 4:
            return ano_int
        # Janela simples para anos com 2 digitos:
        # 00-79 => 2000-2079 | 80-99 => 1980-1999
        return 2000 + ano_int if ano_int <= 79 else 1900 + ano_int

    for tipo, padrao in padroes:
        match = re.search(padrao, base)
        if not match:
            continue
        grupos = match.groups()
        try:
            if tipo.startswith("ymd"):
                ano = _normalizar_ano(grupos[0])
                mes = int(grupos[1])
                dia = int(grupos[2])
                return date(ano, mes, dia)
            if tipo.startswith("dmy"):
                dia = int(grupos[0])
                mes = int(grupos[1])
                ano = _normalizar_ano(grupos[2])
                return date(ano, mes, dia)
        except ValueError:
            continue
    return None


def _data_arquivo_do_nome_arquivo(caminho_arquivo: Path):
    data_arquivo = _extrair_data_do_nome_arquivo(caminho_arquivo.name)
    if data_arquivo:
        return data_arquivo
    # Fallback intencional: manter vazio quando nao for possivel extrair do nome.
    return None


FATURAMENTO_SUBPASTA_DIARIO = "1 - Faturamento diario"
FATURAMENTO_SUBPASTA_PRODUTOS = "2 - Venda por Produto (NF)"
FATURAMENTO_CHAVE_PASTA_DIARIO = _normalizar_nome_coluna("1 - Faturamento diario")
FATURAMENTO_CHAVE_PASTA_PRODUTOS = _normalizar_nome_coluna("2 - Venda por Produto (NF)")
FATURAMENTO_OPERACOES_PERMITIDAS = {
    _normalizar_nome_coluna(valor)
    for valor in [
        "SAFIA VENDA INTERNA DF AÇUCAREIRA",
        "SAFIA VENDA NFC - AÇUCAREIRA",
        "SAFIA VENDA NFE",
        "SAFIA VENDA NFE - ATACADO",
        "SAFIA VENDA NFE - AÇUCAREIRA",
        "SAFIA VENDA NFE -TRIANGULAR SEM TRASISTA",
    ]
}


def _arquivo_xlsx_visivel(caminho: Path) -> bool:
    nome = str(caminho.name or "").strip()
    if not nome:
        return False
    if nome.startswith(".") or nome.startswith("~$"):
        return False
    if nome.lower() in {"thumbs.db", "desktop.ini"}:
        return False
    return caminho.suffix.lower() == ".xlsx"


def _classificar_arquivo_faturamento(base: Path, caminho_arquivo: Path) -> str:
    try:
        rel_parts = list(caminho_arquivo.relative_to(base).parts[:-1])
    except ValueError:
        rel_parts = list(caminho_arquivo.parts[:-1])
    tokens = {_normalizar_nome_coluna(parte) for parte in rel_parts}
    if FATURAMENTO_CHAVE_PASTA_DIARIO in tokens:
        return "diario"
    if FATURAMENTO_CHAVE_PASTA_PRODUTOS in tokens:
        return "produtos"

    # Fallback para navegadores que enviam apenas o nome do arquivo no upload.
    if re.match(r"^\d{2}\.\d{2}\.\d{4}\.xlsx$", caminho_arquivo.name, flags=re.IGNORECASE):
        return "diario"
    return "produtos"


def _valor_por_indice(linha, indices, chave):
    idx = (indices or {}).get(chave)
    if idx is None or idx < 0 or idx >= len(linha):
        return ""
    return linha[idx]


def _extrair_decimal_de_texto(valor, decimal_places: int = 2) -> Decimal:
    texto = _normalizar_texto(valor)
    if not texto:
        return Decimal("0")
    match = re.search(r"-?\d[\d.,]*", texto)
    if not match:
        return Decimal("0")
    return _to_decimal(match.group(0), decimal_places=decimal_places)


def _gerente_valido_ou_vazio(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return ""
    if texto.upper() in {"<SEM VENDEDOR>", "SEM VENDEDOR", "<SEM GERENTE>", "SEM GERENTE"}:
        return ""
    return texto


def _split_codigo_nome_texto(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return "", ""
    if " - " in texto:
        codigo, nome = texto.split(" - ", 1)
        return _normalizar_codigo(codigo), _normalizar_texto(nome)
    return "", texto


def _split_codigo_descricao_produto(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return "", ""

    if " - " in texto:
        esquerda, descricao = texto.split(" - ", 1)
        esquerda = _normalizar_texto(esquerda)
        descricao = _normalizar_texto(descricao)
        numero_match = re.search(r"(\d+)", esquerda)
        if numero_match:
            return numero_match.group(1), descricao
        return _normalizar_codigo(esquerda), descricao

    return "", texto


def _codigo_cidade_faturamento_unico() -> str:
    for idx in range(1, 10000):
        codigo = f"{idx:04d}"
        if not Cidade.objects.filter(codigo=codigo).exists():
            return codigo
    return datetime.now().strftime("%H%M")


def _cidade_por_nome_get_create(empresa, nome_cidade, cache_cidades):
    nome = _normalizar_texto(nome_cidade)
    if not nome:
        return None

    chave = _normalizar_nome_coluna(nome)
    if chave in cache_cidades:
        return cache_cidades[chave]

    cidade = Cidade.objects.filter(empresa=empresa, nome__iexact=nome).first()
    if not cidade:
        cidade = Cidade.criar_cidade(
            nome=nome,
            empresa=empresa,
            codigo=_codigo_cidade_faturamento_unico(),
        )
    cache_cidades[chave] = cidade
    return cidade


def _parceiro_get_create_com_cidade(empresa, parceiro_codigo, parceiro_nome, cidade, cache_parceiros):
    codigo = _normalizar_codigo(parceiro_codigo)
    nome = _normalizar_texto(parceiro_nome)
    chave = _normalizar_nome_coluna(f"{codigo}|{nome}")
    if chave in cache_parceiros:
        parceiro = cache_parceiros[chave]
    else:
        if codigo:
            parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                empresa=empresa,
                codigo=codigo,
                nome=nome,
            )
        else:
            parceiro = Parceiro.objects.filter(empresa=empresa, nome__iexact=nome).first()
            if parceiro is None and nome:
                codigo = f"DESC_{_codigo_a_partir_descricao('', nome, 46) or '0001'}"[:50]
                parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                    empresa=empresa,
                    codigo=codigo,
                    nome=nome,
                )
        cache_parceiros[chave] = parceiro

    if parceiro and cidade and parceiro.cidade_id != cidade.id:
        parceiro.cidade = cidade
        parceiro.save(update_fields=["cidade"])
    return parceiro


def _operacao_get_create_por_descricao(empresa, descricao, cache_operacoes):
    texto = _normalizar_texto(descricao)
    if not texto:
        return None
    chave = _normalizar_nome_coluna(texto)
    if chave in cache_operacoes:
        return cache_operacoes[chave]
    codigo = _codigo_a_partir_descricao("DESC_", texto, 50)
    operacao = Operacao.obter_ou_criar_por_codigo_descricao(
        empresa=empresa,
        tipo_operacao_codigo=codigo or texto[:50],
        descricao_receita_despesa=texto,
    )
    cache_operacoes[chave] = operacao
    return operacao


def _natureza_get_create_por_descricao(empresa, descricao, cache_naturezas):
    texto = _normalizar_texto(descricao)
    if not texto:
        return None
    chave = _normalizar_nome_coluna(texto)
    if chave in cache_naturezas:
        return cache_naturezas[chave]
    codigo = _codigo_a_partir_descricao("DESC_", texto, 50)
    natureza = Natureza.obter_ou_criar_por_codigo_descricao(
        empresa=empresa,
        codigo=codigo or texto[:50],
        descricao=texto,
    )
    cache_naturezas[chave] = natureza
    return natureza


def _centro_resultado_get_create(empresa, descricao, cache_centros):
    texto = _descricao_textual_ou_vazio(descricao)
    if not texto:
        return None
    chave = _normalizar_nome_coluna(texto)
    if chave in cache_centros:
        return cache_centros[chave]
    centro = CentroResultado.obter_ou_criar_por_descricao(empresa=empresa, descricao=texto)
    cache_centros[chave] = centro
    return centro


def _produto_get_create_por_texto(empresa, produto_texto, cache_produtos):
    codigo, descricao = _split_codigo_descricao_produto(produto_texto)
    if not codigo and not descricao:
        return None
    chave = _normalizar_nome_coluna(f"{codigo}|{descricao}")
    if chave in cache_produtos:
        return cache_produtos[chave]
    if not codigo and descricao:
        codigo = _codigo_a_partir_descricao("DESC_", descricao, 50)
    if not codigo:
        return None
    produto = Produto.obter_ou_criar_por_codigo_descricao(
        empresa=empresa,
        codigo_produto=codigo,
        descricao_produto=descricao,
    )
    cache_produtos[chave] = produto
    return produto


def _mapa_cadastro_carteira_faturamento(empresa):
    mapa = {}
    for item in (
        Carteira.objects.filter(empresa=empresa, parceiro__isnull=False)
        .order_by("-data_cadastro", "-id")
        .values("parceiro__codigo", "parceiro__nome", "gerente", "descricao_perfil")
    ):
        codigo = _normalizar_texto(item.get("parceiro__codigo"))
        nome = _normalizar_texto(item.get("parceiro__nome"))
        if not codigo and not nome:
            continue
        chave = _normalizar_nome_coluna(f"{codigo} - {nome}")
        if chave in mapa:
            continue
        mapa[chave] = {
            "gerente": _gerente_valido_ou_vazio(item.get("gerente")),
            "descricao_perfil": _normalizar_texto(item.get("descricao_perfil")),
        }
    return mapa


def _mapa_frete_tonelada_por_cidade(empresa):
    mapa = {}
    for frete in Frete.objects.filter(empresa=empresa).select_related("cidade"):
        nome_cidade = _normalizar_texto(getattr(getattr(frete, "cidade", None), "nome", ""))
        if not nome_cidade:
            continue
        chave = _normalizar_nome_coluna(nome_cidade)
        if not chave or chave in mapa:
            continue
        valor = frete.valor_frete_tonelada or Decimal("0")
        if valor > 0:
            mapa[chave] = valor
    return mapa


def _percentual_faturamento(valor: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0")
    try:
        return ((valor * Decimal("100")) / total).quantize(Decimal("0.000001"))
    except (InvalidOperation, ZeroDivisionError):
        return Decimal("0")


def _calcular_valor_frete_faturamento(registro, frete_por_cidade):
    tipo_venda = _normalizar_nome_coluna(registro.get("tipo_venda"))
    if "entrega" not in tipo_venda:
        return None

    qtd_saida = registro.get("quantidade_saida") or Decimal("0")
    if qtd_saida <= 0:
        return None

    valor_tonelada = registro.get("valor_tonelada_frete") or Decimal("0")
    if valor_tonelada <= 0:
        cidade_nome = registro.get("cidade_parceiro_nome")
        if not cidade_nome:
            parceiro = registro.get("parceiro")
            cidade_nome = getattr(getattr(parceiro, "cidade", None), "nome", "")
        chave_cidade = _normalizar_nome_coluna(cidade_nome)
        valor_tonelada = frete_por_cidade.get(chave_cidade, Decimal("0"))
    if valor_tonelada <= 0:
        return None

    try:
        return ((qtd_saida / Decimal("1000")) * valor_tonelada).quantize(Decimal("0.01"))
    except (InvalidOperation, ZeroDivisionError):
        return None


def _importar_nf_produtos_faturamento(arquivos):
    produtos_por_nota = defaultdict(list)
    total_linhas = 0
    avisos = []

    mapeamento_colunas = {
        "produto": ["produto"],
        "numero_nota": ["notafiscal", "nronota", "numeronota"],
        "quantidade_saida": ["qtdsaida", "qntsaida", "quantidadesaida", "qtdsaida"],
    }
    obrigatorias = {"produto", "numero_nota", "quantidade_saida"}

    for arquivo in arquivos:
        indices = None
        melhor_idx_map = None
        melhor_score = -1

        for linha in _iterar_linhas_xlsx(arquivo):
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
                if all(idx_map.get(chave) is not None for chave in obrigatorias):
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

            numero_nota_bruto = _valor_por_indice(linha, indices, "numero_nota")
            numero_nota = _to_int64(numero_nota_bruto)
            if numero_nota < 0:
                continue
            if numero_nota == 0 and not _eh_zero_explicito(numero_nota_bruto):
                continue

            quantidade_saida = _to_decimal(_valor_por_indice(linha, indices, "quantidade_saida"))
            produto = _normalizar_texto(_valor_por_indice(linha, indices, "produto"))

            if quantidade_saida <= 0 and not produto:
                continue

            produtos_por_nota[numero_nota].append(
                {
                    "produto": produto,
                    "quantidade_saida": quantidade_saida,
                }
            )
            total_linhas += 1

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

    return {
        "linhas": total_linhas,
        "produtos_por_nota": produtos_por_nota,
        "avisos": avisos,
    }


def _importar_base_faturamento_diario(arquivos):
    registros = []
    total_linhas = 0
    avisos = []

    mapeamento_colunas = {
        "nome_parceiro_base": ["nomeparceiroparceiro", "nomeparceiro"],
        "quantidade_volumes": ["qtdvolumes"],
        "numero_nota": ["nronota", "numeronota", "notafiscal"],
        "valor_nota": ["vlrnota"],
        "peso_bruto": ["pesobruto"],
        "parceiro_codigo": ["parceiro"],
        "status_nfe": ["statusnfe"],
        "descricao_tipo_operacao": ["descricaotipodeoperacao"],
        "apelido_vendedor": ["apelidovendedor"],
        "nome_fantasia_empresa": ["nomefantasiaempresa"],
        "empresa_codigo": ["empresa"],
        "descricao_natureza": ["descricaonatureza"],
        "descricao_centro_resultado": ["descricaocentroderesultado"],
        "tipo_movimento": ["tipodemovimento"],
        "data_faturamento": ["dtdofaturamento", "datafaturamento", "datafatur"],
        "tipo_venda": ["tipodavenda"],
        "prazo_medio": ["prazomediosafia", "prazomedio"],
        "nome_cidade_parceiro_safia": ["nomecidadeparceirosafia"],
        "valor_tonelada_frete": ["valortoneladafretesafia"],
    }
    obrigatorias = {
        "nome_parceiro_base",
        "numero_nota",
        "valor_nota",
        "data_faturamento",
        "descricao_tipo_operacao",
    }

    for arquivo in arquivos:
        indices = None
        melhor_idx_map = None
        melhor_score = -1

        for idx, linha in enumerate(_iterar_linhas_xlsx(arquivo)):
            if idx < 2:
                continue
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if indices is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                score = sum(1 for idx_coluna in idx_map.values() if idx_coluna is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if all(idx_map.get(chave) is not None for chave in obrigatorias):
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

            data_faturamento = _excel_date(_valor_por_indice(linha, indices, "data_faturamento"))
            nome_parceiro_base = _normalizar_texto(_valor_por_indice(linha, indices, "nome_parceiro_base"))
            if not data_faturamento or not nome_parceiro_base:
                continue

            numero_nota_bruto = _valor_por_indice(linha, indices, "numero_nota")
            numero_nota = _to_int64(numero_nota_bruto)
            if numero_nota < 0:
                continue
            if numero_nota == 0 and not _eh_zero_explicito(numero_nota_bruto):
                continue

            codigo_extraido, nome_extraido = _split_codigo_nome_texto(nome_parceiro_base)
            parceiro_codigo = _normalizar_codigo(_valor_por_indice(linha, indices, "parceiro_codigo")) or codigo_extraido
            parceiro_nome = nome_extraido or nome_parceiro_base
            nome_parceiro_legado = (
                _normalizar_texto(f"{parceiro_codigo} - {parceiro_nome}")
                if parceiro_codigo
                else parceiro_nome
            )
            if nome_parceiro_legado == "3620 - SAFIA DISTRIBUIDORA DE ALIMENTOS FILIAL":
                continue

            empresa_codigo = _normalizar_codigo(_valor_por_indice(linha, indices, "empresa_codigo"))
            nome_fantasia_empresa = _normalizar_texto(_valor_por_indice(linha, indices, "nome_fantasia_empresa"))

            nome_empresa = _normalizar_texto(f"{empresa_codigo} - {nome_fantasia_empresa}") if empresa_codigo else nome_fantasia_empresa

            valor_nota = _to_decimal(_valor_por_indice(linha, indices, "valor_nota"))
            prazo_medio = _to_decimal(_valor_por_indice(linha, indices, "prazo_medio"))
            media = prazo_medio * valor_nota

            registros.append(
                {
                    "nome_origem": str(arquivo.stem or "")[:10],
                    "data_faturamento": data_faturamento,
                    "nome_empresa": nome_empresa,
                    "parceiro_codigo": parceiro_codigo,
                    "parceiro_nome": parceiro_nome,
                    "numero_nota": numero_nota,
                    "valor_nota": valor_nota,
                    "peso_bruto": _to_decimal(_valor_por_indice(linha, indices, "peso_bruto")),
                    "quantidade_volumes": _to_decimal(_valor_por_indice(linha, indices, "quantidade_volumes")),
                    "status_nfe": _normalizar_texto(_valor_por_indice(linha, indices, "status_nfe")),
                    "apelido_vendedor": _normalizar_texto(_valor_por_indice(linha, indices, "apelido_vendedor")),
                    "operacao_descricao": _normalizar_texto(_valor_por_indice(linha, indices, "descricao_tipo_operacao")),
                    "natureza_descricao": _normalizar_texto(_valor_por_indice(linha, indices, "descricao_natureza")),
                    "centro_resultado_descricao": _normalizar_texto(_valor_por_indice(linha, indices, "descricao_centro_resultado")),
                    "tipo_movimento": _normalizar_texto(_valor_por_indice(linha, indices, "tipo_movimento")),
                    "tipo_venda": _normalizar_texto(_valor_por_indice(linha, indices, "tipo_venda")),
                    "prazo_medio": prazo_medio,
                    "media": media,
                    "cidade_parceiro_nome": _normalizar_texto(_valor_por_indice(linha, indices, "nome_cidade_parceiro_safia")),
                    "valor_tonelada_frete": _extrair_decimal_de_texto(_valor_por_indice(linha, indices, "valor_tonelada_frete")),
                }
            )
            total_linhas += 1

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

    return {
        "linhas": total_linhas,
        "registros": registros,
        "avisos": avisos,
    }


@transaction.atomic
def importar_faturamento_do_diretorio(
    empresa,
    diretorio: str = "importacoes/administrativo/faturamento",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    pasta_subscritos = base / "subscritos"
    arquivos = sorted(
        [
            arquivo
            for arquivo in base.rglob("*")
            if arquivo.is_file()
            and pasta_subscritos not in arquivo.parents
            and _arquivo_xlsx_visivel(arquivo)
        ]
    )
    if not arquivos:
        return {
            "arquivos": 0,
            "arquivos_faturamento_diario": 0,
            "arquivos_nf_produtos": 0,
            "linhas_faturamento_diario": 0,
            "linhas_nf_produtos": 0,
            "linhas": 0,
            "faturamento": 0,
            "avisos": [],
        }

    arquivos_diario = []
    arquivos_produtos = []
    avisos = []

    for arquivo in arquivos:
        tipo_arquivo = _classificar_arquivo_faturamento(base, arquivo)
        if tipo_arquivo == "diario":
            arquivos_diario.append(arquivo)
            continue
        if tipo_arquivo == "produtos":
            arquivos_produtos.append(arquivo)
            continue
        avisos.append(f"Arquivo ignorado '{arquivo.name}': subpasta nao reconhecida.")

    if not arquivos_diario:
        avisos.append("Nenhum arquivo .xlsx localizado na subpasta '1 - Faturamento diario'.")
    if not arquivos_produtos:
        avisos.append("Nenhum arquivo .xlsx localizado na subpasta '2 - Venda por Produto (NF)'.")

    produtos_result = _importar_nf_produtos_faturamento(arquivos_produtos)
    diario_result = _importar_base_faturamento_diario(arquivos_diario)
    avisos.extend(produtos_result.get("avisos", []))
    avisos.extend(diario_result.get("avisos", []))

    if limpar_antes:
        Faturamento.objects.filter(empresa=empresa).delete()

    registros_base = diario_result.get("registros", [])
    produtos_por_nota = produtos_result.get("produtos_por_nota", {})

    cache_cidades: dict[str, Cidade] = {}
    cache_parceiros: dict[str, Parceiro] = {}
    cache_operacoes: dict[str, Operacao] = {}
    cache_naturezas: dict[str, Natureza] = {}
    cache_centros: dict[str, CentroResultado] = {}
    cache_produtos: dict[str, Produto] = {}

    registros_expandido = []
    indice_global = 0
    for registro in registros_base:
        cidade = _cidade_por_nome_get_create(
            empresa,
            registro.get("cidade_parceiro_nome"),
            cache_cidades,
        )
        parceiro = _parceiro_get_create_com_cidade(
            empresa,
            registro.get("parceiro_codigo"),
            registro.get("parceiro_nome"),
            cidade,
            cache_parceiros,
        )
        operacao = _operacao_get_create_por_descricao(
            empresa,
            registro.get("operacao_descricao"),
            cache_operacoes,
        )
        natureza = _natureza_get_create_por_descricao(
            empresa,
            registro.get("natureza_descricao"),
            cache_naturezas,
        )
        centro_resultado = _centro_resultado_get_create(
            empresa,
            registro.get("centro_resultado_descricao"),
            cache_centros,
        )

        item_base = dict(registro)
        item_base["parceiro"] = parceiro
        item_base["operacao"] = operacao
        item_base["natureza"] = natureza
        item_base["centro_resultado"] = centro_resultado
        item_base["cidade_parceiro_nome"] = (
            getattr(getattr(parceiro, "cidade", None), "nome", "")
            or registro.get("cidade_parceiro_nome")
            or ""
        )

        produtos = produtos_por_nota.get(registro.get("numero_nota")) or []
        if not produtos:
            item = dict(item_base)
            item["produto"] = None
            item["quantidade_saida"] = Decimal("0")
            item["__global_index"] = indice_global
            indice_global += 1
            registros_expandido.append(item)
            continue

        for produto_info in produtos:
            item = dict(item_base)
            item["produto"] = _produto_get_create_por_texto(
                empresa,
                produto_info.get("produto"),
                cache_produtos,
            )
            item["quantidade_saida"] = produto_info.get("quantidade_saida") or Decimal("0")
            item["__global_index"] = indice_global
            indice_global += 1
            registros_expandido.append(item)

    registros_expandido.sort(
        key=lambda item: (
            int(item.get("numero_nota") or 0),
            int(item.get("__global_index") or 0),
        )
    )

    contadores_por_nota = defaultdict(int)
    for item in registros_expandido:
        numero_nota = int(item.get("numero_nota") or 0)
        contadores_por_nota[numero_nota] += 1
        indice_produto = contadores_por_nota[numero_nota]
        item["indice_produto"] = indice_produto
        item["valor_nota_unico"] = item.get("valor_nota", Decimal("0")) if indice_produto == 1 else Decimal("0")
        item["media_unica"] = item.get("media") if indice_produto == 1 else None
        item["peso_bruto_unico"] = item.get("peso_bruto", Decimal("0")) if indice_produto == 1 else Decimal("0")

    registros_filtrados = []
    for item in registros_expandido:
        operacao_descricao = getattr(item.get("operacao"), "descricao_receita_despesa", "")
        if _normalizar_nome_coluna(operacao_descricao) in FATURAMENTO_OPERACOES_PERMITIDAS:
            registros_filtrados.append(item)

    cadastro_por_parceiro = _mapa_cadastro_carteira_faturamento(empresa)
    frete_por_cidade = _mapa_frete_tonelada_por_cidade(empresa)

    total_venda_geral = Decimal("0")
    for item in registros_filtrados:
        valor_unico = item.get("valor_nota_unico") or Decimal("0")
        total_venda_geral += valor_unico

    for item in registros_filtrados:
        parceiro = item.get("parceiro")
        chave_parceiro = _normalizar_nome_coluna(
            f"{getattr(parceiro, 'codigo', '')} - {getattr(parceiro, 'nome', '')}"
        )
        cadastro = cadastro_por_parceiro.get(chave_parceiro) or {}
        item["gerente"] = cadastro.get("gerente", "")
        item["descricao_perfil"] = cadastro.get("descricao_perfil", "")
        item["valor_frete"] = _calcular_valor_frete_faturamento(item, frete_por_cidade)

        valor_unico = item.get("valor_nota_unico") or Decimal("0")
        participacao_geral = _percentual_faturamento(valor_unico, total_venda_geral)
        # Contrato esperado: participacao cliente segue a mesma base consolidada.
        item["participacao_venda_geral"] = participacao_geral
        item["participacao_venda_cliente"] = participacao_geral

    registros_filtrados.sort(
        key=lambda item: (
            item.get("data_faturamento") or date.min,
            int(item.get("numero_nota") or 0),
            int(item.get("indice_produto") or 0),
        ),
        reverse=True,
    )

    objetos = []
    total_faturamento = 0
    for item in registros_filtrados:
        objetos.append(
            Faturamento(
                empresa=empresa,
                nome_origem=item.get("nome_origem") or "",
                data_faturamento=item.get("data_faturamento"),
                nome_empresa=item.get("nome_empresa") or "",
                parceiro=item.get("parceiro"),
                numero_nota=item.get("numero_nota") or 0,
                indice_produto=item.get("indice_produto") or 1,
                valor_nota=item.get("valor_nota") or Decimal("0"),
                participacao_venda_geral=item.get("participacao_venda_geral") or Decimal("0"),
                participacao_venda_cliente=item.get("participacao_venda_cliente") or Decimal("0"),
                valor_nota_unico=item.get("valor_nota_unico") or Decimal("0"),
                peso_bruto=item.get("peso_bruto") or Decimal("0"),
                peso_bruto_unico=item.get("peso_bruto_unico") or Decimal("0"),
                quantidade_volumes=item.get("quantidade_volumes") or Decimal("0"),
                quantidade_saida=item.get("quantidade_saida") or Decimal("0"),
                status_nfe=item.get("status_nfe") or "",
                apelido_vendedor=item.get("apelido_vendedor") or "",
                operacao=item.get("operacao"),
                natureza=item.get("natureza"),
                centro_resultado=item.get("centro_resultado"),
                tipo_movimento=item.get("tipo_movimento") or "",
                prazo_medio=item.get("prazo_medio") or Decimal("0"),
                media_unica=item.get("media_unica"),
                tipo_venda=item.get("tipo_venda") or "",
                produto=item.get("produto"),
                gerente=item.get("gerente") or "",
                descricao_perfil=item.get("descricao_perfil") or "",
                valor_frete=item.get("valor_frete"),
            )
        )

        if len(objetos) >= 1000:
            Faturamento.objects.bulk_create(objetos, batch_size=1000)
            total_faturamento += len(objetos)
            objetos = []

    if objetos:
        Faturamento.objects.bulk_create(objetos, batch_size=1000)
        total_faturamento += len(objetos)

    return {
        "arquivos": len(arquivos),
        "arquivos_faturamento_diario": len(arquivos_diario),
        "arquivos_nf_produtos": len(arquivos_produtos),
        "linhas_faturamento_diario": diario_result.get("linhas", 0),
        "linhas_nf_produtos": produtos_result.get("linhas", 0),
        "linhas": len(registros_filtrados),
        "faturamento": total_faturamento,
        "avisos": avisos,
    }


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
        data_arquivo = _data_arquivo_do_nome_arquivo(arquivo)
        if data_arquivo is None:
            avisos.append(
                f"Data do arquivo nao identificada pelo nome em '{arquivo.name}'. "
                "Registro salvo com Data Arquivo vazia."
            )

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
