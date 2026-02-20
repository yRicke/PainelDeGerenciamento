from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0021_contasareceber_vendedor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="fluxodecaixadfc",
            name="descricao_tipo_operacao",
        ),
    ]
