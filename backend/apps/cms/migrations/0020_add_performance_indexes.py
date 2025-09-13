# Generated migration for performance indexes


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0019_add_model_relationships_to_blocktype"),
    ]

    operations = [
        # Add GIN index for JSON fields on PostgreSQL
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS cms_page_blocks_gin
            ON cms_page USING gin (blocks jsonb_path_ops)
            WHERE blocks IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS cms_page_blocks_gin;",
            state_operations=[],
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS cms_page_seo_gin
            ON cms_page USING gin (seo jsonb_path_ops)
            WHERE seo IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS cms_page_seo_gin;",
            state_operations=[],
        ),
        # Add composite index for homepage lookup
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                fields=["locale", "is_homepage"],
                name="cms_page_homepage_idx",
                condition=models.Q(is_homepage=True),
            ),
        ),
        # Add index for menu pages
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                fields=["locale", "in_main_menu", "position"],
                name="cms_page_menu_idx",
                condition=models.Q(in_main_menu=True),
            ),
        ),
        # Add index for footer pages
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                fields=["locale", "in_footer", "position"],
                name="cms_page_footer_idx",
                condition=models.Q(in_footer=True),
            ),
        ),
        # Add covering index for list queries
        migrations.AddIndex(
            model_name="page",
            index=(
                models.Index(
                    fields=["status", "locale", "-updated_at"],
                    name="cms_page_list_idx",
                    include=["title", "slug", "path"],  # PostgreSQL 11+ only
                )
                if hasattr(models.Index, "include")
                else models.Index(
                    fields=["status", "locale", "-updated_at"], name="cms_page_list_idx"
                )
            ),
        ),
        # Index for scheduling queries
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                fields=["status", "scheduled_publish_at"],
                name="cms_page_schedule_pub_idx",
                condition=models.Q(status="scheduled"),
            ),
        ),
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                fields=["status", "scheduled_unpublish_at"],
                name="cms_page_schedule_unpub_idx",
                condition=models.Q(scheduled_unpublish_at__isnull=False),
            ),
        ),
        # Optimize redirect lookups
        migrations.AddIndex(
            model_name="redirect",
            index=models.Index(
                fields=["from_path", "is_active"],
                name="cms_redirect_lookup_idx",
                condition=models.Q(is_active=True),
            ),
        ),
    ]
