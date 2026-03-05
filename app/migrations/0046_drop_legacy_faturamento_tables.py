from django.db import migrations


def _drop_legacy_faturamento_tables(apps, schema_editor):
    tabelas = [
        "app_faturamentoadministrativo",
        "app_faturamentoaministrativo",
        "app_faturamentoimportacaoarquivo",
        "app_faturamentoimportacaolote",
        "app_faturamentoimportacaometadiaria",
        "app_faturamentometadiaria",
    ]
    for tabela in tabelas:
        schema_editor.execute(f'DROP TABLE IF EXISTS "{tabela}"')


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0045_remove_faturamento_descricao_centro_resultado_and_more"),
    ]

    operations = [
        migrations.RunPython(
            _drop_legacy_faturamento_tables,
            migrations.RunPython.noop,
        ),
    ]
