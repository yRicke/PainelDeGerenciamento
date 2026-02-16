from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import unicodedata

from django.db import transaction

from ..models import Carteira, Cidade, Regiao, Venda

try:
    import xlrd
except ModuleNotFoundError:  # pragma: no cover - dependencia opcional em tempo de execucao
    xlrd = None


XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _coluna_para_indice(referencia: str) -> int:
    letras = "".join(ch for ch in referencia if ch.isalpha()).upper()
    indice = 0
    for ch in letras:
        indice = indice * 26 + (ord(ch) - 64)
    return indice - 1


def _texto_compartilhado(zf: zipfile.ZipFile) -> list[str]:
    caminho = "xl/sharedStrings.xml"
    if caminho not in zf.namelist():
        return []

    ns = {"a": XML_NS}
    raiz = ET.fromstring(zf.read(caminho))
    valores: list[str] = []
    for si in raiz.findall("a:si", ns):
        texto = "".join(node.text or "" for node in si.findall(".//a:t", ns))
        valores.append(texto)
    return valores


def _primeira_planilha(zf: zipfile.ZipFile) -> str:
    ns = {"a": XML_NS}
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels}

    primeira = wb.find("a:sheets/a:sheet", ns)
    if primeira is None:
        raise ValueError("Arquivo sem planilha.")

    rid = primeira.attrib.get(f"{{{REL_NS}}}id")
    if not rid or rid not in rel_map:
        raise ValueError("Relacionamento da planilha nao encontrado.")

    return "xl/" + rel_map[rid].lstrip("/")


def _valor_celula(celula: ET.Element, shared_strings: list[str]) -> str:
    ns = {"a": XML_NS}
    tipo = celula.attrib.get("t")

    if tipo == "inlineStr":
        return "".join(node.text or "" for node in celula.findall(".//a:t", ns))

    valor = celula.find("a:v", ns)
    if valor is None or valor.text is None:
        return ""

    if tipo == "s":
        try:
            return shared_strings[int(valor.text)]
        except (ValueError, IndexError):
            return valor.text
    return valor.text


def _iterar_linhas_xlsx(caminho: Path):
    ns_row = f"{{{XML_NS}}}row"
    ns_cell = f"{{{XML_NS}}}c"

    with zipfile.ZipFile(caminho, "r") as zf:
        shared_strings = _texto_compartilhado(zf)
        planilha = _primeira_planilha(zf)
        with zf.open(planilha) as stream:
            for _, elem in ET.iterparse(stream, events=("end",)):
                if elem.tag != ns_row:
                    continue

                celulas: dict[int, str] = {}
                for celula in elem.findall(ns_cell):
                    referencia = celula.attrib.get("r", "")
                    indice = _coluna_para_indice(referencia) if referencia else len(celulas)
                    celulas[indice] = _valor_celula(celula, shared_strings)

                if celulas:
                    max_col = max(celulas)
                    yield [celulas.get(i, "") for i in range(max_col + 1)]

                elem.clear()


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


def _to_decimal(valor, max_digits: int = 10, decimal_places: int = 2) -> Decimal:
    texto = _normalizar_texto(valor)
    if not texto:
        return Decimal("0")

    texto = texto.replace("R$", "").replace(" ", "")
    texto_lower = texto.lower()

    # Se houver virgula, assume padrao pt-BR: milhar com ponto e decimal com virgula.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    # Sem virgula, preserva ponto como decimal (ex.: 200000.0, 1.0E8).
    # Caso haja multiplos pontos sem notacao cientifica, trata como separador de milhar.
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


def _to_int(valor) -> int:
    texto = _normalizar_texto(valor)
    if not texto:
        return 0
    try:
        return int(float(texto.replace(",", ".")))
    except ValueError:
        return 0


def _to_bool(valor) -> bool:
    texto = _normalizar_texto(valor).lower()
    return texto in {"sim", "s", "true", "1"}


