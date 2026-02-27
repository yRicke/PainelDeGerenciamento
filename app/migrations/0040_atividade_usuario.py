from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0039_parametromargemfinanceiro_remuneracao_percentual_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="atividade",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="atividades_criadas",
                to="app.usuario",
            ),
        ),
    ]
