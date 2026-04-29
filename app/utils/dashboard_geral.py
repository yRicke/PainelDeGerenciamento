import calendar
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from ..models import (
    Atividade,
    Cargas,
    Estoque,
    Faturamento,
    ParametroNegocios,
    Producao,
    Venda,
)
from ..services.administrativo import calcular_dashboard_tofu


NOME_PERMISSAO_DASHBOARD_GERAL = "Dashboard Geral"


def resolver_mes_dashboard_geral(valor):
    hoje = timezone.localdate()
    texto = str(valor or "").strip()
    if texto:
        partes = texto.split("-")
        if len(partes) == 2:
            try:
                ano = int(partes[0])
                mes = int(partes[1])
                if 1 <= mes <= 12:
                    inicio = date(ano, mes, 1)
                    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
                    return inicio, fim
            except (TypeError, ValueError):
                pass
    inicio = date(hoje.year, hoje.month, 1)
    fim = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    return inicio, fim


def texto_mes_referencia(data_inicio):
    return data_inicio.strftime("%Y-%m")


def _normalizar_texto(valor):
    texto = unicodedata.normalize("NFD", str(valor or "").strip().lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.split())


def _gerente_token(valor):
    token = _normalizar_texto(valor)
    if token in {"sem gerente", "<sem gerente>", "sem vendedor", "<sem vendedor>"}:
        return ""
    return token


def _gerente_eh_mp_ou_luciano(valor):
    token = _gerente_token(valor)
    if not token:
        return False
    return "luciano" in token or token in {"mp", "ger mp", "gerente mp"}


def _decimal(valor):
    return Decimal(valor or 0)


def _texto_moeda(valor):
    numero = _decimal(valor).quantize(Decimal("0.01"))
    prefixo = "R$ "
    if numero < 0:
        numero = abs(numero)
        prefixo = "-R$ "
    texto = f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{prefixo}{texto}"


def _texto_numero(valor, casas=2):
    numero = _decimal(valor)
    texto = f"{numero:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return texto


def _texto_percentual(valor):
    return f"{_texto_numero(valor, 2)}%"


def _valor_para_angulo(valor, maximo):
    referencia = _decimal(maximo)
    if referencia <= 0:
        return -90.0
    proporcao = max(Decimal("0"), min(Decimal("1"), _decimal(valor) / referencia))
    return float((proporcao * Decimal("180")) - Decimal("90"))


def _somar_decimal(qs, campo, *, max_digits=18, decimal_places=2):
    return _decimal(
        qs.aggregate(
            total=Coalesce(
                Sum(campo),
                Value(Decimal("0"), output_field=DecimalField(max_digits=max_digits, decimal_places=decimal_places)),
            )
        ).get("total")
    )


def _dias_uteis(inicio, fim):
    if not inicio or not fim or inicio > fim:
        return 0
    cursor = inicio
    total = 0
    while cursor <= fim:
        if cursor.weekday() < 5:
            total += 1
        cursor += timedelta(days=1)
    return total


def _dias_uteis_restantes_mes(inicio_mes, fim_mes):
    hoje = timezone.localdate()
    if fim_mes < hoje:
        return 0
    inicio = max(inicio_mes, hoje)
    return _dias_uteis(inicio, fim_mes)


def _parametro_faturamento(empresa):
    parametros = ParametroNegocios.objects.filter(empresa=empresa).order_by("-id")
    return (
        parametros.filter(direcao__icontains="faturamento", compromisso_unidade="valor").first()
        or parametros.filter(direcao__icontains="faturamento").first()
        or parametros.filter(compromisso_unidade="valor").first()
        or parametros.first()
    )


def _consolidar_notas_faturamento(linhas):
    notas = {}
    for item in linhas:
        chave = f"nota:{item.numero_nota}" if item.numero_nota else f"row:{item.id}"
        valor_nota = _decimal(item.valor_nota)
        valor_unico = _decimal(item.valor_nota_unico)
        atual = notas.get(chave)
        if not atual:
            notas[chave] = {
                "valor_nota": valor_nota,
                "valor_unico": valor_unico,
                "tipo_venda": item.tipo_venda or "",
            }
            continue
        if not atual["valor_nota"] and valor_nota:
            atual["valor_nota"] = valor_nota
        if abs(valor_unico) > abs(atual["valor_unico"]):
            atual["valor_unico"] = valor_unico
        if not atual["tipo_venda"] and item.tipo_venda:
            atual["tipo_venda"] = item.tipo_venda

    total = Decimal("0")
    tipo_entrega = Decimal("0")
    tipo_balcao = Decimal("0")
    for nota in notas.values():
        valor = nota["valor_unico"] or nota["valor_nota"]
        total += valor
        if "balc" in _normalizar_texto(nota["tipo_venda"]):
            tipo_balcao += valor
        else:
            tipo_entrega += valor
    return total, tipo_entrega, tipo_balcao


