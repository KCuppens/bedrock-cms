# Generated migration for thumbnail support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0002_mediacategory"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileupload",
            name="width",
            field=models.PositiveIntegerField(
                blank=True, help_text="Image width in pixels", null=True
            ),
        ),
        migrations.AddField(
            model_name="fileupload",
            name="height",
            field=models.PositiveIntegerField(
                blank=True, help_text="Image height in pixels", null=True
            ),
        ),
        migrations.AddField(
            model_name="fileupload",
            name="blurhash",
            field=models.CharField(
                blank=True,
                help_text="BlurHash for ultra-fast image placeholders",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="fileupload",
            name="dominant_color",
            field=models.CharField(
                blank=True, help_text="Dominant color as hex value", max_length=7
            ),
        ),
        migrations.AddField(
            model_name="fileupload",
            name="thumbnails",
            field=models.JSONField(
                default=dict,
                help_text="Generated thumbnail configurations and URLs",
            ),
        ),
    ]
