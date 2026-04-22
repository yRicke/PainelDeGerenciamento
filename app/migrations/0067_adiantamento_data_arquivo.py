from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0066_parametronegocios_unidades_meta_compromisso"),
    ]

    operations = [
        migrations.AddField(
            model_name="adiantamento",
            name="data_arquivo",
            field=models.DateField(blank=True, null=True),
        ),
    ]
