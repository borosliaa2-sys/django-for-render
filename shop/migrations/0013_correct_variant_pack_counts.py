from django.db import migrations


def correct_pack_counts(apps, schema_editor):
    ProductVariant = apps.get_model("shop", "ProductVariant")
    # In the imported catalogue this field was accidentally populated from
    # stock for several products. Every item is a single pack, apart from the
    # product explicitly sold as a two-piece qara pack.
    ProductVariant.objects.exclude(product__name__icontains="قارا بسته دو عددی").update(
        pack_count=1
    )
    ProductVariant.objects.filter(product__name__icontains="قارا بسته دو عددی").update(
        pack_count=2
    )


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0012_article_sort_order"),
    ]

    operations = [migrations.RunPython(correct_pack_counts, migrations.RunPython.noop)]
