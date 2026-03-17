from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import unicodedata

from django.db import transaction
from django.utils import timezone

from ..models import Carteira, Cidade, ControleMargem, PedidoPendente, Parceiro, Regiao, Rota, Venda
from .comercial import _sincronizar_descricao_perfil
from .controle_margem_regras import (
    calcular_campos_controle_margem_legado,
    obter_parametros_controle_margem,
)

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


def _primeira_planilha(zf: zipfile.ZipFile, nome_planilha: str | None = None) -> str:
    ns = {"a": XML_NS}
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels}

    planilha = None
    if nome_planilha:
        nome_planilha_normalizado = _normalizar_texto(nome_planilha).lower()
        for sheet in wb.findall("a:sheets/a:sheet", ns):
            nome_atual = _normalizar_texto(sheet.attrib.get("name", "")).lower()
            if nome_atual == nome_planilha_normalizado:
                planilha = sheet
                break
        if planilha is None:
            raise ValueError(f"Planilha '{nome_planilha}' nao encontrada.")
    else:
        planilha = wb.find("a:sheets/a:sheet", ns)
        if planilha is None:
            raise ValueError("Arquivo sem planilha.")

    rid = planilha.attrib.get(f"{{{REL_NS}}}id")
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


def _iterar_linhas_xlsx(caminho: Path, nome_planilha: str | None = None):
    ns_row = f"{{{XML_NS}}}row"
    ns_cell = f"{{{XML_NS}}}c"

    with zipfile.ZipFile(caminho, "r") as zf:
        shared_strings = _texto_compartilhado(zf)
        planilha = _primeira_planilha(zf, nome_planilha=nome_planilha)
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


def _normalizar_ultima_venda_carteira(valor):
    data = _excel_date(valor)
    if data == date(2000, 1, 1):
        return None
    return data


def _dias_sem_venda_carteira(ultima_venda):
    if not ultima_venda:
        return 0
    dias = (timezone.localdate() - ultima_venda).days
    return max(0, int(dias))


def _intervalo_carteira(ultima_venda):
    if not ultima_venda:
        return Carteira.INTERVALO_SEM_VENDA
    dias = _dias_sem_venda_carteira(ultima_venda)
    if dias <= 5:
        return Carteira.INTERVALO_0_5
    if dias <= 30:
        return Carteira.INTERVALO_6_30
    if dias <= 60:
        return Carteira.INTERVALO_31_60
    if dias <= 90:
        return Carteira.INTERVALO_61_90
    if dias <= 120:
        return Carteira.INTERVALO_91_120
    if dias <= 180:
        return Carteira.INTERVALO_121_180
    return Carteira.INTERVALO_180_MAIS


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


def _iterar_linhas_xls(caminho: Path, nome_planilha: str | None = None):
    if xlrd is None:
        raise RuntimeError(
            "Dependencia 'xlrd' nao encontrada. Instale com: pip install xlrd==2.0.1"
        )

    workbook = xlrd.open_workbook(str(caminho))
    if workbook.nsheets <= 0:
        return

    if nome_planilha:
        sheet = next(
            (workbook.sheet_by_index(i) for i in range(workbook.nsheets) if _normalizar_texto(workbook.sheet_by_index(i).name).lower() == _normalizar_texto(nome_planilha).lower()),
            None,
        )
        if sheet is None:
            raise ValueError(f"Planilha '{nome_planilha}' nao encontrada.")
    else:
        sheet = workbook.sheet_by_index(0)

    for row_idx in range(sheet.nrows):
        linha = []
        for col_idx in range(sheet.ncols):
            valor = sheet.cell_value(row_idx, col_idx)
            if isinstance(valor, float) and valor.is_integer():
                valor = int(valor)
            linha.append(valor)
        yield linha


def _iterar_linhas_planilha(caminho: Path, nome_planilha: str | None = None):
    sufixo = caminho.suffix.lower()
    if sufixo == ".xlsx":
        return _iterar_linhas_xlsx(caminho, nome_planilha=nome_planilha)
    if sufixo == ".xls":
        return _iterar_linhas_xls(caminho, nome_planilha=nome_planilha)
    raise ValueError(f"Formato de arquivo invalido: {caminho.name}. Use .xls ou .xlsx.")


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


