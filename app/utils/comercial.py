from ..models import ControleMargem


def _normalizar_numero_unico_texto(valor):
    texto = (str(valor or "")).strip()
    if not texto:
        return ""
    if texto.endswith(".0"):
        texto = texto[:-2]
    texto = texto.replace(" ", "")
    if texto.isdigit():
        return str(int(texto))
    return texto


def _gerente_valido_ou_vazio(valor):
    texto = (str(valor or "")).strip()
    if not texto:
        return ""
    if texto.upper() in {"<SEM VENDEDOR>", "SEM VENDEDOR", "<SEM GERENTE>", "SEM GERENTE"}:
        return ""
    return texto


def _situacao_controle_margem_param_ou_none(valor):
    texto = (valor or "").strip().lower()
    if not texto:
        return ""
    mapa = {
        "amarelo": ControleMargem.SITUACAO_AMARELO,
        "roxo": ControleMargem.SITUACAO_ROXO,
        "verde": ControleMargem.SITUACAO_VERDE,
        "vermelho": ControleMargem.SITUACAO_VERMELHO,
    }
    return mapa.get(texto, "")


def _filtrar_controle_margem_por_situacao(qs, situacao):
    if not situacao:
        return qs
    if situacao == ControleMargem.SITUACAO_ROXO:
        return qs.filter(margem_bruta__lt=0.10)
    if situacao == ControleMargem.SITUACAO_VERMELHO:
        return qs.filter(margem_bruta__gte=0.10, margem_bruta__lt=0.12)
    if situacao == ControleMargem.SITUACAO_AMARELO:
        return qs.filter(margem_bruta__gte=0.12, margem_bruta__lt=0.14)
    if situacao == ControleMargem.SITUACAO_VERDE:
        return qs.filter(margem_bruta__gte=0.14)
    return qs.none()

