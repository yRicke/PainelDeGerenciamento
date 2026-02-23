from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0029_producao_estoque_minimo_pacote"),
    ]

    operations = [
        migrations.AddField(
            model_name="produto",
            name="empacotadeiras",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="estoque_minimo_pacote",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="horas",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="horas_uteis",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="kg",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="pacote_por_fardo",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="peso_kg",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="ppm",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="producao_por_dia_fd",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="remuneracao_por_fardo",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="setup",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="produto",
            name="status",
            field=models.CharField(blank=True, default="Ativo", max_length=20),
        ),
        migrations.AddField(
            model_name="produto",
            name="turno",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=18),
        ),
    ]
