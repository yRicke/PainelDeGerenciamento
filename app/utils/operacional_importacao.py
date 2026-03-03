from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

from django.db import transaction
from django.utils import timezone

from ..models import Cargas, Cidade, Estoque, Frete, Producao, Produto, Regiao, UnidadeFederativa

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
    if not codigo and not nome:
        return None
    if not codigo:
        return Regiao.objects.filter(empresa=empresa, nome=nome).first()

    defaults = {"empresa": empresa, "nome": nome or codigo}
    regiao, created = Regiao.objects.get_or_create(codigo=codigo, defaults=defaults)
    if created or not nome or regiao.nome == nome:
        return regiao

    regiao.nome = nome
    regiao.save(update_fields=["nome"])
    return regiao


def _resolver_cidade(empresa, codigo_cidade: str, nome_cidade: str):
    codigo = _normalizar_codigo(codigo_cidade)
    nome = _normalizar_texto(nome_cidade)
    if not codigo and not nome:
        return None
    if not codigo:
        return Cidade.objects.filter(empresa=empresa, nome=nome).first()

    defaults = {"empresa": empresa, "nome": nome or codigo}
    cidade, created = Cidade.objects.get_or_create(codigo=codigo, defaults=defaults)
    if created or not nome or cidade.nome == nome:
        return cidade

    cidade.nome = nome
    cidade.save(update_fields=["nome"])
    return cidade


def _resolver_unidade_federativa(empresa, codigo_uf: str, sigla_uf: str):
    codigo = _normalizar_codigo(codigo_uf)
    sigla = _normalizar_texto(sigla_uf).upper()
    if not codigo:
        return None

    defaults = {"empresa": empresa, "sigla": sigla or codigo}
    unidade, created = UnidadeFederativa.objects.get_or_create(codigo=codigo, defaults=defaults)
    if created or not sigla or unidade.sigla == sigla:
        return unidade

    unidade.sigla = sigla
    unidade.save(update_fields=["sigla"])
    return unidade


def _to_decimal_frete_comercial(valor) -> Decimal:
    texto = _normalizar_texto(valor)
    if not texto:
        return Decimal("0")

    match = re.search(r"R\$\s*([0-9\.\,]+)", texto, flags=re.IGNORECASE)
    if match:
        return _to_decimal(match.group(1))
    return _to_decimal(texto)


def _detectar_indices_colunas_frete(linhas):
    melhor = None
    melhor_score = -1

    for linha in linhas:
        if not any(_normalizar_texto(v) for v in linha):
            continue
        tokens = [_normalizar_nome_coluna(v) for v in linha]

        idx_cidade_codigo = next((i for i, t in enumerate(tokens) if t == "codcidade"), None)
        idx_uf_codigo = next((i for i, t in enumerate(tokens) if t == "coduf"), None)
        idx_regiao_codigo = next((i for i, t in enumerate(tokens) if t == "regiao"), None)

        idx_cidade_nome = None
        idx_regiao_nome = None
        if idx_cidade_codigo is not None:
            idx_cidade_nome = next(
                (
                    i
                    for i, t in enumerate(tokens)
                    if t == "nome" and i > idx_cidade_codigo
                ),
                None,
            )
        if idx_regiao_codigo is not None:
            idx_regiao_nome = next(
                (
                    i
                    for i, t in enumerate(tokens)
                    if t == "nome" and i > idx_regiao_codigo
                ),
                None,
            )

        mapa = {
            "cidade_codigo": idx_cidade_codigo,
            "cidade_nome": idx_cidade_nome,
            "sigla_uf": next((i for i, t in enumerate(tokens) if t == "sigla"), None),
            "codigo_uf": idx_uf_codigo,
            "valor_frete_comercial": next((i for i, t in enumerate(tokens) if t == "vlrfretecomercial"), None),
            "regiao_codigo": idx_regiao_codigo,
            "regiao_nome": idx_regiao_nome,
            "data_hora_alteracao": next((i for i, t in enumerate(tokens) if t == "datadealteracao"), None),
            "valor_frete_minimo": next((i for i, t in enumerate(tokens) if t == "valordefreteminimo"), None),
            "valor_frete_tonelada": next((i for i, t in enumerate(tokens) if t == "valordefreteportonelada"), None),
            "tipo_frete": next((i for i, t in enumerate(tokens) if t == "tipodefrete"), None),
            "valor_frete_por_km": next((i for i, t in enumerate(tokens) if t == "valordefreteporkm"), None),
            "valor_taxa_entrada": next((i for i, t in enumerate(tokens) if t == "valortaxadeentrada"), None),
            "venda_minima": next((i for i, t in enumerate(tokens) if t == "vendaminima"), None),
        }
        score = sum(1 for value in mapa.values() if value is not None)
        if score > melhor_score:
            melhor_score = score
            melhor = mapa

    if not melhor:
        return None
    if melhor.get("cidade_codigo") is None or melhor.get("codigo_uf") is None or melhor.get("regiao_codigo") is None:
        return None
    return melhor


