# Generated migration for adding base64_micro field to FileUpload

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0003_add_thumbnail_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileupload",
            name="base64_micro",
            field=models.TextField(
                blank=True,
                help_text="Ultra-small base64-encoded thumbnail (~500 bytes) for inline embedding",
                verbose_name="Base64 micro thumbnail",
            ),
        ),
    ]
