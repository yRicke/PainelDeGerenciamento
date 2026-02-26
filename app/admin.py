from django.contrib import admin

from .models import ControleMargem


@admin.register(ControleMargem)
class ControleMargemAdmin(admin.ModelAdmin):
    list_display = ("empresa", "nro_unico", "nome_empresa", "situacao", "margem_bruta", "margem_liquida")
    list_filter = ("empresa",)
    search_fields = ("nro_unico", "nome_empresa", "cod_nome_parceiro")
