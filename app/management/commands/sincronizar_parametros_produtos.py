from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import Empresa, Produto


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"a": NS_MAIN}


def _normalizar_chave(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return (
        texto
        .strip()
        .lower()
        .replace(" ", "")
        .replace(".", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )


def _to_decimal(valor) -> Decimal:
    texto = str(valor or "").strip()
    if not texto or texto.upper() in {"#VALUE!", "NONE"}:
        return Decimal("0")
    texto = texto.replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _ler_planilha_xlsx(caminho: Path) -> list[list[str]]:
    with zipfile.ZipFile(caminho) as arquivo_zip:
        workbook = ET.fromstring(arquivo_zip.read("xl/workbook.xml"))
        sheets = workbook.find("a:sheets", NS)
        if sheets is None or len(sheets) == 0:
            return []

        rels = ET.fromstring(arquivo_zip.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        primeiro = sheets[0]
        rid = primeiro.attrib.get(f"{{{NS_REL}}}id")
        if not rid or rid not in relmap:
            return []
        target = relmap[rid]
        if not target.startswith("xl/"):
            target = f"xl/{target}"

        shared = []
        if "xl/sharedStrings.xml" in arquivo_zip.namelist():
            sst = ET.fromstring(arquivo_zip.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", NS):
                textos = [t.text or "" for t in si.findall(".//a:t", NS)]
                shared.append("".join(textos))

        ws = ET.fromstring(arquivo_zip.read(target))
        linhas = []
        for row in ws.findall(".//a:sheetData/a:row", NS):
            valores = []
            for cell in row.findall("a:c", NS):
                tipo = cell.attrib.get("t")
                v = cell.find("a:v", NS)
                if v is None:
                    valores.append("")
                    continue
                bruto = v.text or ""
                if tipo == "s":
                    idx = int(bruto) if bruto.isdigit() else -1
                    valores.append(shared[idx] if 0 <= idx < len(shared) else "")
                else:
                    valores.append(bruto)
            linhas.append(valores)
        return linhas


class Command(BaseCommand):
    help = "Sincroniza parametros de produtos a partir de um XLSX."

    def add_arguments(self, parser):
        parser.add_argument("--xlsx", required=True, help="Caminho completo do arquivo XLSX.")
        parser.add_argument("--empresa-id", type=int, default=None, help="Empresa alvo (opcional).")

    @transaction.atomic
    def handle(self, *args, **options):
        caminho = Path(options["xlsx"]).expanduser()
        if not caminho.exists():
            raise CommandError(f"Arquivo nao encontrado: {caminho}")

        linhas = _ler_planilha_xlsx(caminho)
        if len(linhas) < 2:
            raise CommandError("Planilha sem dados suficientes.")

        header = linhas[0]
        idx = {_normalizar_chave(col): i for i, col in enumerate(header)}

        def _col(chave):
            i = idx.get(chave)
            if i is None:
                return None
            return i

        colunas = {
            "codigo_produto": _col("codigo"),
            "status": _col("status"),
            "descricao_produto": _col("produto"),
            "kg": _col("kg"),
            "remuneracao_por_fardo": _col("remuneracaoporfardo"),
            "ppm": _col("ppm"),
            "peso_kg": _col("pesokg"),
            "pacote_por_fardo": _col("pacoteporfardo"),
            "turno": _col("turno"),
            "horas": _col("horas"),
            "setup": _col("setup"),
            "horas_uteis": _col("horasuteis"),
            "empacotadeiras": _col("empacotadeiras"),
            "producao_por_dia_fd": _col("producaopordiafd"),
            "estoque_minimo_pacote": _col("estoqueminimopacote"),
        }

        if colunas["codigo_produto"] is None:
            raise CommandError("Coluna 'Codigo' nao encontrada na planilha.")

        registros = []
        for row in linhas[1:]:
            def _valor(chave):
                i = colunas[chave]
                if i is None or i >= len(row):
                    return ""
                return row[i]

            codigo = str(_valor("codigo_produto") or "").strip()
            if not codigo:
                continue

            registros.append(
                {
                    "codigo_produto": codigo,
                    "status": str(_valor("status") or "Ativo").strip() or "Ativo",
                    "descricao_produto": str(_valor("descricao_produto") or "").strip(),
                    "kg": _to_decimal(_valor("kg")),
                    "remuneracao_por_fardo": _to_decimal(_valor("remuneracao_por_fardo")),
                    "ppm": _to_decimal(_valor("ppm")),
                    "peso_kg": _to_decimal(_valor("peso_kg")),
                    "pacote_por_fardo": _to_decimal(_valor("pacote_por_fardo")),
                    "turno": _to_decimal(_valor("turno")),
                    "horas": _to_decimal(_valor("horas")),
                    "setup": _to_decimal(_valor("setup")),
                    "empacotadeiras": _to_decimal(_valor("empacotadeiras")),
                    "estoque_minimo_pacote": _to_decimal(_valor("estoque_minimo_pacote")),
                }
            )

        for reg in registros:
            horas_uteis = reg["horas"] - reg["setup"]
            if horas_uteis < 0:
                horas_uteis = Decimal("0")
            reg["horas_uteis"] = horas_uteis

            producao_por_dia_fd = Decimal("0")
            if (
                reg["ppm"] > 0
                and reg["pacote_por_fardo"] > 0
                and reg["empacotadeiras"] > 0
                and horas_uteis > 0
            ):
                producao_por_dia_fd = (
                    (reg["ppm"] / reg["pacote_por_fardo"])
                    * Decimal("60")
                    * horas_uteis
                    * reg["empacotadeiras"]
                )
            reg["producao_por_dia_fd"] = producao_por_dia_fd

        empresas_qs = Empresa.objects.all()
        if options["empresa_id"]:
            empresas_qs = empresas_qs.filter(id=options["empresa_id"])
        empresas = list(empresas_qs)
        if not empresas:
            raise CommandError("Nenhuma empresa encontrada para sincronizar.")

        total_atualizados = 0
        total_criados = 0

        for empresa in empresas:
            produtos_map = {
                p.codigo_produto: p
                for p in Produto.objects.filter(empresa=empresa)
            }

            for reg in registros:
                existente = produtos_map.get(reg["codigo_produto"])
                if existente:
                    existente.atualizar_produto(**reg)
                    total_atualizados += 1
                else:
                    Produto.criar_produto(empresa=empresa, **reg)
                    total_criados += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"Sincronizacao concluida. Linhas validas: {len(registros)} | "
                    f"Produtos atualizados: {total_atualizados} | Produtos criados: {total_criados}."
                )
            )
        )
