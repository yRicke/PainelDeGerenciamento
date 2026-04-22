from decimal import Decimal

from django.db import migrations, models


def recalcular_remuneracao_financeira(apps, schema_editor):
    ParametroMargemFinanceiro = apps.get_model("app", "ParametroMargemFinanceiro")
    for parametro in ParametroMargemFinanceiro.objects.all():
        parametro.remuneracao_percentual = Decimal(parametro.taxa_ao_mes or 0) / Decimal("30")
        parametro.save(update_fields=["remuneracao_percentual"])


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0067_adiantamento_data_arquivo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parametromargemfinanceiro",
            name="remuneracao_percentual",
            field=models.DecimalField(decimal_places=12, default=0, max_digits=18),
        ),
        migrations.RunPython(recalcular_remuneracao_financeira, migrations.RunPython.noop),
    ]
