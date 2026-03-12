import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0049_parametronegocios_direcao"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContratoRede",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_registro", models.CharField(max_length=80)),
                ("numero_contrato", models.CharField(max_length=80)),
                ("data_inicio", models.DateField()),
                ("data_encerramento", models.DateField(blank=True, null=True)),
                ("descricao_acordos", models.TextField()),
                ("valor_acordo", models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                (
                    "status_contrato",
                    models.CharField(
                        choices=[("Ativo", "Ativo"), ("Inativo", "Inativo")],
                        default="Ativo",
                        max_length=20,
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contratos_redes",
                        to="app.empresa",
                    ),
                ),
                (
                    "parceiro",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contratos_redes",
                        to="app.parceiro",
                    ),
                ),
            ],
        ),
    ]
