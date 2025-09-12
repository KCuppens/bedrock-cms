from django.db import migrations

Migration to add custom permissions to CMS models.



class Migration(migrations.Migration):

    dependencies = [

        ("cms", "0007_add_custom_permissions"),

    ]



    operations = [

        migrations.AlterModelOptions(

            name="page",

            options={

                "ordering": ["parent_id", "position", "id"],

                "permissions": [

                    ("publish_page", "Can publish pages"),

                    ("unpublish_page", "Can unpublish pages"),

                    ("preview_page", "Can preview draft pages"),

                    ("revert_page", "Can revert page to previous version"),

                    ("translate_page", "Can translate pages"),

                    ("manage_page_seo", "Can manage page SEO settings"),

                    ("bulk_delete_pages", "Can bulk delete pages"),

                    ("export_pages", "Can export pages"),

                    ("import_pages", "Can import pages"),

                ],

            },

        ),

        migrations.AlterModelOptions(

            name="redirect",

            options={

                "permissions": [

                    ("bulk_create_redirect", "Can bulk create redirects"),

                    ("import_redirect", "Can import redirects from CSV"),

                    ("export_redirect", "Can export redirects to CSV"),

                    """("test_redirect", "Can test redirect rules"),"""

                ],

            },

        ),

    ]
