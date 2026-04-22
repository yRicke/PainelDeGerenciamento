from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0065_alter_precificacaoprodutoacabadoprecovenda_situacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="parametronegocios",
            name="compromisso_unidade",
            field=models.CharField(
                choices=[("valor", "R$"), ("percentual", "%")],
                default="valor",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="parametronegocios",
            name="meta_unidade",
            field=models.CharField(
                choices=[("valor", "R$"), ("percentual", "%")],
                default="valor",
                max_length=12,
            ),
        ),
    ]
