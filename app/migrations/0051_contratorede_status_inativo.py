from django.db import migrations, models


def normalizar_status_contrato_para_inativo(apps, schema_editor):
    ContratoRede = apps.get_model("app", "ContratoRede")
    ContratoRede.objects.exclude(status_contrato__in=["Ativo", "Inativo"]).update(status_contrato="Inativo")


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0050_contratorede"),
    ]

    operations = [
        migrations.RunPython(
            normalizar_status_contrato_para_inativo,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="contratorede",
            name="status_contrato",
            field=models.CharField(
                choices=[("Ativo", "Ativo"), ("Inativo", "Inativo")],
                default="Ativo",
                max_length=20,
            ),
        ),
    ]
