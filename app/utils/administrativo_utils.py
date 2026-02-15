from datetime import date, datetime


def _transformar_int_ou_none(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _transformar_date_ou_none(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _transformar_iso_week_parts_ou_none(value):
    if not value:
        return None
    try:
        ano_str, semana_str = value.split("-W")
        ano = int(ano_str)
        semana = int(semana_str)
        if semana < 1 or semana > 53:
            return None
        date.fromisocalendar(ano, semana, 1)
        return ano, semana
    except (TypeError, ValueError):
        return None


def _set_prazo_inicio_e_prazo_termino(ano, semana):
    inicio = date.fromisocalendar(ano, semana, 1)
    termino = date.fromisocalendar(ano, semana, 7)
    return inicio, termino
