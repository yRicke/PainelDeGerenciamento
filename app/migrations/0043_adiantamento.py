from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0042_alter_estoque_codigo_volume"),
    ]

    operations = [
        migrations.CreateModel(
            name="Adiantamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("moeda", models.CharField(blank=True, default="", max_length=120)),
                ("saldo_banco_em_reais", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("saldo_real_em_reais", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("saldo_real", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("conta_descricao", models.CharField(max_length=255)),
                ("saldo_banco", models.BigIntegerField(default=0)),
                ("banco", models.CharField(blank=True, default="", max_length=255)),
                ("agencia", models.CharField(blank=True, default="", max_length=120)),
                ("conta_bancaria", models.CharField(blank=True, default="", max_length=255)),
                ("empresa_descricao", models.CharField(blank=True, default="", max_length=255)),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adiantamentos",
                        to="app.empresa",
                    ),
                ),
            ],
        ),
    ]
