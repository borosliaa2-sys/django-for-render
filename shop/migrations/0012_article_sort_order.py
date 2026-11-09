from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0011_contact_message_inbox"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش"),
        ),
        migrations.AlterModelOptions(
            name="article",
            options={
                "ordering": ["sort_order", "-created_at"],
                "verbose_name": "مقاله",
                "verbose_name_plural": "مقالات و وبلاگ",
            },
        ),
        migrations.RemoveIndex(
            model_name="article",
            name="art_pub_idx",
        ),
        migrations.AddIndex(
            model_name="article",
            index=models.Index(
                fields=["is_published", "sort_order", "-created_at"],
                name="art_pub_sort_idx",
            ),
        ),
    ]
