from django.db import migrations, models
import django.db.models.deletion


def migrar_descricoes_bp(apps, schema_editor):
    DescricaoBP = apps.get_model("app", "DescricaoBP")
    BalancoPatrimonial = apps.get_model("app", "BalancoPatrimonial")

    cache = {}
    for item in BalancoPatrimonial.objects.all().order_by("empresa_id", "id"):
        descricao = (getattr(item, "descricao", "") or "").strip() or "Sem descricao"
        chave = (item.empresa_id, descricao.casefold())
        descricao_bp = cache.get(chave)
        if descricao_bp is None:
            descricao_bp, _ = DescricaoBP.objects.get_or_create(
                empresa_id=item.empresa_id,
                descricao=descricao,
            )
            cache[chave] = descricao_bp
        item.descricao_bp_id = descricao_bp.id
        item.save(update_fields=["descricao_bp"])


def restaurar_descricoes_texto(apps, schema_editor):
    DescricaoBP = apps.get_model("app", "DescricaoBP")
    BalancoPatrimonial = apps.get_model("app", "BalancoPatrimonial")

    descricoes_por_id = {
        item.id: item.descricao
        for item in DescricaoBP.objects.all()
    }
    for item in BalancoPatrimonial.objects.all().only("id", "descricao_bp_id", "descricao"):
        item.descricao = descricoes_por_id.get(item.descricao_bp_id, "") or "Sem descricao"
        item.save(update_fields=["descricao"])


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0068_parametromargemfinanceiro_remuneracao_precisao"),
    ]

    operations = [
        migrations.CreateModel(
            name="DescricaoBP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descricao", models.CharField(max_length=220)),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="descricoes_bp",
                        to="app.empresa",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="descricaobp",
            constraint=models.UniqueConstraint(
                fields=("empresa", "descricao"),
                name="uq_descricao_bp_empresa_descricao",
            ),
        ),
        migrations.AddField(
            model_name="balancopatrimonial",
            name="descricao_bp",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="balancos_patrimoniais",
                to="app.descricaobp",
            ),
        ),
        migrations.RunPython(migrar_descricoes_bp, restaurar_descricoes_texto),
        migrations.RemoveField(
            model_name="balancopatrimonial",
            name="descricao",
        ),
        migrations.AlterField(
            model_name="balancopatrimonial",
            name="descricao_bp",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="balancos_patrimoniais",
                to="app.descricaobp",
            ),
        ),
    ]
