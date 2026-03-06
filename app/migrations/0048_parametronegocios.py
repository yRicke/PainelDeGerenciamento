from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def criar_parametro_negocios_inicial(apps, schema_editor):
    Empresa = apps.get_model("app", "Empresa")
    ParametroNegocios = apps.get_model("app", "ParametroNegocios")

    if not Empresa.objects.filter(id=3).exists():
        return
    if ParametroNegocios.objects.filter(empresa_id=3).exists():
        return

    compromisso = Decimal("6000000.00")
    gerente_pa_e_outros = Decimal("0.00")
    gerente_mp_e_gerente_luciano = compromisso - gerente_pa_e_outros

    ParametroNegocios.objects.create(
        empresa_id=3,
        firecao=Decimal("10000000.00"),
        meta=Decimal("9000000.00"),
        compromisso=compromisso,
        gerente_pa_e_outros=gerente_pa_e_outros,
        gerente_mp_e_gerente_luciano=gerente_mp_e_gerente_luciano,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0047_rename_faturamento_prazo_medio"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParametroNegocios",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("firecao", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("meta", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("compromisso", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("gerente_pa_e_outros", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("gerente_mp_e_gerente_luciano", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parametros_negocios",
                        to="app.empresa",
                    ),
                ),
            ],
        ),
        migrations.RunPython(criar_parametro_negocios_inicial, migrations.RunPython.noop),
    ]
