# Compatibility migration to create Asset as a proxy model for FileUpload
# This satisfies old migration dependencies

from django.db import migrations

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("files", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("files.fileupload",),
        ),
    ]
