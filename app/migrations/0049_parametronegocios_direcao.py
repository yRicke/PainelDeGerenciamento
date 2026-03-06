from decimal import Decimal

from django.db import migrations, models


def ajustar_parametros_negocios(apps, schema_editor):
    ParametroNegocios = apps.get_model("app", "ParametroNegocios")

    primeiro_empresa_3 = ParametroNegocios.objects.filter(empresa_id=3).order_by("id").first()
    if primeiro_empresa_3:
        primeiro_empresa_3.direcao = "Faturamento"
        primeiro_empresa_3.meta = Decimal("10000000.00")
        primeiro_empresa_3.compromisso = Decimal("9000000.00")
        primeiro_empresa_3.gerente_pa_e_outros = Decimal("6000000.00")
        primeiro_empresa_3.gerente_mp_e_gerente_luciano = (
            primeiro_empresa_3.compromisso - primeiro_empresa_3.gerente_pa_e_outros
        )
        primeiro_empresa_3.save(
            update_fields=[
                "direcao",
                "meta",
                "compromisso",
                "gerente_pa_e_outros",
                "gerente_mp_e_gerente_luciano",
            ]
        )

    for item in ParametroNegocios.objects.all().iterator():
        novo_direcao = (item.direcao or "").strip() or "Faturamento"
        novo_gerente_mp = (item.compromisso or Decimal("0")) - (item.gerente_pa_e_outros or Decimal("0"))
        campos = []
        if item.direcao != novo_direcao:
            item.direcao = novo_direcao
            campos.append("direcao")
        if item.gerente_mp_e_gerente_luciano != novo_gerente_mp:
            item.gerente_mp_e_gerente_luciano = novo_gerente_mp
            campos.append("gerente_mp_e_gerente_luciano")
        if campos:
            item.save(update_fields=campos)


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0048_parametronegocios"),
    ]

    operations = [
        migrations.AddField(
            model_name="parametronegocios",
            name="direcao",
            field=models.CharField(default="", max_length=80),
        ),
        migrations.RunPython(ajustar_parametros_negocios, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="parametronegocios",
            name="firecao",
        ),
    ]
