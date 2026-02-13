import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse

from .models import Atividade


class AtividadeTable(tables.Table):
    id = tables.Column(verbose_name="ID")
    projeto = tables.Column(accessor="projeto.nome", verbose_name="Projeto", order_by=("projeto__nome",))
    codigo_projeto = tables.Column(accessor="projeto.codigo", verbose_name="Codigo Projeto", order_by=("projeto__codigo",))
    gestor = tables.Column(accessor="gestor.nome", verbose_name="Gestor", order_by=("gestor__nome",), default="-")
    responsavel = tables.Column(accessor="responsavel.nome", verbose_name="Responsavel", order_by=("responsavel__nome",), default="-")
    interlocutor = tables.Column(verbose_name="Interlocutor")
    data_previsao_inicio = tables.DateColumn(verbose_name="Prev. Inicio", format="d/m/Y")
    data_previsao_termino = tables.DateColumn(verbose_name="Prev. Termino", format="d/m/Y")
    data_finalizada = tables.DateColumn(verbose_name="Finalizada", format="d/m/Y")
    indicador = tables.Column(verbose_name="Indicador", orderable=False)
    historico = tables.Column(verbose_name="Historico")
    tarefa = tables.Column(verbose_name="Tarefa")
    progresso = tables.Column(verbose_name="Progresso (%)")
    acoes = tables.Column(empty_values=(), orderable=False, verbose_name="Acoes")

    class Meta:
        model = Atividade
        template_name = "django_tables2/table.html"
        attrs = {"class": "atividade-table"}
        fields = (
            "id",
            "projeto",
            "codigo_projeto",
            "gestor",
            "responsavel",
            "interlocutor",
            "data_previsao_inicio",
            "data_previsao_termino",
            "data_finalizada",
            "indicador",
            "historico",
            "tarefa",
            "progresso",
        )

    def render_acoes(self, record):
        empresa_id = record.projeto.empresa_id
        editar_url = reverse("editar_atividade_tofu", kwargs={"empresa_id": empresa_id, "atividade_id": record.id})
        return format_html(
            '<a class="btn-primary" href="{}">Editar</a>',
            editar_url
        )
