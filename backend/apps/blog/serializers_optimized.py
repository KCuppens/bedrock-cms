from rest_framework import serializers



from .models import BlogPost, Category, Tag



Optimized serializers for Blog with reduced field loading.



class BlogPostMinimalSerializer(serializers.ModelSerializer):

    """Ultra-minimal serializer for references."""



    class Meta:

        model = BlogPost

        fields = ["id", "title", "slug"]



class BlogPostListSerializer(serializers.ModelSerializer):

    """Optimized serializer for blog post lists."""



    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    category_name = serializers.CharField(source="category.name", read_only=True)

    locale_code = serializers.CharField(source="locale.code", read_only=True)

    tags_list = serializers.SerializerMethodField()

    view_count = serializers.IntegerField(read_only=True)



    class Meta:

        model = BlogPost

        fields = [

            "id",

            "title",

            "slug",

            "excerpt",

            "status",

            "author_name",

            "category_name",

            "locale_code",

            "tags_list",

            "view_count",

            "featured",

            "published_at",

            "updated_at",

            "created_at",

        ]



    def get_tags_list(self, obj):

        # Use prefetched tags

        if (

            hasattr(obj, "_prefetched_objects_cache")

            and "tags" in obj._prefetched_objects_cache

        ):

            return [tag.name for tag in obj.tags.all()]

        return []



class BlogPostDetailSerializer(serializers.ModelSerializer):

    """Full serializer for blog post detail views."""



    author = serializers.SerializerMethodField()

    category = serializers.SerializerMethodField()

    tags = serializers.SerializerMethodField()

    locale = serializers.SerializerMethodField()

    view_count = serializers.IntegerField(read_only=True)

    recent_revisions = serializers.SerializerMethodField()



    class Meta:

        model = BlogPost

        fields = "__all__"



    def get_author(self, obj):

        return {

            "id": obj.author.id,

            "name": obj.author.get_full_name(),

            "email": obj.author.email,

        }



    def get_category(self, obj):

        if obj.category:

            return {

                "id": obj.category.id,

                "name": obj.category.name,

                "slug": obj.category.slug,

            }

        return None



    def get_tags(self, obj):

        return [

            {"id": tag.id, "name": tag.name, "slug": tag.slug} for tag in obj.tags.all()

        ]



    def get_locale(self, obj):

        return {"id": obj.locale.id, "code": obj.locale.code, "name": obj.locale.name}



    def get_recent_revisions(self, obj):

        # Use prefetched revisions if available

        if (

            hasattr(obj, "_prefetched_objects_cache")

            and "revisions" in obj._prefetched_objects_cache

        ):

            revisions = obj.revisions.all()[:5]

            return [

                {

                    "id": rev.id,

                    "created_at": rev.created_at,

                    "user": rev.user.get_full_name() if rev.user else None,

                    "comment": rev.comment,

                }

                for rev in revisions

            ]

        return []



class CategoryListSerializer(serializers.ModelSerializer):

    """Optimized serializer for category lists."""



    post_count = serializers.SerializerMethodField()



    class Meta:

        model = Category

        fields = ["id", "name", "slug", "description", "post_count"]



    def get_post_count(self, obj):

        # Use annotation if available

        if hasattr(obj, "post_count"):

            return obj.post_count

        return 0



class TagListSerializer(serializers.ModelSerializer):

    """Optimized serializer for tag lists."""



    usage_count = serializers.SerializerMethodField()



    class Meta:

        model = Tag

        fields = ["id", "name", "slug", "usage_count"]



    def get_usage_count(self, obj):

        # Use annotation if available

        if hasattr(obj, "usage_count"):

            return obj.usage_count

        return 0

