import csv
import io
import os
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings")
import django

django.setup()

from app.models import SaldoLimite

EMPRESA_ID = 3
ARQUIVO = "tmp_compare_saldos_clipboard.txt"


def normalize_text(value):
    text = str(value or "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def normalize_bank(value):
    return " ".join(str(value or "").strip().upper().split())


def parse_date_custom(value):
    text = str(value or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if not m:
        return None
    p1 = int(m.group(1))
    p2 = int(m.group(2))
    year = int(m.group(3))
    if year == 2026 and p1 in (2, 3):
        try:
            return date(year, p1, p2)
        except ValueError:
            return None
    try:
        return date(year, p2, p1)
    except ValueError:
        try:
            return date(year, p1, p2)
        except ValueError:
            return None


def parse_tipo(value):
    text = normalize_text(value).lower()
    mapping = {
        "saldo inicial": "saldo_inicial",
        "limite inicial": "limite_inicial",
        "saldo final": "saldo_final",
        "limite final": "limite_final",
        "antecipacao": "antecipacao",
    }
    return mapping.get(text, "")


def parse_valor(value):
    text = str(value or "").strip().replace("R$", "").replace(" ", "")
    if text in {"", "-", ".", ",", "R$-"}:
        val = Decimal("0")
    else:
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            val = Decimal(text)
        except (InvalidOperation, ValueError):
            val = Decimal("0")
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_codigo_titular(value):
    match = re.match(r"\s*(\d+)\s*-", str(value or ""))
    return int(match.group(1)) if match else 0

raw = open(ARQUIVO, "r", encoding="utf-8", errors="ignore").read()
reader = csv.reader(io.StringIO(raw), delimiter="\t")
fields = []
for row in reader:
    fields.extend(row)
fields = [f.strip() for f in fields]
while fields and not fields[0]:
    fields.pop(0)
while fields and not fields[-1]:
    fields.pop()

is_date = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
parsed_total = 0
expected = {}

idx = 0
while idx + 5 < len(fields):
    token = fields[idx]
    if not token or not is_date.match(token):
        idx += 1
        continue

    data_raw, titular_raw, banco_raw, conta_raw, tipo_raw, valor_raw = fields[idx:idx+6]
    idx += 6
    parsed_total += 1

    data = parse_date_custom(data_raw)
    codigo_titular = parse_codigo_titular(titular_raw)
    banco = normalize_bank(banco_raw)
    conta = re.sub(r"\D", "", str(conta_raw or ""))
    tipo = parse_tipo(tipo_raw)
    valor = parse_valor(valor_raw)

    if not data or not codigo_titular or not banco or not conta or not tipo:
        continue

    expected[(data.isoformat(), codigo_titular, banco, conta, tipo)] = valor

current = {}
for item in SaldoLimite.objects.filter(empresa_id=EMPRESA_ID).select_related("empresa_titular", "conta_bancaria"):
    key = (
        item.data.isoformat(),
        int(item.empresa_titular.codigo),
        normalize_bank(item.conta_bancaria.nome_banco),
        str(item.conta_bancaria.numero_conta),
        str(item.tipo_movimentacao),
    )
    current[key] = Decimal(item.valor_atual).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

expected_keys = set(expected.keys())
current_keys = set(current.keys())

missing = sorted(expected_keys - current_keys)
extra = sorted(current_keys - expected_keys)
value_diff = sorted(k for k in (expected_keys & current_keys) if expected[k] != current[k])

print("parsed_total", parsed_total)
print("expected_unique", len(expected))
print("current_unique", len(current))
print("missing", len(missing))
print("extra", len(extra))
print("value_diff", len(value_diff))
print("sample_missing", missing[:20])
print("sample_extra", extra[:20])
print("sample_value_diff", [(k, str(expected[k]), str(current[k])) for k in value_diff[:20]])
