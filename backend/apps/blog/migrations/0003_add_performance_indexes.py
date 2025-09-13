# Generated migration for blog performance indexes


from django.db import migrations, models

from apps.core.migration_utils import (
    conditional_sql_for_postgresql,
    gin_index_operation,
)


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0002_add_presentation_features"),
    ]

    operations = [
        # Add index for featured posts
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(
                fields=["status", "featured", "-published_at"],
                name="blog_post_featured_idx",
                condition=models.Q(featured=True, status="published"),
            ),
        ),
        # Add index for category posts
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(
                fields=["category", "status", "-published_at"],
                name="blog_post_category_idx",
                condition=models.Q(status="published"),
            ),
        ),
        # Add index for author posts
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(
                fields=["author", "status", "-published_at"],
                name="blog_post_author_idx",
                condition=models.Q(status="published"),
            ),
        ),
        # Add covering index for list queries
        migrations.AddIndex(
            model_name="blogpost",
            index=(
                models.Index(
                    fields=["locale", "status", "-published_at"],
                    name="blog_post_list_idx",
                    include=[
                        "title",
                        "slug",
                        "excerpt",
                        "featured",
                    ],  # PostgreSQL 11+ only
                )
                if hasattr(models.Index, "include")
                else models.Index(
                    fields=["locale", "status", "-published_at"],
                    name="blog_post_list_idx",
                )
            ),
        ),
        # Add GIN index for blocks field on PostgreSQL only
        gin_index_operation(
            table_name="blog_blogpost",
            column_name="blocks",
            index_name="blog_blogpost_blocks_gin",
            condition="blocks IS NOT NULL",
        ),
        # Add full text search index for PostgreSQL only
        conditional_sql_for_postgresql(
            sql="""
            CREATE INDEX IF NOT EXISTS blog_blogpost_search_idx
            ON blog_blogpost USING gin (
                to_tsvector('english',
                    coalesce(title, '') || ' ' ||
                    coalesce(excerpt, '') || ' ' ||
                    coalesce(content, '')
                )
            );
            """,
            reverse_sql="DROP INDEX IF EXISTS blog_blogpost_search_idx;",
        ),
        # Add index for tag lookups
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["slug"], name="blog_tag_slug_idx"),
        ),
        # Add index for category lookups
        migrations.AddIndex(
            model_name="category",
            index=models.Index(fields=["slug"], name="blog_category_slug_idx"),
        ),
    ]