def _dashboard_faturamento(empresa, inicio, fim):
    linhas = list(
        Faturamento.objects.filter(
            empresa=empresa,
            data_faturamento__gte=inicio,
            data_faturamento__lte=fim,
        ).only(
            "id",
            "numero_nota",
            "valor_nota",
            "valor_nota_unico",
            "prazo_medio",
            "gerente",
            "tipo_venda",
        )
    )
    valor_faturamento, entrega, balcao = _consolidar_notas_faturamento(linhas)

    soma_prazo = sum((_decimal(item.prazo_medio) for item in linhas), Decimal("0"))
    prazo_medio = round(soma_prazo / len(linhas)) if linhas else 0

    grupos = set()
    for item in linhas:
        grupos.add("mp_luciano" if _gerente_eh_mp_ou_luciano(item.gerente) else "pa_outros")

    parametro = _parametro_faturamento(empresa)
    compromisso = _decimal(getattr(parametro, "compromisso", 0))
    gerente_pa = _decimal(getattr(parametro, "gerente_pa_e_outros", 0))
    gerente_mp = _decimal(getattr(parametro, "gerente_mp_e_gerente_luciano", 0))
    if not linhas:
        meta_base = Decimal("0")
    elif {"pa_outros", "mp_luciano"}.issubset(grupos):
        meta_base = compromisso
    elif "mp_luciano" in grupos:
        meta_base = gerente_mp
    else:
        meta_base = gerente_pa

    meta_geral = meta_base
    gap = meta_geral - valor_faturamento
    dias_restantes = _dias_uteis_restantes_mes(inicio, fim)
    meta_diaria = gap / Decimal(dias_restantes) if dias_restantes else Decimal("0")
    percentual_meta = (valor_faturamento / meta_geral * Decimal("100")) if meta_geral else Decimal("0")
    referencia_reloginho = meta_geral if meta_geral > 0 else max(valor_faturamento, Decimal("1"))

    return {
        "valor_faturamento": _texto_moeda(valor_faturamento),
        "meta_geral": _texto_moeda(meta_geral),
        "gap_faturamento": _texto_moeda(gap),
        "prazo_medio": str(prazo_medio),
        "dias_uteis": str(dias_restantes),
        "meta_diaria": _texto_moeda(meta_diaria),
        "reloginho_meta": _texto_moeda(meta_geral),
        "reloginho_real": _texto_moeda(valor_faturamento),
        "reloginho_percentual": _texto_percentual(percentual_meta),
        "tipo_venda_labels": ["Entrega", "Venda Balcao"],
        "tipo_venda_series": [float(entrega), float(balcao)],
        "reloginho_real_percentual": float(max(0, min(percentual_meta, Decimal("100")))),
        "reloginho_meta_angulo": _valor_para_angulo(referencia_reloginho, referencia_reloginho),
        "reloginho_real_angulo": _valor_para_angulo(valor_faturamento, referencia_reloginho),
    }


def _dashboard_vendas(empresa, inicio, fim):
    qs = Venda.objects.filter(empresa=empresa, data_venda__gte=inicio, data_venda__lte=fim)
    vendas = _somar_decimal(qs, "valor_venda")
    cmv = _somar_decimal(qs, "custo_medio_icms_cmv")
    lucro = _somar_decimal(qs, "lucro")
    margem = (lucro / vendas * Decimal("100")) if vendas else Decimal("0")
    return {
        "vendas": _texto_moeda(vendas),
        "cmv": _texto_moeda(cmv),
        "lucro": _texto_moeda(lucro),
        "margem": _texto_percentual(margem),
    }


def _dashboard_estoque(empresa, inicio, fim):
    qs = Estoque.objects.filter(empresa=empresa, data_contagem__gte=inicio, data_contagem__lte=fim)
    data_recente = qs.order_by("-data_contagem").values_list("data_contagem", flat=True).first()
    return {
        "valor": _texto_moeda(_somar_decimal(qs, "custo_total", max_digits=20, decimal_places=3)),
        "data_recente": data_recente.strftime("%d/%m/%Y") if data_recente else "-",
    }


def _dashboard_cargas(empresa, inicio, fim):
    cargas = list(Cargas.objects.filter(empresa=empresa, data_inicio__gte=inicio, data_inicio__lte=fim))
    fora = sum(1 for item in cargas if item.verificacao)
    total = len(cargas)
    return {
        "total": total,
        "no_prazo": total - fora,
        "fora_prazo": fora,
    }


def _categoria_producao(texto):
    valor = _normalizar_texto(texto).replace(" ", "")
    if "30x1" in valor:
        return "30x1"
    if "15x2" in valor:
        return "15x2"
    if "6x5" in valor:
        return "6x5"
    return "outras"