def _detectar_tipo_layout_estoque(linhas):
    for linha in linhas:
        tokens = {_normalizar_nome_coluna(valor) for valor in linha if _normalizar_texto(valor)}
        # Layout "posicao" varia entre arquivos: alguns nao trazem DESCRPROD.
        # Mantemos a deteccao por colunas estruturais obrigatorias.
        if {"qtdestoque", "dtcontagem", "codempresa", "codlocal", "codproduto"}.issubset(tokens):
            return "posicao"
        if {"empresa", "local", "descricaolocal", "codproduto", "reservado", "estoque"}.issubset(tokens):
            return "reservado"
    return ""


def _extrair_data_do_nome_arquivo(nome_arquivo: str):
    texto = _normalizar_texto(nome_arquivo)
    match = re.search(r"(\d{2})[.\-_/](\d{2})[.\-_/](\d{2,4})", texto)
    if not match:
        return None
    dia, mes, ano = match.groups()
    if len(ano) == 2:
        ano = f"20{ano}"
    try:
        return datetime.strptime(f"{dia}/{mes}/{ano}", "%d/%m/%Y").date()
    except ValueError:
        return None


def _detectar_indices_colunas_exatas(linhas, mapeamento_colunas, obrigatorias=None):
    melhor = None
    melhor_score = -1

    for linha in linhas:
        if not any(_normalizar_texto(v) for v in linha):
            continue
        normalizadas = [_normalizar_nome_coluna(v) for v in linha]
        idx_map = {}
        for chave, alias in mapeamento_colunas.items():
            idx_map[chave] = next((i for i, token in enumerate(normalizadas) if token == alias), None)
        score = sum(1 for v in idx_map.values() if v is not None)
        if score > melhor_score:
            melhor_score = score
            melhor = idx_map

    if not melhor:
        return None
    if obrigatorias:
        for campo in obrigatorias:
            if melhor.get(campo) is None:
                return None
    return melhor


def _pacote_por_fardo_por_descricao(descricao: str) -> Decimal:
    texto = _normalizar_texto(descricao).upper()
    match = re.search(r"(\d+)\s*[Xx]", texto)
    if match:
        return Decimal(match.group(1))
    return Decimal("1")


def _decimal_zero():
    return Decimal("0")


