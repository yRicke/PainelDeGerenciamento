from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

from django.db import transaction
from django.utils import timezone

from ..models import Cargas, Producao, Produto, Regiao

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
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def _normalizar_nome_coluna(valor: str) -> str:
    texto = _normalizar_texto(valor).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return "".join(ch for ch in texto if ch.isalnum())


def _to_int(valor) -> int:
    texto = _normalizar_texto(valor)
    if not texto:
        return 0
    try:
        return max(0, int(float(texto.replace(",", "."))))
    except ValueError:
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


def _excel_datetime(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return None

    for formato in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(texto, formato)
            if "H" not in formato:
                return datetime.combine(parsed.date(), datetime.min.time())
            return parsed
        except ValueError:
            pass

    try:
        serial = float(texto.replace(",", "."))
    except ValueError:
        return None

    if serial <= 0:
        return None
    return datetime(1899, 12, 30) + timedelta(days=serial)


def _to_decimal(valor) -> Decimal:
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
        return Decimal(texto)
    except InvalidOperation:
        return Decimal("0")


def _extrair_kg_da_descricao_produto(descricao: str) -> Decimal:
    texto = _normalizar_texto(descricao).upper()
    if not texto:
        return Decimal("0")

    match_multiplicado = re.search(r"(\d+)\s*[Xx]\s*(\d+)\s*KG", texto)
    if match_multiplicado:
        a = Decimal(match_multiplicado.group(1))
        b = Decimal(match_multiplicado.group(2))
        return a * b

    match_simples = re.search(r"(\d+)\s*KG", texto)
    if match_simples:
        return Decimal(match_simples.group(1))

    return Decimal("0")


def _as_aware_datetime(valor):
    if not valor:
        return None
    if timezone.is_aware(valor):
        return valor
    return timezone.make_aware(valor, timezone.get_current_timezone())


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


def _detectar_indices_colunas(linhas, mapeamento_colunas, obrigatorias=None):
    melhor_score = -1
    melhor_indices = None

    for linha in linhas:
        if not any(_normalizar_texto(v) for v in linha):
            continue

        normalizadas = [_normalizar_nome_coluna(valor) for valor in linha]
        idx_map = {}
        for chave, aliases in mapeamento_colunas.items():
            idx = None
            for alias in aliases:
                idx = next((i for i, token in enumerate(normalizadas) if token == alias), None)
                if idx is not None:
                    break
            idx_map[chave] = idx

        score = sum(1 for valor in idx_map.values() if valor is not None)
        if score > melhor_score:
            melhor_score = score
            melhor_indices = idx_map

    if melhor_score < 3:
        return None
    if obrigatorias:
        for coluna in obrigatorias:
            if melhor_indices is None or melhor_indices.get(coluna) is None:
                return None
    return melhor_indices


def _primeiro_valor_do_registro(registro: dict, aliases: list[str]):
    for alias in aliases:
        if alias in registro and _normalizar_texto(registro.get(alias)):
            return registro.get(alias)
    return ""


def _resolver_regiao(empresa, codigo_regiao: str, nome_regiao: str):
    codigo = _normalizar_codigo(codigo_regiao)
    nome = _normalizar_texto(nome_regiao)
    if codigo:
        defaults = {"empresa": empresa, "nome": nome or codigo}
        regiao, created = Regiao.objects.get_or_create(codigo=codigo, defaults=defaults)
        if not created and nome and regiao.nome != nome:
            regiao.nome = nome
            regiao.save(update_fields=["nome"])
        return regiao
    if nome:
        return Regiao.objects.filter(empresa=empresa, nome=nome).first()
    return None


@transaction.atomic
def importar_cargas_do_diretorio(
    empresa,
    diretorio: str = "importacoes/operacional/cargas_em_aberto",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "cargas": 0}

    if limpar_antes:
        Cargas.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_cargas = 0
    objetos: list[Cargas] = []

    for arquivo in arquivos:
        linhas = list(_iterar_linhas_xls(arquivo))
        if not linhas:
            continue

        mapeamento_colunas = {
            "situacao": ["situacao", "status"],
            "ordem_de_carga_codigo": ["ordemdecarga", "ordemdecargacodigo", "codordemdecarga", "oc"],
            "data_inicio": ["datainicio", "datacriacao", "dataabertura"],
            "data_prevista_saida": [
                "dataprevistasaida",
                "datasaidaprevista",
                "dataprevisaosaida",
                "dataprevistaparasaida",
            ],
            "data_chegada": ["datachegada", "dtchegada"],
            "data_finalizacao": ["datafinalizacao", "dataencerramento", "dtfinalizacao"],
            "nome_motorista": [
                "nomemotorista",
                "motorista",
                "nomeparceiromotoristadoveiculo",
                "nomeparceiromotorista",
            ],
            "nome_fantasia_empresa": ["nomefantasiaempresa", "nomefantasia", "empresa", "cliente"],
            "regiao_codigo": ["codigoregiao", "codregiao", "regiao"],
            "regiao_nome": ["nomeregiao", "descricaoregiao", "regiaonome", "nome"],
            "prazo_maximo_dias": ["prazomaximodias", "prazomaximo", "prazodias"],
        }

        indices = _detectar_indices_colunas(
            linhas[:25],
            mapeamento_colunas,
            obrigatorias=["ordem_de_carga_codigo"],
        )
        if indices is None:
            continue

        for linha in linhas:
            if not any(_normalizar_texto(v) for v in linha):
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            registro = {
                chave: _valor_por_indice(chave)
                for chave in mapeamento_colunas.keys()
            }

            codigo = _normalizar_codigo(_valor_por_indice("ordem_de_carga_codigo"))
            if not codigo:
                continue

            if codigo.lower() in {"ordemdecarga", "ordem de carga"}:
                continue

            primeira_celula = _normalizar_texto(linha[0]) if linha else ""
            primeira_celula_token = _normalizar_nome_coluna(primeira_celula)
            if primeira_celula_token.startswith("emissao") or primeira_celula_token.startswith("totalderegistros"):
                continue

            data_inicio = _excel_date(registro["data_inicio"]) or datetime.today().date()
            data_prevista_saida = _excel_date(registro["data_prevista_saida"]) or data_inicio
            data_chegada = _excel_date(registro["data_chegada"])
            data_finalizacao = _excel_date(registro["data_finalizacao"])

            regiao = _resolver_regiao(
                empresa,
                registro["regiao_codigo"],
                _primeiro_valor_do_registro(
                    registro,
                    ["regiao_nome"],
                ),
            )

            objetos.append(
                Cargas(
                    empresa=empresa,
                    situacao=_normalizar_texto(registro["situacao"]) or "Em Aberto",
                    ordem_de_carga_codigo=codigo,
                    data_inicio=data_inicio,
                    data_prevista_saida=data_prevista_saida,
                    data_chegada=data_chegada,
                    data_finalizacao=data_finalizacao,
                    nome_motorista=_normalizar_texto(registro["nome_motorista"]),
                    nome_fantasia_empresa=_normalizar_texto(registro["nome_fantasia_empresa"]) or "-",
                    regiao=regiao,
                    prazo_maximo_dias=(
                        10
                        if _normalizar_texto(registro["prazo_maximo_dias"]) == ""
                        else _to_int(registro["prazo_maximo_dias"])
                    ),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Cargas.objects.bulk_create(objetos, batch_size=1000)
                total_cargas += len(objetos)
                objetos = []

    if objetos:
        Cargas.objects.bulk_create(objetos, batch_size=1000)
        total_cargas += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "cargas": total_cargas,
    }


@transaction.atomic
def importar_producao_do_diretorio(
    empresa,
    diretorio: str = "importacoes/operacional/producao",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "producoes": 0, "produtos": 0}

    if limpar_antes:
        Producao.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_producoes = 0
    produtos_codigos = set()
    objetos: list[Producao] = []

    mapeamento_colunas = {
        "numero_operacao": ["numerooperacao", "noperacao", "numoperacao", "operacao", "nroop", "nop"],
        "situacao": ["situacao", "status"],
        "codigo_produto": ["codproduto", "codigoproduto", "codigo", "codigodoproduto"],
        "descricao_produto": ["descricaoproduto", "descricaodoproduto", "descricao", "produto", "descproduto"],
        "tamanho_lote": ["tamanholote", "tamanhoproduto", "tamanho", "tamlote"],
        "numero_lote": ["numerolote", "lote", "numerodolote", "nrolote"],
        "data_hora_entrada_atividade": [
            "dataehoraentradaatividade",
            "datahoraentradaatividade",
            "dtentradaatividade",
            "entradaatividade",
            "dhentradaatividade",
        ],
        "data_hora_aceite_atividade": [
            "dataehoraaceiteatividade",
            "datahoraaceiteatividade",
            "dtaceiteatividade",
            "aceiteatividade",
            "dhaceiteatividade",
        ],
        "data_hora_inicio_atividade": [
            "dataehorainicioatividade",
            "datahorainicioatividade",
            "dtinicioatividade",
            "inicioatividade",
            "dhinicioatividade",
        ],
        "data_hora_fim_atividade": [
            "dataehorafimatividade",
            "datahorafimatividade",
            "dtfimatividade",
            "fimatividade",
            "dhfimatividade",
        ],
        "kg": ["kg", "peso", "pesoemkg"],
        "producao_por_dia": ["producaopordiafd", "producaopordia", "fd", "producaopordiafd"],
        "kg_por_lote": ["kgporlote", "kglote", "kgdolote"],
    }

    for arquivo in arquivos:
        linhas = list(_iterar_linhas_xls(arquivo))
        if not linhas:
            continue

        indices = _detectar_indices_colunas(
            linhas[:25],
            mapeamento_colunas,
            obrigatorias=["numero_operacao", "codigo_produto"],
        )
        if indices is None:
            continue

        for linha in linhas:
            if not any(_normalizar_texto(v) for v in linha):
                continue

            def _valor_por_indice(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            numero_operacao = _to_int(_valor_por_indice("numero_operacao"))
            if numero_operacao <= 0:
                continue

            codigo_produto = _normalizar_codigo(_valor_por_indice("codigo_produto"))
            descricao_produto = _normalizar_texto(_valor_por_indice("descricao_produto"))
            if not codigo_produto:
                continue

            produto = Produto.obter_ou_criar_por_codigo_descricao(
                empresa=empresa,
                codigo_produto=codigo_produto,
                descricao_produto=descricao_produto,
            )
            if not produto:
                continue
            produtos_codigos.add(produto.codigo_produto)

            tamanho_lote_decimal = _to_decimal(_valor_por_indice("tamanho_lote"))
            kg_valor = _to_decimal(_valor_por_indice("kg"))
            if kg_valor <= 0:
                kg_valor = _extrair_kg_da_descricao_produto(descricao_produto)

            producao_por_dia_valor = _to_decimal(_valor_por_indice("producao_por_dia"))
            if producao_por_dia_valor <= 0 and kg_valor > 0:
                producao_por_dia_valor = kg_valor

            kg_por_lote_valor = _to_decimal(_valor_por_indice("kg_por_lote"))
            if kg_por_lote_valor <= 0 and kg_valor > 0 and tamanho_lote_decimal > 0:
                kg_por_lote_valor = tamanho_lote_decimal / kg_valor

            objetos.append(
                Producao(
                    empresa=empresa,
                    data_origem=arquivo.name,
                    numero_operacao=numero_operacao,
                    situacao=_normalizar_texto(_valor_por_indice("situacao")),
                    produto=produto,
                    tamanho_lote=_normalizar_texto(_valor_por_indice("tamanho_lote")),
                    numero_lote=_normalizar_texto(_valor_por_indice("numero_lote")),
                    data_hora_entrada_atividade=_as_aware_datetime(
                        _excel_datetime(_valor_por_indice("data_hora_entrada_atividade"))
                    ),
                    data_hora_aceite_atividade=_as_aware_datetime(
                        _excel_datetime(_valor_por_indice("data_hora_aceite_atividade"))
                    ),
                    data_hora_inicio_atividade=_as_aware_datetime(
                        _excel_datetime(_valor_por_indice("data_hora_inicio_atividade"))
                    ),
                    data_hora_fim_atividade=_as_aware_datetime(
                        _excel_datetime(_valor_por_indice("data_hora_fim_atividade"))
                    ),
                    kg=kg_valor,
                    producao_por_dia=producao_por_dia_valor,
                    kg_por_lote=kg_por_lote_valor,
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Producao.objects.bulk_create(objetos, batch_size=1000)
                total_producoes += len(objetos)
                objetos = []

    if objetos:
        Producao.objects.bulk_create(objetos, batch_size=1000)
        total_producoes += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "producoes": total_producoes,
        "produtos": len(produtos_codigos),
    }
