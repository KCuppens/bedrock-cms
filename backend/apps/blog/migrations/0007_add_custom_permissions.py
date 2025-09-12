"""
Migration to add custom permissions to Blog models.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0006_add_custom_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="blogpost",
            options={
                "verbose_name": "Blog Post",
                "verbose_name_plural": "Blog Posts",
                "ordering": ["-published_at", "-created_at"],
                "permissions": [
                    ("publish_blogpost", "Can publish blog posts"),
                    ("unpublish_blogpost", "Can unpublish blog posts"),
                    ("feature_blogpost", "Can feature blog posts"),
                    ("moderate_comments", "Can moderate blog comments"),
                    ("bulk_delete_blogpost", "Can bulk delete blog posts"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="category",
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["name"],
                "permissions": [
                    ("manage_blog_category_tree", "Can manage blog category hierarchy"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="tag",
            options={
                "verbose_name": "Tag",
                "verbose_name_plural": "Tags",
                "ordering": ["name"],
                "permissions": [
                    ("merge_tag", "Can merge tags"),
                    ("bulk_delete_tag", "Can bulk delete tags"),
                ],
            },
        ),
    ]