def _valor_por_indice(linha, indices, chave):
    idx = indices.get(chave)
    if idx is None or idx >= len(linha):
        return ""
    return linha[idx]


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
def importar_estoque_do_diretorio(
    empresa,
    diretorio: str = "importacoes/operacional/estoque_pcp",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    pasta_subscritos = base / "subscritos"
    arquivos = sorted(
        [
            arquivo
            for arquivo in base.rglob("*.xls")
            if arquivo.is_file() and pasta_subscritos not in arquivo.parents
        ]
    )
    if not arquivos:
        return {
            "arquivos": 0,
            "arquivos_posicao": 0,
            "arquivos_reservado": 0,
            "linhas": 0,
            "estoques": 0,
            "avisos": [],
        }

    posicoes = {}
    reservados = {}
    total_linhas = 0
    total_arquivos_posicao = 0
    total_arquivos_reservado = 0
    avisos: list[str] = []

    for arquivo in arquivos:
        linhas = list(_iterar_linhas_xls(arquivo))
        if not linhas:
            continue

        tipo_layout = _detectar_tipo_layout_estoque(linhas[:10])
        data_nome_arquivo = _extrair_data_do_nome_arquivo(arquivo.name) or timezone.localdate()

        if tipo_layout == "posicao":
            total_arquivos_posicao += 1
            mapeamento_posicao = {
                "descricao_produto": "descrprod",
                "qtd_estoque": "qtdestoque",
                "data_contagem": "dtcontagem",
                "codigo_empresa": "codempresa",
                "codigo_produto": "codproduto",
                "codigo_volume": "codvoume",
                "codigo_local": "codlocal",
                "custo_total": "custototal",
            }
            obrigatorias_posicao = {"codigo_produto", "codigo_empresa", "codigo_local", "qtd_estoque"}
            indices = _detectar_indices_colunas_exatas(
                linhas[:20],
                mapeamento_posicao,
                obrigatorias=list(obrigatorias_posicao),
            )
            if not indices:
                _registrar_aviso_colunas(
                    avisos,
                    nome_arquivo=arquivo.name,
                    faltantes=list(mapeamento_posicao.keys()),
                    obrigatorias=obrigatorias_posicao,
                )
                continue
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=_colunas_nao_identificadas(indices, mapeamento_posicao.keys()),
                obrigatorias=obrigatorias_posicao,
            )

            for linha in linhas:
                codigo_produto = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_produto"))
                if not codigo_produto or not codigo_produto.isdigit():
                    continue

                codigo_empresa = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_empresa"))
                codigo_local = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_local"))
                if not codigo_empresa or not codigo_local:
                    continue

                descricao_produto = _normalizar_texto(_valor_por_indice(linha, indices, "descricao_produto"))
                qtd_estoque = _to_decimal(_valor_por_indice(linha, indices, "qtd_estoque"))
                custo_total = _to_decimal(_valor_por_indice(linha, indices, "custo_total"))
                data_contagem = _excel_date(_valor_por_indice(linha, indices, "data_contagem")) or data_nome_arquivo
                codigo_volume = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_volume"))
                chave = (data_contagem, codigo_empresa, codigo_local, codigo_produto)

                atual = posicoes.get(chave)
                if not atual:
                    posicoes[chave] = {
                        "descricao_produto": descricao_produto,
                        "qtd_estoque": qtd_estoque,
                        "custo_total": custo_total,
                        "data_contagem": data_contagem,
                        "codigo_volume": codigo_volume,
                        "nome_origem": data_nome_arquivo,
                    }
                else:
                    atual["qtd_estoque"] += qtd_estoque
                    atual["custo_total"] += custo_total
                    if not atual["descricao_produto"] and descricao_produto:
                        atual["descricao_produto"] = descricao_produto
                    if not atual["codigo_volume"] and codigo_volume:
                        atual["codigo_volume"] = codigo_volume
                total_linhas += 1

        elif tipo_layout == "reservado":
            total_arquivos_reservado += 1
            mapeamento_reservado = {
                "codigo_empresa": "empresa",
                "codigo_local": "local",
                "codigo_produto": "codproduto",
                "descricao_produto": "descricaoproduto",
                "reservado": "reservado",
                "estoque": "estoque",
            }
            obrigatorias_reservado = {"codigo_produto", "codigo_empresa", "reservado"}
            indices = _detectar_indices_colunas_exatas(
                linhas[:20],
                mapeamento_reservado,
                obrigatorias=list(obrigatorias_reservado),
            )
            if not indices:
                _registrar_aviso_colunas(
                    avisos,
                    nome_arquivo=arquivo.name,
                    faltantes=list(mapeamento_reservado.keys()),
                    obrigatorias=obrigatorias_reservado,
                )
                continue
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=_colunas_nao_identificadas(indices, mapeamento_reservado.keys()),
                obrigatorias=obrigatorias_reservado,
            )

            for linha in linhas:
                codigo_produto = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_produto"))
                if not codigo_produto or not codigo_produto.isdigit():
                    continue

                codigo_empresa = _normalizar_codigo(_valor_por_indice(linha, indices, "codigo_empresa"))
                if not codigo_empresa:
                    continue

                # No legado, reservado e agregado por data/empresa/produto (sem local).
                chave = (data_nome_arquivo, codigo_empresa, codigo_produto)
                descricao_produto = _normalizar_texto(_valor_por_indice(linha, indices, "descricao_produto"))
                reservado = _to_decimal(_valor_por_indice(linha, indices, "reservado"))
                estoque = _to_decimal(_valor_por_indice(linha, indices, "estoque"))

                atual = reservados.get(chave)
                if not atual:
                    reservados[chave] = {
                        "descricao_produto": descricao_produto,
                        "reservado": reservado,
                        "estoque": estoque,
                        "nome_origem": data_nome_arquivo,
                    }
                else:
                    atual["reservado"] += reservado
                    atual["estoque"] += estoque
                    if not atual["descricao_produto"] and descricao_produto:
                        atual["descricao_produto"] = descricao_produto
                total_linhas += 1
        else:
            avisos.append(
                f"Arquivo '{arquivo.name}': nao foi possivel identificar o layout esperado (posicao/reservado)."
            )

    if total_arquivos_posicao == 0 or total_arquivos_reservado == 0:
        return {
            "arquivos": len(arquivos),
            "arquivos_posicao": total_arquivos_posicao,
            "arquivos_reservado": total_arquivos_reservado,
            "linhas": total_linhas,
            "estoques": 0,
            "avisos": avisos,
        }

    if limpar_antes:
        Estoque.objects.filter(empresa=empresa).delete()

    objetos = []
    for data_contagem, codigo_empresa, codigo_local, codigo_produto in posicoes.keys():
        posicao = posicoes.get((data_contagem, codigo_empresa, codigo_local, codigo_produto), {})
        reservado_item = reservados.get((data_contagem, codigo_empresa, codigo_produto), {})

        descricao_produto = (
            posicao.get("descricao_produto")
            or reservado_item.get("descricao_produto")
            or ""
        )
        produto = Produto.obter_ou_criar_por_codigo_descricao(
            empresa=empresa,
            codigo_produto=codigo_produto,
            descricao_produto=descricao_produto,
        )

        qtd_estoque = posicao.get("qtd_estoque", _decimal_zero())
        reservado = reservado_item.get("reservado", _decimal_zero())
        custo_total = posicao.get("custo_total", _decimal_zero())
        nome_origem = posicao.get("nome_origem") or reservado_item.get("nome_origem") or timezone.localdate()
        data_contagem = posicao.get("data_contagem") or nome_origem
        codigo_volume = posicao.get("codigo_volume", "")

        pacote_por_fardo = _to_decimal(produto.pacote_por_fardo if produto else 0)
        if pacote_por_fardo < 0:
            pacote_por_fardo = _decimal_zero()
        giro_mensal = _decimal_zero()
        lead_time_fornecimento = _decimal_zero()

        estoque_minimo_parametro = _to_decimal(produto.estoque_minimo_pacote if produto else 0)
        if estoque_minimo_parametro < 0:
            estoque_minimo_parametro = _decimal_zero()
        producao_por_dia_fd = _to_decimal(produto.producao_por_dia_fd if produto else 0)
        if producao_por_dia_fd < 0:
            producao_por_dia_fd = _decimal_zero()

        produto_tem_parametro = bool(
            produto
            and (
                pacote_por_fardo > 0
                or producao_por_dia_fd > 0
                or estoque_minimo_parametro > 0
            )
        )
        status = _normalizar_texto(produto.status) if produto_tem_parametro else ""

        # Legado: quando nao encontra parametro de produto, usa 12000.
        estoque_minimo = (
            estoque_minimo_parametro
            if produto_tem_parametro
            else Decimal("12000")
        )
        if estoque_minimo < 0:
            estoque_minimo = _decimal_zero()

        sub_total_est_pen = qtd_estoque - reservado
        total_pcp_pacote = sub_total_est_pen - estoque_minimo
        total_pcp_fardo = (
            (total_pcp_pacote / pacote_por_fardo)
            if pacote_por_fardo > 0
            else _decimal_zero()
        )
        dia_de_producao = (
            (total_pcp_fardo / producao_por_dia_fd)
            if producao_por_dia_fd > 0
            else _decimal_zero()
        )

        objetos.append(
            Estoque(
                empresa=empresa,
                nome_origem=nome_origem,
                data_contagem=data_contagem,
                status=status or "Pendente",
                codigo_empresa=codigo_empresa,
                produto=produto,
                qtd_estoque=qtd_estoque,
                giro_mensal=giro_mensal,
                lead_time_fornecimento=lead_time_fornecimento,
                codigo_volume=codigo_volume,
                custo_total=custo_total,
                reservado=reservado,
                pacote_por_fardo=pacote_por_fardo,
                sub_total_est_pen=sub_total_est_pen,
                estoque_minimo=estoque_minimo,
                producao_por_dia_fd=producao_por_dia_fd,
                total_pcp_pacote=total_pcp_pacote,
                total_pcp_fardo=total_pcp_fardo,
                dia_de_producao=dia_de_producao,
                codigo_local=codigo_local,
            )
        )

    total_estoques = 0
    for i in range(0, len(objetos), 1000):
        lote = objetos[i : i + 1000]
        Estoque.objects.bulk_create(
            lote,
            batch_size=1000,
            update_conflicts=True,
            update_fields=[
                "status",
                "qtd_estoque",
                "giro_mensal",
                "lead_time_fornecimento",
                "codigo_volume",
                "custo_total",
                "reservado",
                "pacote_por_fardo",
                "sub_total_est_pen",
                "estoque_minimo",
                "producao_por_dia_fd",
                "total_pcp_pacote",
                "total_pcp_fardo",
                "dia_de_producao",
            ],
            unique_fields=["empresa", "nome_origem", "data_contagem", "codigo_empresa", "codigo_local", "produto"],
        )
        total_estoques += len(lote)

    return {
        "arquivos": len(arquivos),
        "arquivos_posicao": total_arquivos_posicao,
        "arquivos_reservado": total_arquivos_reservado,
        "linhas": total_linhas,
        "estoques": total_estoques,
        "avisos": avisos,
    }