def _excel_date(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return None

    hoje = datetime.today()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass

    for formato_sem_ano in ("%d/%m", "%d-%m"):
        try:
            parcial = datetime.strptime(texto, formato_sem_ano)
            return datetime(hoje.year, parcial.month, parcial.day).date()
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


def _extrair_data_venda_do_nome_arquivo(caminho: Path):
    nome = caminho.stem.strip()
    try:
        return datetime.strptime(nome, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError(
            f"Nome de arquivo invalido '{caminho.name}'. Use o padrao dd.mm.aaaa (ex.: 02.01.2026.xls)."
        ) from exc


def _iterar_linhas_xls(caminho: Path):
    if xlrd is None:
        raise RuntimeError(
            "Dependencia 'xlrd' nao encontrada. Instale com: pip install xlrd==2.0.1"
        )

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


def _obter_primeiro_valor(registro: dict, nomes_coluna: list[str]):
    def _token(valor):
        return "".join(ch for ch in str(valor).lower().strip() if ch.isalnum())

    chaves = list(registro.keys())
    mapa_tokens = {chave: _token(chave) for chave in chaves}

    for nome in nomes_coluna:
        token_nome = _token(nome)
        for chave in chaves:
            token_chave = mapa_tokens[chave]
            if (
                token_chave == token_nome
                or token_nome in token_chave
                or token_chave in token_nome
            ) and _normalizar_texto(registro.get(chave)):
                return registro.get(chave)
    return ""


def _cidade_por_codigo(empresa, codigo: str, nome: str):
    defaults = {"empresa": empresa, "nome": nome}
    cidade, created = Cidade.objects.get_or_create(codigo=codigo, defaults=defaults)
    if not created and nome and cidade.nome != nome:
        cidade.nome = nome
        cidade.save(update_fields=["nome"])
    return cidade


def _regiao_por_codigo(empresa, codigo: str, nome: str):
    defaults = {"empresa": empresa, "nome": nome}
    regiao, created = Regiao.objects.get_or_create(codigo=codigo, defaults=defaults)
    if not created and nome and regiao.nome != nome:
        regiao.nome = nome
        regiao.save(update_fields=["nome"])
    return regiao


@transaction.atomic
def importar_carteira_do_diretorio(
    empresa,
    diretorio: str = "importacoes/comercial/carteira",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xlsx"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "carteiras": 0, "cidades": 0, "regioes": 0}

    if limpar_antes:
        Carteira.objects.filter(empresa=empresa).delete()

    cache_cidades: dict[str, Cidade] = {}
    cache_regioes: dict[str, Regiao] = {}
    total_linhas = 0
    total_carteiras = 0

    objetos: list[Carteira] = []
    colunas_obrigatorias = {"Nome Parceiro", "Cód. Cidade", "Região", "Nome (Cidade)", "Nome (Região)"}

    for arquivo in arquivos:
        cabecalho = None
        for linha in _iterar_linhas_xlsx(arquivo):
            if cabecalho is None:
                if colunas_obrigatorias.issubset(set(linha)):
                    cabecalho = linha
                continue

            if not any(linha):
                continue

            registro = {cabecalho[i]: (linha[i] if i < len(linha) else "") for i in range(len(cabecalho))}
            nome_parceiro = _normalizar_texto(registro.get("Nome Parceiro"))
            if not nome_parceiro:
                continue

            codigo_cidade = _normalizar_codigo(registro.get("Cód. Cidade"))
            nome_cidade = _normalizar_texto(registro.get("Nome (Cidade)"))
            cidade = None
            if codigo_cidade:
                cidade = cache_cidades.get(codigo_cidade)
                if cidade is None:
                    cidade = _cidade_por_codigo(empresa, codigo_cidade, nome_cidade)
                    cache_cidades[codigo_cidade] = cidade

            codigo_regiao = _normalizar_codigo(registro.get("Região"))
            nome_regiao = _normalizar_texto(registro.get("Nome (Região)"))
            regiao = None
            if codigo_regiao:
                regiao = cache_regioes.get(codigo_regiao)
                if regiao is None:
                    regiao = _regiao_por_codigo(empresa, codigo_regiao, nome_regiao)
                    cache_regioes[codigo_regiao] = regiao

            intervalo_str = _normalizar_texto(registro.get("Intervalo p/ análise de crédito"))
            valor_data_cadastro = _obter_primeiro_valor(
                registro,
                [
                    "Data de cadastramento",
                    "Data Cadastramento",
                    "Data cadastramento",
                    "Data de cadastro",
                    "Data Cadastro",
                    "Cadastro",
                ],
            )
            data_cadastro = _excel_date(valor_data_cadastro)
            objetos.append(
                Carteira(
                    empresa=empresa,
                    regiao=regiao,
                    cidade=cidade,
                    valor_faturado=_to_decimal(registro.get("Vlr. Faturado")),
                    limite_credito=_to_decimal(registro.get("Limite de crédito")),
                    ultima_venda=_excel_date(registro.get("Última venda [SAFIA]")),
                    qtd_dias_sem_venda=_to_int(intervalo_str),
                    intervalo=intervalo_str,
                    data_cadastro=data_cadastro or datetime.today().date(),
                    gerente=_normalizar_texto(registro.get("Gerente")),
                    vendedor=_normalizar_texto(registro.get("Apelido (Vendedor)")),
                    descricao_perfil=_normalizar_texto(registro.get("Descrição (Perfil)")),
                    nome_parceiro=nome_parceiro,
                    ativo_indicador=_to_bool(registro.get("Ativo")),
                    cliente_indicador=_to_bool(registro.get("Cliente")),
                    fornecedor_indicador=_to_bool(registro.get("Fornecedor")),
                    transporte_indicador=_to_bool(registro.get("Transportadora")),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Carteira.objects.bulk_create(objetos, batch_size=1000)
                total_carteiras += len(objetos)
                objetos = []

    if objetos:
        Carteira.objects.bulk_create(objetos, batch_size=1000)
        total_carteiras += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "carteiras": total_carteiras,
        "cidades": len(cache_cidades),
        "regioes": len(cache_regioes),
    }


@transaction.atomic
def importar_vendas_do_diretorio(
    empresa,
    diretorio: str = "importacoes/comercial/vendas",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "vendas": 0}

    if limpar_antes:
        Venda.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_vendas = 0
    objetos: list[Venda] = []

    mapeamento_colunas = {
        "codigo": ["codigo", "codigoproduto", "cod"],
        "descricao": ["descricao", "descricaoproduto", "produto"],
        "valor_venda": ["vlrvendas", "valorvenda", "vendas"],
        "qtd_notas": ["qtdnotas", "quantidadenotas", "qtdnota"],
        "custo_medio_icms_cmv": ["customedcomicmscmv", "customedioicmscmv", "cmv", "custo"],
        "peso_bruto": ["pesobruto"],
        "peso_liquido": ["pesoliquido"],
    }

    for arquivo in arquivos:
        data_venda = _extrair_data_venda_do_nome_arquivo(arquivo)
        cabecalho = None
        indices = None

        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if cabecalho is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                    idx_map[chave] = idx
                if idx_map["codigo"] is not None and idx_map["valor_venda"] is not None:
                    cabecalho = linha
                    indices = idx_map
                continue

            if indices is None:
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            codigo = _normalizar_codigo(_valor_por_indice("codigo"))
            if not codigo:
                continue

            descricao = _normalizar_texto(_valor_por_indice("descricao"))
            valor_venda = _to_decimal(_valor_por_indice("valor_venda"))
            custo_medio = _to_decimal(_valor_por_indice("custo_medio_icms_cmv"))
            peso_bruto = _to_decimal(_valor_por_indice("peso_bruto"))
            peso_liquido = _to_decimal(_valor_por_indice("peso_liquido"))
            qtd_notas = max(0, _to_int(_valor_por_indice("qtd_notas")))
            lucro = valor_venda - custo_medio
            margem = Decimal("0")
            if valor_venda > 0:
                margem = (lucro / valor_venda) * Decimal("100")

            objetos.append(
                Venda(
                    empresa=empresa,
                    codigo=codigo,
                    descricao=descricao,
                    valor_venda=valor_venda,
                    qtd_notas=qtd_notas,
                    custo_medio_icms_cmv=custo_medio,
                    lucro=lucro,
                    peso_bruto=peso_bruto,
                    peso_liquido=peso_liquido,
                    margem=margem,
                    data_venda=data_venda,
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Venda.objects.bulk_create(objetos, batch_size=1000)
                total_vendas += len(objetos)
                objetos = []

    if objetos:
        Venda.objects.bulk_create(objetos, batch_size=1000)
        total_vendas += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "vendas": total_vendas,
    }
