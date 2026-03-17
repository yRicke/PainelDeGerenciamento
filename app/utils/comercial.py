from ..models import ControleMargem, DescricaoPerfil


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


def _sincronizar_descricao_perfil(empresa, valor, *, vazio_como_none=False, cache=None):
    texto = (str(valor or "")).strip()
    if not texto:
        return None if vazio_como_none else ""

    chave = texto.casefold()
    if cache is not None and chave in cache:
        descricao = cache[chave]
        if descricao:
            return descricao
        return None if vazio_como_none else ""

    item = (
        DescricaoPerfil.objects.filter(empresa=empresa, descricao__iexact=texto)
        .order_by("id")
        .first()
    )
    if not item:
        item = DescricaoPerfil.criar_descricao_perfil(empresa=empresa, descricao=texto)

    descricao = (item.descricao or "").strip()
    if cache is not None:
        cache[chave] = descricao
    if descricao:
        return descricao
    return None if vazio_como_none else ""

