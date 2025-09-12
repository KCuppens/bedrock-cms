from typing import Any



from django.contrib.auth import get_user_model

from django.db.models import Count, Q



from drf_spectacular.utils import OpenApiParameter, extend_schema

from rest_framework.decorators import api_view, permission_classes

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response



from apps.blog.models import BlogPost

from apps.blog.models import Category as BlogCategory

from apps.blog.models import Tag as BlogTag

from apps.cms.model_parts.category import Collection

from apps.cms.models import Page, Redirect

from apps.files.models import FileUpload

from apps.i18n.models import TranslationUnit

from apps.search.models import SearchQuery



"""Global search functionality for the dashboard search bar."""



User = get_user_model()



def search_pages(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search CMS pages"""

    pages = Page.objects.filter(

        Q(title__icontains=query) | Q(path__icontains=query) | Q(slug__icontains=query)

    ).select_related("locale")[:limit]



    return [

        {

            "id": page.id,

            "title": page.title,

            "type": "page",

            "icon": "📄",

            "description": f"Path: {page.path}",

            "url": f"/dashboard/pages/{page.id}/edit",

            "status": page.status,

            "locale": page.locale.code if page.locale else None,

        }

        for page in pages

    ]



def search_blog_posts(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search blog posts"""

    posts = BlogPost.objects.filter(

        Q(title__icontains=query)

        | Q(content__icontains=query)

        | Q(excerpt__icontains=query)

    ).select_related("author", "category")[:limit]



    return [

        {

            "id": post.id,

            "title": post.title,

            "type": "blog_post",

            "icon": "📝",

            "description": post.excerpt[:100] if post.excerpt else "",

            "url": f"/dashboard/blog-posts/{post.id}/edit",

            "status": post.status,

            "author": post.author.get_full_name() if post.author else None,

        }

        for post in posts

    ]



def search_media(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search media files"""

    files = FileUpload.objects.filter(

        Q(original_filename__icontains=query) | Q(description__icontains=query)

    )[:limit]



    return [

        {

            "id": str(file.id),

            "title": file.original_filename,

            "type": "media",

            "icon": "🖼️",

            "description": f"Type: {file.file_type}, Size: {file.file_size} bytes",

            "url": f"/dashboard/media?file={file.id}",

            "file_type": file.file_type,

            "is_public": file.is_public,

        }

        for file in files

    ]



def search_collections(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search collections"""

    collections = Collection.objects.filter(

        Q(name__icontains=query) | Q(description__icontains=query)

    ).annotate(item_count=Count("categories"))[:limit]



    return [

        {

            "id": collection.id,

            "title": collection.name,

            "type": "collection",

            "icon": "📁",

            "description": (

                collection.description[:100] if collection.description else ""

            ),

            "url": f"/dashboard/collections?id={collection.id}",

            "status": collection.status,

            "item_count": collection.item_count,

        }

        for collection in collections

    ]



def search_categories(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search categories"""

    categories = BlogCategory.objects.filter(

        Q(name__icontains=query) | Q(description__icontains=query)

    )[:limit]



    return [

        {

            "id": category.id,

            "title": category.name,

            "type": "category",

            "icon": "🏷️",

            "description": category.description[:100] if category.description else "",

            "url": f"/dashboard/categories?id={category.id}",

            "color": category.color,

        }

        for category in categories

    ]



def search_tags(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search tags"""

    tags = BlogTag.objects.filter(

        Q(name__icontains=query) | Q(description__icontains=query)

    )[:limit]



    return [

        {

            "id": tag.id,

            "title": tag.name,

            "type": "tag",

            "icon": "🔖",

            "description": tag.description[:100] if tag.description else "",

            "url": f"/dashboard/tags?id={tag.id}",

            "color": tag.color,

        }

        for tag in tags

    ]



def search_translations(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search translations"""

    translations = TranslationUnit.objects.filter(

        Q(key__icontains=query)

        | Q(source_text__icontains=query)

        | Q(target_text__icontains=query)

    ).select_related("source_locale", "target_locale")[:limit]



    return [

        {

            "id": translation.id,

            "title": translation.key,

            "type": "translation",

            "icon": "🌐",

            "description": (

                f"{translation.source_text[:50]}... → {translation.target_text[:50]}..."

                if translation.target_text

                else translation.source_text[:100]

            ),

            "url": f"/dashboard/translations/workspace?id={translation.id}",

            "status": translation.status,

            "locales": f"{translation.source_locale.code} → {translation.target_locale.code}",

        }

        for translation in translations

    ]



def search_users(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search users (admin only)"""

    users = User.objects.filter(

        Q(email__icontains=query)

        | Q(first_name__icontains=query)

        | Q(last_name__icontains=query)

    )[:limit]



    return [

        {

            "id": user.id,

            "title": user.get_full_name() or user.email,

            "type": "user",

            "icon": "👤",

            "description": user.email,

            "url": f"/dashboard/users-roles?user={user.id}",

            "is_active": user.is_active,

        }

        for user in users

    ]



def search_redirects(query: str, limit: int = 5) -> list[dict[str, Any]]:

    """Search redirects"""

    redirects = Redirect.objects.filter(

        Q(from_path__icontains=query) | Q(to_path__icontains=query)

    )[:limit]



    return [

        {

            "id": redirect.id,

            "title": redirect.from_path,

            "type": "redirect",

            "icon": "↪️",

            "description": f"→ {redirect.to_path}",

            "url": f"/dashboard/seo/redirects?id={redirect.id}",

            "status": redirect.status,

        }

        for redirect in redirects

    ]



@extend_schema(

    summary="Global dashboard search",

    description="Search across all content types in the CMS",

    parameters=[

        OpenApiParameter(

            name="q",

            description="Search query",

            required=True,

            type=str,

            location=OpenApiParameter.QUERY,

        ),

        OpenApiParameter(

            name="types",

            description="Content types to search (comma-separated)",

            required=False,

            type=str,

            location=OpenApiParameter.QUERY,

        ),

        OpenApiParameter(

            name="limit",

            description="Maximum results per type",

            required=False,

            type=int,

            location=OpenApiParameter.QUERY,

        ),

    ],

    tags=["Search"],

)

@api_view(["GET"])

@permission_classes([IsAuthenticated])

def global_search(request):



    Global search endpoint for dashboard search bar.



    Searches across multiple content types and returns grouped results.



    query = request.query_params.get("q", "").strip()



    if not query or len(query) < 2:

        return Response({"query": query, "results": [], "total": 0})



    # Get search parameters

    types = (

        request.query_params.get("types", "").split(",")

        if request.query_params.get("types")

        else None

    )

    limit = int(request.query_params.get("limit", 5))



    # Define search types and their functions

    search_functions = {

        "pages": search_pages,

        "blog_posts": search_blog_posts,

        "media": search_media,

        "collections": search_collections,

        "categories": search_categories,

        "tags": search_tags,

        "translations": search_translations,

        "redirects": search_redirects,

    }



    # Add user search for admin users

    if request.user.is_staff:

        search_functions["users"] = search_users



    # Filter search types if specified

    if types:

        search_functions = {k: v for k, v in search_functions.items() if k in types}



    # Perform searches

    results = {}

    total = 0



    for search_type, search_func in search_functions.items():

        try:

            type_results = search_func(query, limit)

            if type_results:

                results[search_type] = type_results

                total += len(type_results)

        except Exception:

            # Log error but continue with other searches



    # Format response

    return Response(

        {"query": query, "results": results, "total": total, "grouped": True}

    )



@extend_schema(

    summary="Search suggestions",

    description="Get search suggestions based on partial query",

    parameters=[

        OpenApiParameter(

            name="q",

            description="Partial search query",

            required=True,

            type=str,

            location=OpenApiParameter.QUERY,

        ),

    ],

    tags=["Search"],

)

@api_view(["GET"])

@permission_classes([IsAuthenticated])

def search_suggestions(request):



    Get search suggestions for autocomplete.



    Returns quick suggestions based on partial query.



    query = request.query_params.get("q", "").strip()



    if not query:

        return Response({"suggestions": []})



    suggestions = []



    # Get recent searches by this user



    recent_searches = (

        SearchQuery.objects.filter(user=request.user, query__istartswith=query)

        .values_list("query", flat=True)

        .distinct()[:5]

    )



    suggestions.extend(

        [{"text": search, "type": "recent", "icon": "🕐"} for search in recent_searches]

    )



    # Get popular pages

    pages = Page.objects.filter(title__istartswith=query).values_list(

        "title", flat=True

    )[:3]



    suggestions.extend(

        [{"text": title, "type": "page", "icon": "📄"} for title in pages]

    )



    # Get popular blog posts

    posts = BlogPost.objects.filter(

        title__istartswith=query, status="published"

    ).values_list("title", flat=True)[:3]



    suggestions.extend(

        [{"text": title, "type": "blog", "icon": "📝"} for title in posts]

    )



    return Response(

        {"query": query, "suggestions": suggestions[:10]}  # Limit total suggestions

    )

