# Generated migration for blog performance indexes

from django.db import migrations, models


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
        # Add GIN index for blocks field on PostgreSQL
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS blog_blogpost_blocks_gin 
            ON blog_blogpost USING gin (blocks jsonb_path_ops)
            WHERE blocks IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS blog_blogpost_blocks_gin;",
            state_operations=[],
        ),
        # Add full text search index for PostgreSQL
        migrations.RunSQL(
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
            state_operations=[],
        ),
        # Add index for tag lookups
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["slug"], name="blog_tag_slug_idx"),
        ),
        # Add index for category lookups
        migrations.AddIndex(
            model_name="category",
            index=models.Index(
                fields=["slug", "locale"], name="blog_category_slug_idx"
            ),
        ),
        # Add index for view tracker
        migrations.AddIndex(
            model_name="blogpostviewtracker",
            index=models.Index(
                fields=["blog_post", "-last_viewed"], name="blog_view_tracker_idx"
            ),
        ),
    ]
