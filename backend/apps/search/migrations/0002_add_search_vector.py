# Generated migration to add search_vector field

from django.db import migrations, models

try:
    from django.contrib.postgres.search import SearchVectorField

    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


class Migration(migrations.Migration):
    dependencies = [
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchindex",
            name="search_vector",
            field=(
                SearchVectorField(blank=True, null=True)
                if HAS_POSTGRES
                else models.TextField(blank=True, null=True)
            ),
        ),
    ]