def _valor_coluna(registro: dict, nome_coluna: str):
    valor_base = registro.get(nome_coluna, "")
    if _normalizar_texto(valor_base):
        return valor_base
    prefixo = f"{nome_coluna}__"
    for chave, valor in registro.items():
        if chave.startswith(prefixo) and _normalizar_texto(valor):
            return valor
    return valor_base


def _gerente_valido_ou_vazio(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return ""
    if texto.upper() in {"<SEM VENDEDOR>", "SEM VENDEDOR", "<SEM GERENTE>", "SEM GERENTE"}:
        return ""
    return texto


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


def _parceiro_por_codigo_nome(empresa, codigo: str, nome: str):
    return Parceiro.obter_ou_criar_por_codigo_nome(empresa=empresa, codigo=codigo, nome=nome)


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


@transaction.atomic
def importar_carteira_do_diretorio(
    empresa,
    diretorio: str = "importacoes/comercial/carteira",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xlsx"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "carteiras": 0, "cidades": 0, "regioes": 0, "avisos": []}

    if limpar_antes:
        Carteira.objects.filter(empresa=empresa).delete()

    cache_cidades: dict[str, Cidade] = {}
    cache_regioes: dict[str, Regiao] = {}
    cache_descricoes_perfil: dict[str, str] = {}
    total_linhas = 0
    total_carteiras = 0
    avisos: list[str] = []

    objetos: list[Carteira] = []
    colunas_obrigatorias = {"Cód. Parceiro", "Nome Parceiro", "Cód. Cidade", "Região", "Nome (Cidade)", "Nome (Região)"}
    colunas_opcionais = {
        "Vlr. Faturado",
        "Limite de crédito",
        "Gerente",
        "Apelido (Vendedor)",
        "Descrição (Perfil)",
        "Ativo",
        "Cliente",
        "Fornecedor",
        "Transportadora",
        "Última venda [SAFIA]",
    }
    aliases_data_cadastro = {
        "Data de cadastramento",
        "Data Cadastramento",
        "Data cadastramento",
        "Data de cadastro",
        "Data Cadastro",
        "Cadastro",
    }

    for arquivo in arquivos:
        cabecalho = None
        cabecalho_set = set()
        for linha in _iterar_linhas_xlsx(arquivo):
            if cabecalho is None:
                if colunas_obrigatorias.issubset(set(linha)):
                    cabecalho = linha
                    cabecalho_set = {str(col).strip() for col in cabecalho if str(col).strip()}
                    faltantes_opcionais = [col for col in sorted(colunas_opcionais) if col not in cabecalho_set]
                    if not aliases_data_cadastro.intersection(cabecalho_set):
                        faltantes_opcionais.append("Data de cadastramento")
                    _registrar_aviso_colunas(
                        avisos,
                        nome_arquivo=arquivo.name,
                        faltantes=faltantes_opcionais,
                    )
                continue

            if not any(linha):
                continue

            registro = {cabecalho[i]: (linha[i] if i < len(linha) else "") for i in range(len(cabecalho))}
            codigo_parceiro = _normalizar_codigo(registro.get("Cód. Parceiro"))
            nome_parceiro = _normalizar_texto(registro.get("Nome Parceiro"))
            if not codigo_parceiro or not nome_parceiro:
                continue
            parceiro = _parceiro_por_codigo_nome(empresa=empresa, codigo=codigo_parceiro, nome=nome_parceiro)

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
            ultima_venda = _normalizar_ultima_venda_carteira(registro.get("Última venda [SAFIA]"))
            descricao_perfil = _sincronizar_descricao_perfil(
                empresa,
                _normalizar_texto(registro.get("Descrição (Perfil)")),
                cache=cache_descricoes_perfil,
            )
            objetos.append(
                Carteira(
                    empresa=empresa,
                    regiao=regiao,
                    cidade=cidade,
                    valor_faturado=_to_decimal(registro.get("Vlr. Faturado")),
                    limite_credito=_to_decimal(registro.get("Limite de crédito")),
                    ultima_venda=ultima_venda,
                    qtd_dias_sem_venda=_dias_sem_venda_carteira(ultima_venda),
                    intervalo=_intervalo_carteira(ultima_venda),
                    data_cadastro=data_cadastro or datetime.today().date(),
                    gerente=_normalizar_texto(registro.get("Gerente")),
                    vendedor=_normalizar_texto(registro.get("Apelido (Vendedor)")),
                    descricao_perfil=descricao_perfil,
                    parceiro=parceiro,
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

        if cabecalho is None:
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=sorted(colunas_obrigatorias),
                obrigatorias=colunas_obrigatorias,
            )

    if objetos:
        Carteira.objects.bulk_create(objetos, batch_size=1000)
        total_carteiras += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "carteiras": total_carteiras,
        "cidades": len(cache_cidades),
        "regioes": len(cache_regioes),
        "avisos": avisos,
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
        return {"arquivos": 0, "linhas": 0, "vendas": 0, "avisos": []}

    if limpar_antes:
        Venda.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_vendas = 0
    objetos: list[Venda] = []
    avisos: list[str] = []

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
        melhor_idx_map = None
        melhor_score = -1
        obrigatorias = {"codigo", "valor_venda"}

        for linha in _iterar_linhas_xls(arquivo):
            if not any(_normalizar_texto(v) for v in linha):
                continue

            if cabecalho is None:
                normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
                idx_map = {}
                for chave, aliases in mapeamento_colunas.items():
                    idx = next((i for i, token in enumerate(normalizadas) if token in aliases), None)
                    idx_map[chave] = idx
                score = sum(1 for idx in idx_map.values() if idx is not None)
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx_map = idx_map
                if idx_map["codigo"] is not None and idx_map["valor_venda"] is not None:
                    cabecalho = linha
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

        if indices is None:
            faltantes = _colunas_nao_identificadas(melhor_idx_map, mapeamento_colunas.keys())
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=faltantes,
                obrigatorias=obrigatorias,
            )

    if objetos:
        Venda.objects.bulk_create(objetos, batch_size=1000)
        total_vendas += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "vendas": total_vendas,
        "avisos": avisos,
    }


def _split_codigo_nome(valor_texto: str):
    texto = _normalizar_texto(valor_texto)
    if not texto:
        return "", ""

    if " - " in texto:
        codigo, nome = texto.split(" - ", 1)
        return _normalizar_codigo(codigo), _normalizar_texto(nome)

    return _normalizar_codigo(texto), _normalizar_texto(texto)


def _limpar_valor_tonelada_frete(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return "0"
    texto = texto.replace("/", "")
    texto = texto.replace("TON", "").replace("ton", "")
    return texto.strip()


def _to_decimal_percentual(valor, decimal_places: int = 9):
    texto = _normalizar_texto(valor)
    if not texto:
        return Decimal("0")
    tem_percentual = "%" in texto
    texto = texto.replace("%", "")
    numero = _to_decimal(texto, max_digits=18, decimal_places=decimal_places)
    if tem_percentual:
        return numero / Decimal("100")
    return numero


def _rota_por_codigo_nome(empresa, codigo: str, nome: str):
    if not codigo:
        return None
    rota = Rota.objects.filter(empresa=empresa, codigo_rota=codigo).first()
    if not rota:
        rota = Rota.criar_rota(empresa=empresa, codigo_rota=codigo, nome=nome or codigo, uf=None)
        return rota
    if nome and rota.nome != nome:
        rota.nome = nome
        rota.save(update_fields=["nome"])
    return rota


@transaction.atomic
def importar_pedidos_pendentes_do_diretorio(
    empresa,
    diretorio: str = "importacoes/comercial/pedidos_pendentes",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xlsx"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "pedidos_pendentes": 0,
            "rotas": 0,
            "regioes": 0,
            "parceiros": 0,
            "avisos": [],
        }

    if limpar_antes:
        PedidoPendente.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_pedidos = 0
    rotas_criadas = 0
    regioes_criadas = 0
    parceiros_criados = 0
    avisos: list[str] = []

    cache_rotas: dict[str, Rota] = {}
    cache_regioes: dict[str, Regiao] = {}
    cache_parceiros: dict[str, Parceiro] = {}

    objetos: list[PedidoPendente] = []
    titulos_obrigatorios = {
        "Valor Tonelada Frete[SAFIA]",
        "Dt. Neg.",
        "Previsão de entrega",
        "Nro. Único",
        "Parceiro",
        "Nome Parceiro (Parceiro)",
        "Vlr. Nota",
        "Descrição (Tipo de Negociação)",
        "Apelido (Vendedor)",
        "Nome Cidade Parceiro [SAFIA]",
        "Peso bruto",
        "Pendente",
        "Nro. Nota",
        "Tipo da Venda",
        "Peso",
        "Empresa",
        "Nome Fantasia (Empresa)",
        "Peso liq. dos Itens",
        "Região",
        "Rota",
    }

    for arquivo in arquivos:
        cabecalho = None
        for idx, linha in enumerate(_iterar_linhas_xlsx(arquivo)):
            if idx < 2:
                continue

            if cabecalho is None:
                cabecalho = linha
                cabecalho_set = {str(col).strip() for col in cabecalho if str(col).strip()}
                faltantes = sorted(titulos_obrigatorios - cabecalho_set)
                if faltantes:
                    raise ValueError(
                        "Titulos obrigatorios ausentes no arquivo "
                        f"'{arquivo.name}': {', '.join(faltantes)}"
                    )
                continue

            if not any(_normalizar_texto(v) for v in linha):
                continue

            registro = {}
            for i in range(len(cabecalho)):
                chave_base = cabecalho[i]
                chave = chave_base
                sufixo = 2
                while chave in registro:
                    chave = f"{chave_base}__{sufixo}"
                    sufixo += 1
                registro[chave] = linha[i] if i < len(linha) else ""

            nome_fantasia_empresa = _normalizar_texto(_valor_coluna(registro, "Nome Fantasia (Empresa)"))
            if not nome_fantasia_empresa:
                continue

            empresa_codigo = _normalizar_codigo(_valor_coluna(registro, "Empresa"))
            nome_empresa = " - ".join(
                [parte for parte in [empresa_codigo, nome_fantasia_empresa] if parte]
            )

            parceiro_codigo = _normalizar_codigo(_valor_coluna(registro, "Parceiro"))
            parceiro_nome = _normalizar_texto(_valor_coluna(registro, "Nome Parceiro (Parceiro)"))
            cod_nome_parceiro = " - ".join(
                [parte for parte in [parceiro_codigo, parceiro_nome] if parte]
            )

            parceiro = None
            if parceiro_codigo:
                parceiro = cache_parceiros.get(parceiro_codigo)
                if parceiro is None:
                    parceiro_existia = Parceiro.objects.filter(empresa=empresa, codigo=parceiro_codigo).exists()
                    parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                        empresa=empresa,
                        codigo=parceiro_codigo,
                        nome=parceiro_nome,
                    )
                    cache_parceiros[parceiro_codigo] = parceiro
                    if not parceiro_existia:
                        parceiros_criados += 1

            rota_texto = _normalizar_texto(_valor_coluna(registro, "Rota"))
            rota_codigo, rota_nome = _split_codigo_nome(rota_texto)
            rota = None
            if rota_codigo:
                rota = cache_rotas.get(rota_codigo)
                if rota is None:
                    rota_existia = Rota.objects.filter(empresa=empresa, codigo_rota=rota_codigo).exists()
                    rota = _rota_por_codigo_nome(empresa, rota_codigo, rota_nome)
                    cache_rotas[rota_codigo] = rota
                    if rota and not rota_existia:
                        rotas_criadas += 1

            regiao_texto = _normalizar_texto(_valor_coluna(registro, "Região"))
            regiao_codigo, regiao_nome = _split_codigo_nome(regiao_texto)
            regiao = None
            if regiao_codigo:
                regiao = cache_regioes.get(regiao_codigo)
                if regiao is None:
                    regiao_existia = Regiao.objects.filter(codigo=regiao_codigo).exists()
                    regiao = _regiao_por_codigo(empresa, regiao_codigo, regiao_nome)
                    cache_regioes[regiao_codigo] = regiao
                    if regiao and not regiao_existia:
                        regioes_criadas += 1

            dt_neg = _excel_date(_valor_coluna(registro, "Dt. Neg."))
            previsao_entrega = _excel_date(_valor_coluna(registro, "Previsão de entrega"))
            data_para_calculo = previsao_entrega or dt_neg

            gerente = ""
            if parceiro:
                carteira_item = (
                    Carteira.objects.filter(empresa=empresa, parceiro=parceiro)
                    .exclude(gerente="")
                    .exclude(gerente__iexact="<SEM VENDEDOR>")
                    .exclude(gerente__iexact="SEM VENDEDOR")
                    .exclude(gerente__iexact="<SEM GERENTE>")
                    .exclude(gerente__iexact="SEM GERENTE")
                    .order_by("-data_cadastro", "-id")
                    .first()
                )
                if carteira_item:
                    gerente = _gerente_valido_ou_vazio(carteira_item.gerente)

            objetos.append(
                PedidoPendente(
                    empresa=empresa,
                    numero_unico=_normalizar_codigo(_valor_coluna(registro, "Nro. Único")),
                    rota=rota,
                    regiao=regiao,
                    parceiro=parceiro,
                    rota_texto=rota_texto,
                    regiao_texto=regiao_texto,
                    valor_tonelada_frete_safia=_normalizar_texto(_valor_coluna(registro, "Valor Tonelada Frete[SAFIA]")),
                    pendente=_normalizar_texto(_valor_coluna(registro, "Pendente")),
                    nome_cidade_parceiro_safia=_normalizar_texto(_valor_coluna(registro, "Nome Cidade Parceiro [SAFIA]")),
                    previsao_entrega=previsao_entrega,
                    dt_neg=dt_neg,
                    prazo_maximo=3,
                    tipo_venda=_normalizar_texto(_valor_coluna(registro, "Tipo da Venda")),
                    nome_empresa=nome_empresa,
                    cod_nome_parceiro=cod_nome_parceiro,
                    vlr_nota=_to_decimal(_valor_coluna(registro, "Vlr. Nota"), max_digits=12, decimal_places=2),
                    peso_bruto=_to_decimal(_valor_coluna(registro, "Peso bruto"), max_digits=12, decimal_places=2),
                    peso=_to_decimal(_valor_coluna(registro, "Peso"), max_digits=12, decimal_places=2),
                    peso_liq_itens=_to_decimal(_valor_coluna(registro, "Peso liq. dos Itens"), max_digits=12, decimal_places=2),
                    apelido_vendedor=_normalizar_texto(_valor_coluna(registro, "Apelido (Vendedor)")),
                    gerente=gerente,
                    data_para_calculo=data_para_calculo,
                    descricao_tipo_negociacao=_normalizar_texto(_valor_coluna(registro, "Descrição (Tipo de Negociação)")),
                    nro_nota=_to_int(_valor_coluna(registro, "Nro. Nota")),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                PedidoPendente.objects.bulk_create(objetos, batch_size=1000)
                total_pedidos += len(objetos)
                objetos = []

    if objetos:
        PedidoPendente.objects.bulk_create(objetos, batch_size=1000)
        total_pedidos += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "pedidos_pendentes": total_pedidos,
        "rotas": rotas_criadas,
        "regioes": regioes_criadas,
        "parceiros": parceiros_criados,
        "avisos": avisos,
    }


@transaction.atomic
def importar_controle_margem_do_diretorio(
    empresa,
    diretorio: str = "importacoes/comercial/controle_de_margem",
    limpar_antes: bool = False,
):
    base = Path(diretorio)
    arquivos = sorted(
        [
            *base.glob("*.xlsx"),
            *base.glob("*.xls"),
        ]
    )
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "criados": 0,
            "atualizados": 0,
            "parceiros_criados": 0,
            "erros": 0,
            "avisos": [],
        }

    if limpar_antes:
        ControleMargem.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_criados = 0
    total_atualizados = 0
    total_erros = 0
    parceiros_criados = 0
    avisos: list[str] = []

    cache_parceiros: dict[str, Parceiro] = {}
    cache_carteiras: dict[int, Carteira | None] = {}
    cache_descricoes_perfil: dict[str, str] = {}
    parametros = obter_parametros_controle_margem(empresa)

    titulos_obrigatorios = {
        "Nro. Único",
        "Parceiro",
        "Nome Parceiro (Parceiro)",
        "Vlr. Nota",
        "Custo Total do Produto",
        "Peso bruto",
    }
    titulos_opcionais = {
        "Empresa",
        "Nome Fantasia (Empresa)",
        "Dt. Neg.",
        "Previsão de entrega",
        "Tipo da Venda",
        "Apelido (Vendedor)",
        "Valor Tonelada Frete[SAFIA]",
    }

    for arquivo in arquivos:
        data_origem = arquivo.stem
        cabecalho = None
        iterador_linhas = _iterar_linhas_planilha(arquivo, nome_planilha="new sheet")

        for idx, linha in enumerate(iterador_linhas):
            if idx < 2:
                continue

            if cabecalho is None:
                cabecalho = linha
                cabecalho_set = {str(col).strip() for col in cabecalho if str(col).strip()}
                faltantes = sorted(titulos_obrigatorios - cabecalho_set)
                if faltantes:
                    raise ValueError(
                        "Titulos obrigatorios ausentes no arquivo "
                        f"'{arquivo.name}': {', '.join(faltantes)}"
                    )
                faltantes_opcionais = [col for col in sorted(titulos_opcionais) if col not in cabecalho_set]
                _registrar_aviso_colunas(
                    avisos,
                    nome_arquivo=arquivo.name,
                    faltantes=faltantes_opcionais,
                )
                continue

            if not any(_normalizar_texto(v) for v in linha):
                continue

            registro = {}
            for i in range(len(cabecalho)):
                chave_base = cabecalho[i]
                chave = chave_base
                sufixo = 2
                while chave in registro:
                    chave = f"{chave_base}__{sufixo}"
                    sufixo += 1
                registro[chave] = linha[i] if i < len(linha) else ""

            nro_unico_texto = _normalizar_codigo(_valor_coluna(registro, "Nro. Único"))
            if not nro_unico_texto:
                continue

            try:
                nro_unico = int(Decimal(nro_unico_texto.replace(",", ".")))
            except (InvalidOperation, ValueError):
                total_erros += 1
                continue

            parceiro_codigo = _normalizar_codigo(_valor_coluna(registro, "Parceiro"))
            parceiro_nome = _normalizar_texto(_valor_coluna(registro, "Nome Parceiro (Parceiro)"))
            cod_nome_parceiro = " - ".join([parte for parte in [parceiro_codigo, parceiro_nome] if parte])
            if cod_nome_parceiro.upper() == "3620 - SAFIA DISTRIBUIDORA DE ALIMENTOS FILIAL":
                continue

            parceiro = None
            if parceiro_codigo:
                parceiro = cache_parceiros.get(parceiro_codigo)
                if parceiro is None:
                    parceiro_existia = Parceiro.objects.filter(empresa=empresa, codigo=parceiro_codigo).exists()
                    parceiro = Parceiro.obter_ou_criar_por_codigo_nome(
                        empresa=empresa,
                        codigo=parceiro_codigo,
                        nome=parceiro_nome,
                    )
                    cache_parceiros[parceiro_codigo] = parceiro
                    if not parceiro_existia:
                        parceiros_criados += 1

            carteira_item = None
            if parceiro:
                carteira_item = cache_carteiras.get(parceiro.id)
                if parceiro.id not in cache_carteiras:
                    carteira_item = (
                        Carteira.objects.filter(empresa=empresa, parceiro=parceiro)
                        .order_by("-data_cadastro", "-id")
                        .first()
                    )
                    cache_carteiras[parceiro.id] = carteira_item

            empresa_codigo = _normalizar_codigo(_valor_coluna(registro, "Empresa"))
            nome_fantasia_empresa = _normalizar_texto(_valor_coluna(registro, "Nome Fantasia (Empresa)"))
            nome_empresa = " - ".join([parte for parte in [empresa_codigo, nome_fantasia_empresa] if parte])

            vlr_nota = _to_decimal(_valor_coluna(registro, "Vlr. Nota"), max_digits=16, decimal_places=6)
            custo_total_produto = _to_decimal(_valor_coluna(registro, "Custo Total do Produto"), max_digits=16, decimal_places=6)
            peso_bruto = _to_decimal(_valor_coluna(registro, "Peso bruto"), max_digits=16, decimal_places=6)
            valor_tonelada_frete_safia = _to_decimal(
                _limpar_valor_tonelada_frete(_valor_coluna(registro, "Valor Tonelada Frete[SAFIA]")),
                max_digits=16,
                decimal_places=6,
            )
            gerente_valor = (_gerente_valido_ou_vazio(carteira_item.gerente) if carteira_item else None)
            tipo_venda_valor = _normalizar_texto(_valor_coluna(registro, "Tipo da Venda")) or None
            calculados = calcular_campos_controle_margem_legado(
                nome_empresa=nome_empresa,
                gerente=gerente_valor,
                tipo_venda=tipo_venda_valor,
                vlr_nota=vlr_nota,
                custo_total_produto=custo_total_produto,
                peso_bruto=peso_bruto,
                valor_tonelada_frete_safia=valor_tonelada_frete_safia,
                taxa_vendas_percentual=parametros["vendas"].remuneracao_percentual,
                taxa_operador_logistica_rs=parametros["logistica"].remuneracao_rs,
                taxa_administracao_percentual=parametros["administracao"].remuneracao_percentual,
                taxa_financeiro_mes=parametros["financeiro"].taxa_ao_mes,
            )

            defaults = {
                "data_origem": data_origem,
                "nome_empresa": nome_empresa,
                "parceiro": parceiro,
                "cod_nome_parceiro": cod_nome_parceiro,
                "descricao_perfil": _sincronizar_descricao_perfil(
                    empresa,
                    (carteira_item.descricao_perfil if carteira_item else None),
                    vazio_como_none=True,
                    cache=cache_descricoes_perfil,
                ),
                "apelido_vendedor": _normalizar_texto(_valor_coluna(registro, "Apelido (Vendedor)")) or None,
                "gerente": gerente_valor,
                "dt_neg": _excel_date(_valor_coluna(registro, "Dt. Neg.")),
                "previsao_entrega": _excel_date(_valor_coluna(registro, "Previsão de entrega")),
                "tipo_venda": tipo_venda_valor,
                "vlr_nota": vlr_nota,
                "custo_total_produto": custo_total_produto,
                "margem_bruta": calculados["margem_bruta"],
                "lucro_bruto": calculados["lucro_bruto"],
                "valor_tonelada_frete_safia": valor_tonelada_frete_safia,
                "peso_bruto": peso_bruto,
                "custo_por_kg": calculados["custo_por_kg"],
                "vendas": calculados["vendas"],
                "producao": calculados["producao"],
                "operador_logistica": calculados["operador_logistica"],
                "frete_distribuicao": calculados["frete_distribuicao"],
                "total_logistica": calculados["total_logistica"],
                "administracao": calculados["administracao"],
                "financeiro": calculados["financeiro"],
                "total_setores": calculados["total_setores"],
                "valor_liquido": calculados["valor_liquido"],
                "margem_liquida": calculados["margem_liquida"],
            }

            _, criado = ControleMargem.objects.update_or_create(
                empresa=empresa,
                nro_unico=nro_unico,
                defaults=defaults,
            )
            if criado:
                total_criados += 1
            else:
                total_atualizados += 1
            total_linhas += 1

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "criados": total_criados,
        "atualizados": total_atualizados,
        "parceiros_criados": parceiros_criados,
        "erros": total_erros,
        "avisos": avisos,
    }
