from django.db import migrations


def remove_incorrect_pickle_variant(apps, schema_editor):
    """Remove only the confirmed erroneous 10,000-toman pickle variant."""
    ProductVariant = apps.get_model("shop", "ProductVariant")
    ProductVariant.objects.filter(
        product__slug="ترشی",
        price=10_000,
        amount=100,
        unit="gram",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0008_cartitem"),
    ]

    operations = [
        migrations.RunPython(remove_incorrect_pickle_variant, migrations.RunPython.noop),
    ]
