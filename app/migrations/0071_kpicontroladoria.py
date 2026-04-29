from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0070_planocargosalario_contato"),
    ]

    operations = [
        migrations.CreateModel(
            name="KpiControladoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("analise", models.PositiveIntegerField()),
                ("tipo", models.CharField(choices=[("Verificacao", "Verificacao"), ("Controle", "Controle")], max_length=20)),
                ("descricao", models.CharField(max_length=255)),
                ("parametro_meta", models.CharField(blank=True, default="", max_length=255)),
                ("parametro_compromisso", models.CharField(blank=True, default="", max_length=255)),
                ("semana_1_conferencia", models.BooleanField(default=False)),
                ("semana_1_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("semana_2_conferencia", models.BooleanField(default=False)),
                ("semana_2_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("semana_3_conferencia", models.BooleanField(default=False)),
                ("semana_3_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("semana_4_conferencia", models.BooleanField(default=False)),
                ("semana_4_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("semana_5_conferencia", models.BooleanField(default=False)),
                ("semana_5_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("total_mes_conferencia", models.BooleanField(default=False)),
                ("total_mes_resultado", models.CharField(blank=True, choices=[("Ok", "Ok"), ("Alerta", "Alerta")], default="", max_length=20)),
                ("consideracoes", models.CharField(blank=True, default="", max_length=255)),
                ("empresa", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="kpis_controladoria", to="app.empresa")),
            ],
        ),
        migrations.AddConstraint(
            model_name="kpicontroladoria",
            constraint=models.UniqueConstraint(fields=("empresa", "analise"), name="uq_kpi_controladoria_empresa_analise"),
        ),
    ]
