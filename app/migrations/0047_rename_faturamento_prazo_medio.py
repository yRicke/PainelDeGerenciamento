from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0046_drop_legacy_faturamento_tables"),
    ]

    operations = [
        migrations.RenameField(
            model_name="faturamento",
            old_name="prazo_medio_safia",
            new_name="prazo_medio",
        ),
    ]
