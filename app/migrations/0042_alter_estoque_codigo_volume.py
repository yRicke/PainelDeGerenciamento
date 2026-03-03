from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0041_alter_estoque_codigo_voume_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="estoque",
            name="codigo_volume",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]

