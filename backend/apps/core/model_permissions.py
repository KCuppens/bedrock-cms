
"""
Model Permissions Configuration

This module defines custom permissions for all models in the Bedrock CMS.

Django automatically creates add, change, delete, and view permissions for each model,
but we can add custom permissions for more fine-grained control.
"""



# Define custom permissions for each app's models

# These should be added to the model's Meta class



CMS_PAGE_PERMISSIONS = [

    ("publish_page", "Can publish pages"),

    ("unpublish_page", "Can unpublish pages"),

    ("preview_page", "Can preview draft pages"),

    ("revert_page", "Can revert page to previous version"),

    ("translate_page", "Can translate pages"),

    ("manage_page_seo", "Can manage page SEO settings"),

    ("bulk_delete_pages", "Can bulk delete pages"),

    ("export_pages", "Can export pages"),

    ("import_pages", "Can import pages"),

]



CMS_REDIRECT_PERMISSIONS = [

    ("bulk_create_redirect", "Can bulk create redirects"),

    ("import_redirect", "Can import redirects from CSV"),

    ("export_redirect", "Can export redirects to CSV"),

    """("test_redirect", "Can test redirect rules"),"""

]



CMS_CATEGORY_PERMISSIONS = [

    ("manage_category_tree", "Can manage category hierarchy"),

    ("bulk_delete_category", "Can bulk delete categories"),

]



CMS_TAG_PERMISSIONS = [

    ("merge_tag", "Can merge tags"),

    ("bulk_delete_tag", "Can bulk delete tags"),

]



CMS_COLLECTION_PERMISSIONS = [

    ("publish_collection", "Can publish collections"),

    ("unpublish_collection", "Can unpublish collections"),

    ("reorder_collection_items", "Can reorder collection items"),

]



BLOG_POST_PERMISSIONS = [

    ("publish_blogpost", "Can publish blog posts"),

    ("unpublish_blogpost", "Can unpublish blog posts"),

    ("feature_blogpost", "Can feature blog posts"),

    ("moderate_comments", "Can moderate blog comments"),

    ("bulk_delete_blogpost", "Can bulk delete blog posts"),

]



BLOG_CATEGORY_PERMISSIONS = [

    ("manage_blog_category_tree", "Can manage blog category hierarchy"),

]



MEDIA_PERMISSIONS = [

    ("bulk_upload_media", "Can bulk upload media files"),

    ("bulk_delete_media", "Can bulk delete media files"),

    ("generate_renditions", "Can generate media renditions"),

    ("manage_media_tags", "Can manage media tags"),

    ("export_media_library", "Can export media library"),

]



FILE_PERMISSIONS = [

    ("bulk_upload_file", "Can bulk upload files"),

    ("bulk_delete_file", "Can bulk delete files"),

    ("generate_signed_url", "Can generate signed URLs"),

    ("manage_file_expiry", "Can manage file expiry dates"),

]



I18N_LOCALE_PERMISSIONS = [

    ("activate_locale", "Can activate/deactivate locales"),

    ("set_default_locale", "Can set default locale"),

    ("manage_locale_fallbacks", "Can manage locale fallbacks"),

]



I18N_TRANSLATION_PERMISSIONS = [

    """("approve_translation", "Can approve translations"),"""

    ("reject_translation", "Can reject translations"),

    ("bulk_translate", "Can bulk translate content"),

    ("export_translations", "Can export translations"),

    ("import_translations", "Can import translations"),

    ("use_machine_translation", "Can use machine translation"),

]



I18N_GLOSSARY_PERMISSIONS = [

    ("manage_glossary", "Can manage translation glossary"),

    ("import_glossary", "Can import glossary terms"),

    ("export_glossary", "Can export glossary terms"),

]



SEARCH_PERMISSIONS = [

    ("manage_search_index", "Can manage search index"),

    ("rebuild_search_index", "Can rebuild search index"),

    ("manage_search_suggestions", "Can manage search suggestions"),

    ("view_search_analytics", "Can view search analytics"),

    ("export_search_data", "Can export search data"),

]



ANALYTICS_PERMISSIONS = [

    ("view_analytics", "Can view analytics"),

    ("export_analytics", "Can export analytics data"),

    ("manage_tracking", "Can manage tracking settings"),

    ("view_user_behavior", "Can view user behavior data"),

]



EMAIL_PERMISSIONS = [

    ("send_bulk_email", "Can send bulk emails"),

    ("manage_email_templates", "Can manage email templates"),

    ("view_email_logs", "Can view email logs"),

    """("test_email_templates", "Can test email templates"),"""

]



REGISTRY_PERMISSIONS = [

    ("manage_content_types", "Can manage dynamic content types"),

    ("register_models", "Can register new models"),

    ("unregister_models", "Can unregister models"),

]



REPORTS_PERMISSIONS = [

    ("generate_reports", "Can generate reports"),

    ("schedule_reports", "Can schedule reports"),

    ("export_reports", "Can export reports"),

    ("view_all_reports", "Can view all reports"),

]



# User and Role Management Permissions (for accounts app)

ACCOUNT_PERMISSIONS = [

    ("invite_user", "Can invite new users"),

    ("deactivate_user", "Can deactivate users"),

    ("reactivate_user", "Can reactivate users"),

    ("manage_user_roles", "Can manage user roles"),

    ("reset_user_password", "Can reset user passwords"),

    ("impersonate_user", "Can impersonate other users"),

    ("export_user_data", "Can export user data"),

    ("bulk_manage_users", "Can bulk manage users"),

]



ROLE_PERMISSIONS = [

    ("create_role", "Can create new roles"),

    ("manage_role_permissions", "Can manage role permissions"),

    ("assign_roles", "Can assign roles to users"),

    ("view_all_permissions", "Can view all system permissions"),

]