@transaction.atomic
def importar_fretes_do_diretorio(
    empresa,
    diretorio: str = "importacoes/operacional/tabela_de_fretes",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {
            "arquivos": 0,
            "linhas": 0,
            "fretes": 0,
            "cidades": 0,
            "regioes": 0,
            "unidades_federativas": 0,
            "avisos": [],
        }

    if limpar_antes:
        Frete.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_fretes = 0
    cidades_codigos = set()
    regioes_codigos = set()
    ufs_codigos = set()
    objetos: list[Frete] = []
    avisos: list[str] = []

    for arquivo in arquivos:
        linhas = list(_iterar_linhas_xls(arquivo))
        if not linhas:
            continue

        indices = _detectar_indices_colunas_frete(linhas[:30])
        if indices is None:
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=[
                    "cidade_codigo",
                    "cidade_nome",
                    "sigla_uf",
                    "codigo_uf",
                    "valor_frete_comercial",
                    "regiao_codigo",
                    "regiao_nome",
                    "data_hora_alteracao",
                    "valor_frete_minimo",
                    "valor_frete_tonelada",
                    "tipo_frete",
                    "valor_frete_por_km",
                    "valor_taxa_entrada",
                    "venda_minima",
                ],
                obrigatorias={"cidade_codigo", "codigo_uf", "regiao_codigo"},
            )
            continue
        _registrar_aviso_colunas(
            avisos,
            nome_arquivo=arquivo.name,
            faltantes=_colunas_nao_identificadas(
                indices,
                [
                    "cidade_codigo",
                    "cidade_nome",
                    "sigla_uf",
                    "codigo_uf",
                    "valor_frete_comercial",
                    "regiao_codigo",
                    "regiao_nome",
                    "data_hora_alteracao",
                    "valor_frete_minimo",
                    "valor_frete_tonelada",
                    "tipo_frete",
                    "valor_frete_por_km",
                    "valor_taxa_entrada",
                    "venda_minima",
                ],
            ),
            obrigatorias={"cidade_codigo", "codigo_uf", "regiao_codigo"},
        )

        for linha in linhas:
            if not any(_normalizar_texto(v) for v in linha):
                continue

            def _valor(chave):
                idx = indices.get(chave)
                if idx is None or idx >= len(linha):
                    return ""
                return linha[idx]

            primeira_celula_texto = _normalizar_texto(linha[0]) if linha else ""
            primeira_celula_token = _normalizar_nome_coluna(primeira_celula_texto)
            if (
                primeira_celula_token in {"cidade", "codcidade", "nomedacidade"}
                or primeira_celula_token.startswith("emissao")
                or primeira_celula_token.startswith("totalderegistros")
                or primeira_celula_token.startswith("usuario")
            ):
                continue

            cidade_codigo = _normalizar_codigo(_valor("cidade_codigo"))
            if not cidade_codigo or cidade_codigo.lower() in {"codcidade", "codigocidade"}:
                continue
            if not cidade_codigo.isdigit():
                continue

            cidade = _resolver_cidade(empresa, cidade_codigo, _valor("cidade_nome"))
            unidade_federativa = _resolver_unidade_federativa(empresa, _valor("codigo_uf"), _valor("sigla_uf"))
            regiao = _resolver_regiao(empresa, _valor("regiao_codigo"), _valor("regiao_nome"))
            if not cidade:
                continue

            cidades_codigos.add(cidade.codigo)
            if unidade_federativa:
                ufs_codigos.add(unidade_federativa.codigo)
            if regiao:
                regioes_codigos.add(regiao.codigo)

            objetos.append(
                Frete(
                    empresa=empresa,
                    cidade=cidade,
                    unidade_federativa=unidade_federativa,
                    regiao=regiao,
                    valor_frete_comercial=_to_decimal_frete_comercial(_valor("valor_frete_comercial")),
                    data_hora_alteracao=_as_aware_datetime(_excel_datetime(_valor("data_hora_alteracao"))),
                    valor_frete_minimo=_to_decimal(_valor("valor_frete_minimo")),
                    valor_frete_tonelada=_to_decimal(_valor("valor_frete_tonelada")),
                    tipo_frete=_normalizar_texto(_valor("tipo_frete")),
                    valor_frete_por_km=_to_decimal(_valor("valor_frete_por_km")),
                    valor_taxa_entrada=_to_decimal(_valor("valor_taxa_entrada")),
                    venda_minima=_to_decimal(_valor("venda_minima")),
                )
            )
            total_linhas += 1

            if len(objetos) >= 1000:
                Frete.objects.bulk_create(
                    objetos,
                    batch_size=1000,
                    update_conflicts=True,
                    update_fields=[
                        "unidade_federativa",
                        "regiao",
                        "valor_frete_comercial",
                        "data_hora_alteracao",
                        "valor_frete_minimo",
                        "valor_frete_tonelada",
                        "tipo_frete",
                        "valor_frete_por_km",
                        "valor_taxa_entrada",
                        "venda_minima",
                    ],
                    unique_fields=["empresa", "cidade"],
                )
                total_fretes += len(objetos)
                objetos = []

    if objetos:
        Frete.objects.bulk_create(
            objetos,
            batch_size=1000,
            update_conflicts=True,
            update_fields=[
                "unidade_federativa",
                "regiao",
                "valor_frete_comercial",
                "data_hora_alteracao",
                "valor_frete_minimo",
                "valor_frete_tonelada",
                "tipo_frete",
                "valor_frete_por_km",
                "valor_taxa_entrada",
                "venda_minima",
            ],
            unique_fields=["empresa", "cidade"],
        )
        total_fretes += len(objetos)

    return {
        "arquivos": len(arquivos),
        "linhas": total_linhas,
        "fretes": total_fretes,
        "cidades": len(cidades_codigos),
        "regioes": len(regioes_codigos),
        "unidades_federativas": len(ufs_codigos),
        "avisos": avisos,
    }


