from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0051_contratorede_status_inativo"),
    ]

    operations = [
        migrations.CreateModel(
            name="DFCSaldoManual",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data_referencia", models.DateField()),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("previsao_recebivel", "Previsao Recebivel"),
                            ("outras_consideracoes_receita", "Outras Consideracoes Receita"),
                            ("adiantamentos_previsao", "Adiantamentos Previsao"),
                            ("outras_consideracoes_despesa", "Outras Consideracoes Despesa"),
                        ],
                        max_length=40,
                    ),
                ),
                ("valor", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dfc_saldos_manuais",
                        to="app.empresa",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="dfcsaldomanual",
            constraint=models.UniqueConstraint(
                fields=("empresa", "data_referencia", "tipo"),
                name="uq_dfc_saldo_manual_empresa_data_tipo",
            ),
        ),
    ]
