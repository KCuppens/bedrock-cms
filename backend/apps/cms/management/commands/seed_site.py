"""
Management command to seed the site with demo data.
"""

import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.i18n.models import Locale
from apps.cms.models import Page, Redirect
from apps.blog.models import BlogPost, Category, Tag
from apps.media.models import Asset


class Command(BaseCommand):
    help = "Seed the site with demo data for development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_data()

        self.stdout.write("Seeding demo data...")

        # Create locales
        locales = self.create_locales()
        en_locale = locales["en"]
        es_locale = locales["es"]

        # Create demo user
        user = self.create_demo_user()

        # Create sample assets
        assets = self.create_sample_assets(user)

        # Create page tree
        pages = self.create_page_tree(en_locale, es_locale, assets)

        # Create blog content
        blog_data = self.create_blog_content(en_locale, es_locale, user, assets, pages)

        # Create redirects
        self.create_sample_redirects(en_locale)

        self.stdout.write(self.style.SUCCESS(f"Demo data seeded successfully!"))
        self.show_summary(locales, pages, blog_data, assets)

    def clear_data(self):
        """Clear existing demo data."""
        self.stdout.write("Clearing existing data...")

        # Clear in dependency order
        BlogPost.objects.all().delete()
        Category.objects.all().delete()
        Tag.objects.all().delete()
        Page.objects.all().delete()
        Redirect.objects.all().delete()
        Asset.objects.all().delete()

        # Keep locales and users for safety
        self.stdout.write("Data cleared.")

    def create_locales(self):
        """Create demo locales."""
        self.stdout.write("Creating locales...")

        en_locale, created = Locale.objects.get_or_create(
            code="en-US",
            defaults={
                "name": "English (United States)",
                "native_name": "English",
                "language": "en",
                "region": "US",
                "is_default": True,
                "is_active": True,
                "rtl": False,
                "sort_order": 1,
            },
        )

        es_locale, created = Locale.objects.get_or_create(
            code="es-MX",
            defaults={
                "name": "Spanish (Mexico)",
                "native_name": "Español",
                "language": "es",
                "region": "MX",
                "fallback": en_locale,
                "is_active": True,
                "rtl": False,
                "sort_order": 2,
            },
        )

        return {"en": en_locale, "es": es_locale}

    def create_demo_user(self):
        """Create demo user."""
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@example.com",
                "first_name": "Demo",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            user.set_password("demo123")
            user.save()
            self.stdout.write("Created demo user: demo / demo123")

        return user

    def create_sample_assets(self, user):
        """Create sample media assets (placeholders)."""
        self.stdout.write("Creating sample assets...")

        assets = {}

        # Create placeholder assets (without actual files for demo)
        asset_configs = [
            ("hero-image.jpg", "image", 1920, 1080),
            ("about-team.jpg", "image", 800, 600),
            ("blog-featured.jpg", "image", 1200, 800),
            ("gallery-1.jpg", "image", 600, 400),
            ("gallery-2.jpg", "image", 600, 400),
        ]

        for filename, kind, width, height in asset_configs:
            asset, created = Asset.objects.get_or_create(
                checksum=f"demo_{filename}",
                defaults={
                    "file": f"demo/{filename}",  # Placeholder path
                    "kind": kind,
                    "width": width,
                    "height": height,
                    "size": 1024000,  # 1MB placeholder
                    "uploaded_by": user,
                    "alt_json": {
                        "en-US": f'Demo {filename.replace("-", " ").replace(".jpg", "")}',
                        "es-MX": f'Demo {filename.replace("-", " ").replace(".jpg", "")}',
                    },
                    "tags": ["demo", "placeholder"],
                },
            )
            assets[filename.split(".")[0].replace("-", "_")] = asset

        return assets

    def create_page_tree(self, en_locale, es_locale, assets):
        """Create sample page tree."""
        self.stdout.write("Creating page tree...")

        pages = {}

        # English pages
        home_en = Page.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="Welcome to Our Site",
            slug="",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "Welcome to Our Amazing Website",
                        "subtitle": "Discover what makes us special",
                        "background_image": (
                            assets["hero_image"].id if "hero_image" in assets else None
                        ),
                        "cta_text": "Learn More",
                        "cta_url": "/about/",
                    },
                },
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>Welcome to our website! We provide excellent services and solutions for our customers.</p><p>Explore our pages to learn more about what we do.</p>"
                    },
                },
                {
                    "type": "cta_band",
                    "schema_version": 1,
                    "props": {
                        "title": "Ready to Get Started?",
                        "subtitle": "Join thousands of satisfied customers",
                        "cta_text": "Contact Us",
                        "cta_url": "/contact/",
                        "background_color": "#f8f9fa",
                    },
                },
            ],
            seo={
                "title": "Home - Welcome to Our Site",
                "description": "Welcome to our amazing website. Discover our services and solutions.",
                "keywords": "home, welcome, services, solutions",
            },
        )
        pages["home_en"] = home_en

        about_en = Page.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="About Us",
            slug="about",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "About Our Company",
                        "subtitle": "Learn about our mission and values",
                    },
                },
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<h2>Our Story</h2><p>Founded in 2020, we have been dedicated to providing excellent services to our customers. Our team of professionals works tirelessly to ensure customer satisfaction.</p><h3>Our Mission</h3><p>To deliver innovative solutions that make a difference in our customers' lives.</p>"
                    },
                },
                {
                    "type": "image",
                    "schema_version": 1,
                    "props": {
                        "src": f"/media/demo/about-team.jpg",
                        "alt": "Our amazing team",
                        "caption": "Meet our dedicated team members",
                    },
                },
            ],
            seo={
                "title": "About Us - Our Company Story",
                "description": "Learn about our company, mission, and the team behind our success.",
                "keywords": "about, company, mission, team",
            },
        )
        pages["about_en"] = about_en

        services_en = Page.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="Our Services",
            slug="services",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "Our Services",
                        "subtitle": "Comprehensive solutions for your needs",
                    },
                },
                {
                    "type": "columns",
                    "schema_version": 1,
                    "props": {
                        "columns": ["33.33%", "33.33%", "33.33%"],
                        "gap": "lg",
                    },
                    "blocks": [
                        {
                            "type": "rich_text",
                            "schema_version": 1,
                            "props": {
                                "content": "<h3>Web Development</h3><p>Custom websites and applications built with modern technologies.</p>"
                            },
                        },
                        {
                            "type": "rich_text",
                            "schema_version": 1,
                            "props": {
                                "content": "<h3>Consulting</h3><p>Expert advice to help you make informed decisions.</p>"
                            },
                        },
                        {
                            "type": "rich_text",
                            "schema_version": 1,
                            "props": {
                                "content": "<h3>Support</h3><p>Ongoing support to keep your systems running smoothly.</p>"
                            },
                        },
                    ],
                },
            ],
        )
        pages["services_en"] = services_en

        contact_en = Page.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="Contact Us",
            slug="contact",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "Get In Touch",
                        "subtitle": "We'd love to hear from you",
                    },
                },
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>Ready to start your project? Have questions about our services? We're here to help!</p><h3>Contact Information</h3><ul><li>Email: hello@example.com</li><li>Phone: (555) 123-4567</li><li>Address: 123 Main St, City, ST 12345</li></ul>"
                    },
                },
            ],
        )
        pages["contact_en"] = contact_en

        # Spanish pages
        home_es = Page.objects.create(
            group_id=home_en.group_id,
            locale=es_locale,
            title="Bienvenido a Nuestro Sitio",
            slug="",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "Bienvenido a Nuestro Increíble Sitio Web",
                        "subtitle": "Descubre lo que nos hace especiales",
                        "background_image": (
                            assets["hero_image"].id if "hero_image" in assets else None
                        ),
                        "cta_text": "Saber Más",
                        "cta_url": "/acerca/",
                    },
                },
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>¡Bienvenido a nuestro sitio web! Proporcionamos excelentes servicios y soluciones para nuestros clientes.</p><p>Explora nuestras páginas para aprender más sobre lo que hacemos.</p>"
                    },
                },
            ],
            seo={
                "title": "Inicio - Bienvenido a Nuestro Sitio",
                "description": "Bienvenido a nuestro increíble sitio web. Descubre nuestros servicios y soluciones.",
                "keywords": "inicio, bienvenido, servicios, soluciones",
            },
        )
        pages["home_es"] = home_es

        about_es = Page.objects.create(
            group_id=about_en.group_id,
            locale=es_locale,
            title="Acerca de Nosotros",
            slug="acerca",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "hero",
                    "schema_version": 1,
                    "props": {
                        "title": "Acerca de Nuestra Empresa",
                        "subtitle": "Conoce nuestra misión y valores",
                    },
                },
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<h2>Nuestra Historia</h2><p>Fundada en 2020, nos hemos dedicado a brindar excelentes servicios a nuestros clientes. Nuestro equipo de profesionales trabaja incansablemente para garantizar la satisfacción del cliente.</p><h3>Nuestra Misión</h3><p>Entregar soluciones innovadoras que marquen la diferencia en la vida de nuestros clientes.</p>"
                    },
                },
            ],
        )
        pages["about_es"] = about_es

        return pages

    def create_blog_content(self, en_locale, es_locale, user, assets, pages):
        """Create sample blog content."""
        self.stdout.write("Creating blog content...")

        # Create categories
        tech_category = Category.objects.create(
            name="Technology",
            slug="technology",
            description="Posts about technology and innovation",
        )

        business_category = Category.objects.create(
            name="Business",
            slug="business",
            description="Business insights and strategies",
        )

        # Create tags
        django_tag, _ = Tag.objects.get_or_create(name="Django", slug="django")
        python_tag, _ = Tag.objects.get_or_create(name="Python", slug="python")
        web_tag, _ = Tag.objects.get_or_create(
            name="Web Development", slug="web-development"
        )
        startup_tag, _ = Tag.objects.get_or_create(name="Startup", slug="startup")
        tips_tag, _ = Tag.objects.get_or_create(name="Tips", slug="tips")

        # Create blog posts
        posts = []

        # Post 1 - English
        post1_en = BlogPost.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="Getting Started with Django CMS",
            slug="getting-started-django-cms",
            excerpt="Learn how to build powerful content management systems with Django.",
            hero_asset=assets.get("blog_featured"),
            category=tech_category,
            author="Demo Author",
            body_blocks=[
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>Django CMS is a powerful content management system built on the Django framework. In this post, we'll explore how to get started with building your own CMS.</p><h2>Why Choose Django CMS?</h2><p>Django CMS offers flexibility, scalability, and a robust architecture that makes it perfect for complex content management needs.</p>"
                    },
                },
                {
                    "type": "image",
                    "schema_version": 1,
                    "props": {
                        "src": "/media/demo/blog-featured.jpg",
                        "alt": "Django CMS Dashboard",
                        "caption": "The power of Django CMS at your fingertips",
                    },
                },
            ],
            status="published",
            published_at=timezone.now() - timedelta(days=5),
            seo={
                "title": "Getting Started with Django CMS - Complete Guide",
                "description": "Learn how to build powerful content management systems with Django. Complete beginner guide.",
                "keywords": "django, cms, python, web development, tutorial",
            },
        )
        post1_en.tags.set([django_tag, python_tag, web_tag])
        posts.append(post1_en)

        # Post 2 - English
        post2_en = BlogPost.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="5 Tips for Building Scalable Web Applications",
            slug="scalable-web-applications-tips",
            excerpt="Essential tips for creating web applications that can grow with your business.",
            category=business_category,
            author="Tech Expert",
            body_blocks=[
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>Building scalable web applications is crucial for long-term success. Here are our top 5 tips:</p><h2>1. Plan Your Architecture</h2><p>Start with a solid architectural foundation that can accommodate growth.</p><h2>2. Use Caching Strategically</h2><p>Implement caching layers to improve performance and reduce server load.</p>"
                    },
                }
            ],
            status="published",
            published_at=timezone.now() - timedelta(days=10),
        )
        post2_en.tags.set([web_tag, tips_tag, startup_tag])
        posts.append(post2_en)

        # Post 3 - Spanish
        post1_es = BlogPost.objects.create(
            group_id=post1_en.group_id,
            locale=es_locale,
            title="Comenzando con Django CMS",
            slug="comenzando-django-cms",
            excerpt="Aprende cómo construir sistemas de gestión de contenido poderosos con Django.",
            hero_asset=assets.get("blog_featured"),
            category=tech_category,
            author="Autor Demo",
            body_blocks=[
                {
                    "type": "rich_text",
                    "schema_version": 1,
                    "props": {
                        "content": "<p>Django CMS es un sistema de gestión de contenido poderoso construido sobre el framework Django. En este post, exploraremos cómo comenzar a construir tu propio CMS.</p><h2>¿Por qué elegir Django CMS?</h2><p>Django CMS ofrece flexibilidad, escalabilidad y una arquitectura robusta que lo hace perfecto para necesidades complejas de gestión de contenido.</p>"
                    },
                }
            ],
            status="published",
            published_at=timezone.now() - timedelta(days=5),
        )
        post1_es.tags.set([django_tag, python_tag, web_tag])
        posts.append(post1_es)

        # Create presentation page for blog
        blog_presentation = Page.objects.create(
            group_id=uuid.uuid4(),
            locale=en_locale,
            title="Blog Post Template",
            slug="blog-template",
            status="published",
            published_at=timezone.now(),
            blocks=[
                {
                    "type": "content_detail",
                    "schema_version": 1,
                    "props": {
                        "label": "blog.blogpost",
                        "source": "route",
                        "options": {
                            "show_toc": True,
                            "show_author": True,
                            "show_dates": True,
                            "show_share": True,
                            "show_reading_time": True,
                        },
                    },
                }
            ],
        )

        return {
            "posts": posts,
            "categories": [tech_category, business_category],
            "tags": [django_tag, python_tag, web_tag, startup_tag, tips_tag],
            "presentation_page": blog_presentation,
        }

    def create_sample_redirects(self, en_locale):
        """Create sample redirects."""
        self.stdout.write("Creating sample redirects...")

        redirects = [
            ("/old-about/", "/about/", 301),
            ("/old-contact/", "/contact/", 301),
            ("/legacy/services/", "/services/", 301),
            ("/blog/old-post/", "/blog/getting-started-django-cms/", 301),
        ]

        for from_path, to_path, status in redirects:
            Redirect.objects.get_or_create(
                from_path=from_path,
                locale=en_locale,
                defaults={
                    "to_path": to_path,
                    "status": status,
                },
            )

    def show_summary(self, locales, pages, blog_data, assets):
        """Show summary of created data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DEMO DATA SUMMARY")
        self.stdout.write("=" * 50)

        self.stdout.write(f"Locales: {len(locales)}")
        for code, locale in locales.items():
            self.stdout.write(f"  - {locale.name} ({locale.code})")

        self.stdout.write(f"\nPages: {len(pages)}")
        for key, page in pages.items():
            self.stdout.write(f"  - {page.title} ({page.locale.code}) - {page.path}")

        self.stdout.write(f'\nBlog Posts: {len(blog_data["posts"])}')
        for post in blog_data["posts"]:
            self.stdout.write(f"  - {post.title} ({post.locale.code})")

        self.stdout.write(f'\nCategories: {len(blog_data["categories"])}')
        for cat in blog_data["categories"]:
            self.stdout.write(f"  - {cat.name}")

        self.stdout.write(f"\nAssets: {len(assets)}")
        for name, asset in assets.items():
            self.stdout.write(f"  - {name}: {asset.file}")

        self.stdout.write("\nRedirects: 4 sample redirects created")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Ready for frontend development!")
        self.stdout.write("Demo user: demo / demo123")
        self.stdout.write("=" * 50)