@transaction.atomic
def importar_cargas_do_diretorio(
    empresa,
    diretorio: str = "importacoes/operacional/cargas_em_aberto",
    limpar_antes: bool = True,
):
    base = Path(diretorio)
    arquivos = sorted(base.glob("*.xls"))
    if not arquivos:
        return {"arquivos": 0, "linhas": 0, "cargas": 0, "avisos": []}

    if limpar_antes:
        Cargas.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_cargas = 0
    objetos: list[Cargas] = []
    avisos: list[str] = []

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
            "empresa_codigo": ["empresa", "codempresa", "codigoempresa"],
            "nome_fantasia_empresa": ["nomefantasiaempresa", "nomefantasia", "cliente"],
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
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=list(mapeamento_colunas.keys()),
                obrigatorias={"ordem_de_carga_codigo"},
            )
            continue
        _registrar_aviso_colunas(
            avisos,
            nome_arquivo=arquivo.name,
            faltantes=_colunas_nao_identificadas(indices, mapeamento_colunas.keys()),
            obrigatorias={"ordem_de_carga_codigo"},
        )

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

            empresa_codigo = _normalizar_codigo(registro["empresa_codigo"])
            nome_fantasia = _normalizar_texto(registro["nome_fantasia_empresa"])
            if empresa_codigo and nome_fantasia:
                nome_fantasia_empresa = f"{empresa_codigo} - {nome_fantasia}"
            else:
                nome_fantasia_empresa = nome_fantasia or empresa_codigo or "-"

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
                    nome_fantasia_empresa=nome_fantasia_empresa,
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
        "avisos": avisos,
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
        return {"arquivos": 0, "linhas": 0, "producoes": 0, "produtos": 0, "avisos": []}

    if limpar_antes:
        Producao.objects.filter(empresa=empresa).delete()

    total_linhas = 0
    total_producoes = 0
    produtos_codigos = set()
    objetos: list[Producao] = []
    avisos: list[str] = []

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
        "estoque_minimo_pacote": [
            "estoqueminimopacote",
            "estoqueminimo",
            "estminpacote",
            "estoqueminpacote",
        ],
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
            _registrar_aviso_colunas(
                avisos,
                nome_arquivo=arquivo.name,
                faltantes=list(mapeamento_colunas.keys()),
                obrigatorias={"numero_operacao", "codigo_produto"},
            )
            continue
        _registrar_aviso_colunas(
            avisos,
            nome_arquivo=arquivo.name,
            faltantes=_colunas_nao_identificadas(indices, mapeamento_colunas.keys()),
            obrigatorias={"numero_operacao", "codigo_produto"},
        )

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
            # Producao sempre deve refletir os parametros do cadastro de produtos,
            # inclusive quando o parametro estiver zerado.
            kg_valor = _to_decimal(produto.kg if produto else 0)
            if kg_valor < 0:
                kg_valor = _decimal_zero()

            producao_por_dia_valor = _to_decimal(produto.producao_por_dia_fd if produto else 0)
            if producao_por_dia_valor < 0:
                producao_por_dia_valor = _decimal_zero()

            kg_por_lote_valor = (
                (tamanho_lote_decimal / kg_valor)
                if (kg_valor > 0 and tamanho_lote_decimal > 0)
                else _decimal_zero()
            )

            estoque_minimo_pacote_valor = _to_decimal(produto.estoque_minimo_pacote if produto else 0)
            if estoque_minimo_pacote_valor < 0:
                estoque_minimo_pacote_valor = _decimal_zero()

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
                    estoque_minimo_pacote=estoque_minimo_pacote_valor,
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
        "avisos": avisos,
    }
