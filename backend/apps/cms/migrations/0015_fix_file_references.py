# Manual migration to fix file references

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0001_initial"),
        ("cms", "0014_add_comprehensive_seo_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="seosettings",
            name="default_og_asset",
            field=models.ForeignKey(
                blank=True,
                help_text="Default Open Graph image",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="seo_defaults",
                to="files.fileupload",
            ),
        ),
        migrations.AlterField(
            model_name="seosettings",
            name="default_twitter_asset",
            field=models.ForeignKey(
                blank=True,
                help_text="Default Twitter card image",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="twitter_seo_defaults",
                to="files.fileupload",
            ),
        ),
    ]
