from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0034_pedidopendente"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="possui_sistema",
            field=models.BooleanField(default=False),
        ),
    ]