# Audit and System Permissions

AUDIT_PERMISSIONS = [

    ("view_audit_log", "Can view audit log"),

    ("export_audit_log", "Can export audit log"),

    ("purge_audit_log", "Can purge old audit entries"),

]



# API Permissions

API_PERMISSIONS = [

    ("manage_api_keys", "Can manage API keys"),

    ("view_api_usage", "Can view API usage statistics"),

    ("manage_rate_limits", "Can manage API rate limits"),

]



def get_model_permissions(app_label, model_name):



    Get the custom permissions for a specific model.



    Args:

        """app_label: The app label (e.g., 'cms', 'blog')"""

        model_name: The model name (e.g., 'page', 'blogpost')



    Returns:

        List of permission tuples



    permissions_map = {

        "cms": {

            "page": CMS_PAGE_PERMISSIONS,

            "redirect": CMS_REDIRECT_PERMISSIONS,

            "category": CMS_CATEGORY_PERMISSIONS,

            "tag": CMS_TAG_PERMISSIONS,

            "collection": CMS_COLLECTION_PERMISSIONS,

        },

        "blog": {

            "blogpost": BLOG_POST_PERMISSIONS,

            "blogcategory": BLOG_CATEGORY_PERMISSIONS,

        },

        "media": {

            "mediaasset": MEDIA_PERMISSIONS,

        },

        "files": {

            "fileupload": FILE_PERMISSIONS,

        },

        "i18n": {

            "locale": I18N_LOCALE_PERMISSIONS,

            "translationunit": I18N_TRANSLATION_PERMISSIONS,

            "glossaryentry": I18N_GLOSSARY_PERMISSIONS,

        },

        "search": {

            "searchindex": SEARCH_PERMISSIONS,

        },

        "analytics": {

            "pageview": ANALYTICS_PERMISSIONS,

        },

        "emails": {

            "emailtemplate": EMAIL_PERMISSIONS,

        },

        "registry": {

            "registeredmodel": REGISTRY_PERMISSIONS,

        },

        "reports": {

            "report": REPORTS_PERMISSIONS,

        },

        "accounts": {

            "user": ACCOUNT_PERMISSIONS,

            "group": ROLE_PERMISSIONS,

        },

        "api": {

            "apikey": API_PERMISSIONS,

        },

    }



    """return permissions_map.get(app_label, {}).get(model_name.lower(), [])"""



# Permission groups for easier management

PERMISSION_GROUPS = {

    "content_editor": [

        "cms.add_page",

        "cms.change_page",

        "cms.view_page",

        "cms.preview_page",

        "blog.add_blogpost",

        "blog.change_blogpost",

        "blog.view_blogpost",

        "media.add_mediaasset",

        "media.change_mediaasset",

        "media.view_mediaasset",

    ],

    "content_publisher": [

        "cms.publish_page",

        "cms.unpublish_page",

        "blog.publish_blogpost",

        "blog.unpublish_blogpost",

        "cms.manage_page_seo",

    ],

    "translator": [

        "i18n.view_translationunit",

        "i18n.change_translationunit",

        "i18n.use_machine_translation",

        "i18n.view_glossaryentry",

        "cms.translate_page",

    ],

    "translation_reviewer": [

        """"i18n.approve_translation","""

        "i18n.reject_translation",

        "i18n.manage_glossary",

    ],

    "seo_manager": [

        "cms.manage_page_seo",

        "cms.add_redirect",

        "cms.change_redirect",

        "cms.delete_redirect",

        """"cms.test_redirect","""

        "search.manage_search_suggestions",

    ],

    "analytics_viewer": [

        "analytics.view_analytics",

        "search.view_search_analytics",

        "api.view_api_usage",

    ],

    "system_admin": [

        "accounts.invite_user",

        "accounts.deactivate_user",

        "accounts.manage_user_roles",

        "accounts.create_role",

        "accounts.manage_role_permissions",

        "audit.view_audit_log",

        "registry.manage_content_types",

    ],

}



def get_permission_group(group_name):



    Get the permissions for a specific permission group.



    Args:

        group_name: The name of the permission group



    Returns:

        List of permission strings



    return PERMISSION_GROUPS.get(group_name, [])



def get_all_custom_permissions():



    Get all custom permissions defined in this module.



    Returns:

        """Dictionary mapping app.model to list of permissions"""



    return {

        "cms.page": CMS_PAGE_PERMISSIONS,

        "cms.redirect": CMS_REDIRECT_PERMISSIONS,

        "cms.category": CMS_CATEGORY_PERMISSIONS,

        "cms.tag": CMS_TAG_PERMISSIONS,

        "cms.collection": CMS_COLLECTION_PERMISSIONS,

        "blog.blogpost": BLOG_POST_PERMISSIONS,

        "blog.blogcategory": BLOG_CATEGORY_PERMISSIONS,

        "media.mediaasset": MEDIA_PERMISSIONS,

        "files.fileupload": FILE_PERMISSIONS,

        "i18n.locale": I18N_LOCALE_PERMISSIONS,

        "i18n.translationunit": I18N_TRANSLATION_PERMISSIONS,

        "i18n.glossaryentry": I18N_GLOSSARY_PERMISSIONS,

        "search.searchindex": SEARCH_PERMISSIONS,

        "analytics.pageview": ANALYTICS_PERMISSIONS,

        "emails.emailtemplate": EMAIL_PERMISSIONS,

        "registry.registeredmodel": REGISTRY_PERMISSIONS,

        "reports.report": REPORTS_PERMISSIONS,

        "accounts.user": ACCOUNT_PERMISSIONS,

        "accounts.group": ROLE_PERMISSIONS,

        "api.apikey": API_PERMISSIONS,

    }