def _realizado_producao(item):
    try:
        lote = _decimal(str(item.tamanho_lote or "").replace(".", "").replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        lote = Decimal("0")
    pacote_por_fardo = _decimal(getattr(item.produto, "pacote_por_fardo", 0) if item.produto else 0)
    multiplo = pacote_por_fardo if pacote_por_fardo > 0 else _decimal(item.kg)
    return lote / multiplo if multiplo > 0 else Decimal("0")


def _dashboard_producao(empresa, inicio, fim):
    qs = (
        Producao.objects.filter(
            empresa=empresa,
            data_hora_entrada_atividade__date__gte=inicio,
            data_hora_entrada_atividade__date__lte=fim,
        )
        .select_related("produto")
        .order_by("id")
    )
    buckets = {
        "30x1": {"realizado": Decimal("0"), "producao_dia": Decimal("0")},
        "15x2": {"realizado": Decimal("0"), "producao_dia": Decimal("0")},
        "6x5": {"realizado": Decimal("0"), "producao_dia": Decimal("0")},
    }
    total_realizado = Decimal("0")
    for item in qs:
        descricao = item.produto.descricao_produto if item.produto else ""
        realizado = _realizado_producao(item)
        if "varredura" not in _normalizar_texto(descricao):
            total_realizado += realizado
        categoria = _categoria_producao(descricao)
        if categoria in buckets:
            buckets[categoria]["realizado"] += realizado
            buckets[categoria]["producao_dia"] = max(buckets[categoria]["producao_dia"], _decimal(item.producao_por_dia))

    hoje = timezone.localdate()
    if hoje < inicio:
        data_referencia = None
    else:
        data_referencia = min(hoje, fim)

    dias_uteis_mes = _dias_uteis(inicio, fim)
    dias_uteis_acumulados = _dias_uteis(inicio, data_referencia) if data_referencia else 0
    total_meta = sum((item["producao_dia"] * dias_uteis_mes for item in buckets.values()), Decimal("0"))
    total_meta_acumulada = sum((item["producao_dia"] * dias_uteis_acumulados for item in buckets.values()), Decimal("0"))
    percentual = (total_realizado / total_meta * Decimal("100")) if total_meta else Decimal("0")
    itens = []
    reloginhos = []
    for titulo, valores in buckets.items():
        meta_mes = valores["producao_dia"] * dias_uteis_mes
        meta_acumulada = valores["producao_dia"] * dias_uteis_acumulados
        realizado = valores["realizado"]
        percentual_item = (realizado / meta_mes * Decimal("100")) if meta_mes else Decimal("0")
        referencia_reloginho = meta_mes if meta_mes > 0 else max(realizado, Decimal("1"))
        itens.append(
            {
                "titulo": titulo,
                "realizado": _texto_numero(realizado, 2),
            }
        )
        reloginhos.append(
            {
                "sufixo": titulo,
                "titulo": f"Producao {titulo}",
                "meta_acum": _texto_numero(meta_acumulada, 2),
                "real": _texto_numero(realizado, 2),
                "percentual": _texto_percentual(percentual_item),
                "meta_angulo": _valor_para_angulo(referencia_reloginho, referencia_reloginho),
                "real_angulo": _valor_para_angulo(realizado, referencia_reloginho),
                "meta80_angulo": None,
            }
        )

    referencia_total = total_meta if total_meta > 0 else max(total_realizado, Decimal("1"))
    return {
        "meta_mes": _texto_numero(total_meta, 2),
        "realizado": _texto_numero(total_realizado, 2),
        "percentual": _texto_percentual(percentual),
        "meta_acumulada": _texto_numero(total_meta_acumulada, 2),
        "itens": itens,
        "reloginhos": reloginhos + [
            {
                "sufixo": "total",
                "titulo": "Producao TOTAL",
                "meta_acum": _texto_numero(total_meta_acumulada, 2),
                "real": _texto_numero(total_realizado, 2),
                "percentual": _texto_percentual(percentual),
                "meta_angulo": _valor_para_angulo(referencia_total, referencia_total),
                "real_angulo": _valor_para_angulo(total_realizado, referencia_total),
                "meta80_angulo": _valor_para_angulo(total_meta * Decimal("0.8"), referencia_total),
            }
        ],
    }


def montar_dashboard_geral(empresa, inicio, fim):
    tofu_qs = Atividade.objects.filter(
        projeto__empresa=empresa,
        data_previsao_termino__gte=inicio,
        data_previsao_termino__lte=fim,
    )
    return {
        "tofu": calcular_dashboard_tofu(tofu_qs),
        "vendas": _dashboard_vendas(empresa, inicio, fim),
        "faturamento": _dashboard_faturamento(empresa, inicio, fim),
        "estoque": _dashboard_estoque(empresa, inicio, fim),
        "cargas": _dashboard_cargas(empresa, inicio, fim),
        "producao": _dashboard_producao(empresa, inicio, fim),
    }


def montar_payload_pdf_dashboard_geral(dashboard, inicio, fim):
    return {
        "periodo_inicio": inicio.strftime("%d/%m/%Y"),
        "periodo_fim": fim.strftime("%d/%m/%Y"),
        "mes_referencia": texto_mes_referencia(inicio),
        "dashboard": dashboard,
    }
