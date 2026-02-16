from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import unicodedata

from django.db import transaction

from ..models import Cargas, Regiao

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


def _detectar_indices_colunas(linhas, mapeamento_colunas):
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
    if melhor_indices and melhor_indices.get("ordem_de_carga_codigo") is None:
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

        indices = _detectar_indices_colunas(linhas[:25], mapeamento_colunas)
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
