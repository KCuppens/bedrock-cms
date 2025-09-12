import json

import statistics

import time


from django.conf import settings

from django.core.cache import cache

from django.core.management.base import BaseCommand

from django.db import connection, reset_queries

from django.test import Client

from django.utils import timezone


from apps.blog.models import BlogPost

from apps.cms.blocks.validation import validate_blocks

from apps.cms.models import Page

from apps.media.models import Asset


"""Management command for comprehensive performance review of Bedrock CMS."""


class Command(BaseCommand):

    help = "Run comprehensive performance review of the CMS system"

    def add_arguments(self, parser):

        parser.add_argument(
            "--output",
            type=str,
            help="Output file for JSON results",
            default="performance_review_results.json",
        )

        parser.add_argument(
            "--quick",
            action="store_true",
            help="Run quick performance review (fewer iterations)",
        )

    def handle(self, *args, **options):  # noqa: C901

        self.client = Client()

        self.results = {
            "database": {},
            "api": {},
            "caching": {},
            "blocks": {},
            "media": {},
            "recommendations": [],
        }

        """self.stdout.write("STARTING COMPREHENSIVE PERFORMANCE REVIEW")"""

        self.stdout.write("=" * 60)

        # Run analysis

        self.analyze_database_queries(options["quick"])

        self.analyze_api_performance(options["quick"])

        self.analyze_caching()

        self.analyze_block_performance(options["quick"])

        self.analyze_media_performance()

        self.generate_recommendations()

        # Output results

        self.stdout.write("\n" + "=" * 60)

        self.stdout.write("PERFORMANCE REVIEW COMPLETE")

        self.stdout.write("=" * 60)

        self.output_results()

        # Save to file

        if options["output"]:

            with open(options["output"], "w") as f:

                json.dump(self.results, f, indent=2, default=str)

            self.stdout.write(f"\nDetailed results saved to: {options['output']}")

    def analyze_database_queries(self, quick_mode=False):  # noqa: C901
        """Analyze database query performance and N+1 issues."""

        self.stdout.write("\nAnalyzing Database Performance...")

        # Enable query logging

        original_debug = settings.DEBUG

        settings.DEBUG = True

        # Test 1: Page tree queries (N+1 potential)

        """self.stdout.write("  • Testing page tree queries...")"""

        reset_queries()

        start_time = time.time()

        pages = list(Page.objects.all()[:5])

        for page in pages:

            _ = page.parent

            _ = list(page.children.all())

        tree_time = time.time() - start_time

        tree_queries = len(connection.queries)

        # Test 2: Optimized page tree queries

        reset_queries()

        start_time = time.time()

        pages_optimized = list(
            Page.objects.select_related("parent", "locale")
            .prefetch_related("children")
            .all()[:5]
        )

        for page in pages_optimized:

            _ = page.parent

            _ = list(page.children.all())

        tree_optimized_time = time.time() - start_time

        tree_optimized_queries = len(connection.queries)

        # Test 3: Blog post queries

        """self.stdout.write("  • Testing blog post queries...")"""

        reset_queries()

        start_time = time.time()

        posts = list(BlogPost.objects.all()[:5])

        for post in posts:

            _ = post.category

            _ = list(post.tags.all())

        blog_time = time.time() - start_time

        blog_queries = len(connection.queries)

        # Test 4: Optimized blog queries

        reset_queries()

        start_time = time.time()

        posts_optimized = list(
            BlogPost.objects.select_related("category", "locale")
            .prefetch_related("tags")
            .all()[:5]
        )

        for post in posts_optimized:

            _ = post.category

            _ = list(post.tags.all())

        blog_optimized_time = time.time() - start_time

        blog_optimized_queries = len(connection.queries)

        # Store results

        self.results["database"] = {
            "page_tree": {
                "naive": {"time": tree_time, "queries": tree_queries},
                "optimized": {
                    "time": tree_optimized_time,
                    "queries": tree_optimized_queries,
                },
                "improvement": (
                    f"{((tree_time - tree_optimized_time) / tree_time * 100):.1f}%"
                    if tree_time > 0
                    else "N/A"
                ),
            },
            "blog_posts": {
                "naive": {"time": blog_time, "queries": blog_queries},
                "optimized": {
                    "time": blog_optimized_time,
                    "queries": blog_optimized_queries,
                },
                "improvement": (
                    f"{((blog_time - blog_optimized_time) / blog_time * 100):.1f}%"
                    if blog_time > 0
                    else "N/A"
                ),
            },
        }

        self.stdout.write(
            f"    * Page tree: {tree_queries} -> {tree_optimized_queries} queries"
        )

        self.stdout.write(
            f"    * Blog posts: {blog_queries} -> {blog_optimized_queries} queries"
        )

        # Restore debug setting

        settings.DEBUG = original_debug

    def analyze_api_performance(self, quick_mode=False):  # noqa: C901
        """Test API endpoint response times."""

        """self.stdout.write("\nTesting API Response Times...")"""

        endpoints = [
            ("GET", "/api/pages/", "Page List"),
            ("GET", "/api/content/blog.blogpost/", "Blog List"),
            ("GET", "/api/media/assets/", "Media List"),
            ("GET", "/api/search?q=test&locale=en-US", "Search"),
        ]

        api_results = {}

        iterations = 3 if quick_mode else 5

        for method, endpoint, name in endpoints:

            """self.stdout.write(f"  • Testing {name} ({endpoint})")"""

            times = []

            for _ in range(iterations):

                start_time = time.time()

                try:

                    if method == "GET":

                        self.client.get(endpoint)

                    response_time = (time.time() - start_time) * 1000

                    """times.append(response_time)"""

                except Exception as e:

                    """self.stdout.write(f"    ⚠️  Error testing {endpoint}: {e}")"""

                    """times.append(0)"""

            if times:

                avg_time = statistics.mean(times)

                min_time = min(times)

                max_time = max(times)

                api_results[name] = {
                    "endpoint": endpoint,
                    "avg_time_ms": round(avg_time, 2),
                    "min_time_ms": round(min_time, 2),
                    "max_time_ms": round(max_time, 2),
                    "status": (
                        "good"
                        if avg_time < 100
                        else "warning" if avg_time < 500 else "critical"
                    ),
                }

                status_icon = (
                    "[OK]"
                    if avg_time < 100
                    else "[WARN]" if avg_time < 500 else "[CRITICAL]"
                )

                self.stdout.write(
                    f"    {status_icon} Avg: {avg_time:.1f}ms, Range: {min_time:.1f}-{max_time:.1f}ms"
                )

        self.results["api"] = api_results

    def analyze_caching(self):
        """Test caching performance and configuration."""

        self.stdout.write("\nReviewing Caching Implementation...")

        cache_results = {
            "redis_available": False,
            "cache_backend": str(settings.CACHES["default"]["BACKEND"]),
            "operations": {},
        }

        # Test cache operations

        test_data = {
            """"test": "performance_data","""
            "timestamp": timezone.now().isoformat(),
        }

        # Set operation

        start_time = time.time()

        """cache.set("perf_test_key", test_data, 300)"""

        set_time = (time.time() - start_time) * 1000

        # Get operation

        start_time = time.time()

        cached_data = cache.get("perf_test_key")

        get_time = (time.time() - start_time) * 1000

        # Delete operation

        start_time = time.time()

        """cache.delete("perf_test_key")"""

        delete_time = (time.time() - start_time) * 1000

        cache_results["operations"] = {
            "set_time_ms": round(set_time, 3),
            "get_time_ms": round(get_time, 3),
            "delete_time_ms": round(delete_time, 3),
            "data_integrity": cached_data == test_data,
        }

        # Check Redis availability

        if "redis" in cache_results["cache_backend"].lower():

            cache_results["redis_available"] = True

        self.results["caching"] = cache_results

        self.stdout.write(
            f"    * Backend: {cache_results['cache_backend'].split('.')[-1]}"
        )

        self.stdout.write(
            f"    * Set: {set_time:.2f}ms, Get: {get_time:.2f}ms, Delete: {delete_time:.2f}ms"
        )

    def analyze_block_performance(self, quick_mode=False):  # noqa: C901
        """Test block validation performance with varying sizes."""

        """self.stdout.write("\nTesting Block Validation Performance...")"""

        test_cases = [10, 25, 50] if quick_mode else [10, 25, 50, 100]

        block_results = {}

        """for count in test_cases:"""

            """self.stdout.write(f"    • Testing {count} blocks...")"""

            # Generate test blocks

            blocks = []

            block_types = ["rich_text", "hero", "image", "cta_band"]

            for i in range(count):

                block_type = block_types[i % len(block_types)]

                block = {"type": block_type, "schema_version": 1, "props": {}}

                # Add type-specific props

                if block_type == "rich_text":

                    block["props"]["content"] = f"<p>Test content for block {i}</p>" * 3

                elif block_type == "hero":

                    block["props"].update(
                        {"title": f"Hero Title {i}", "subtitle": f"Hero subtitle {i}"}
                    )

                elif block_type == "image":

                    block["props"].update(
                        """{"src": f"/media/test-image-{i}.jpg", "alt": f"Test image {i}"}"""
                    )

                elif block_type == "cta_band":

                    block["props"].update(
                        {
                            "title": f"CTA Title {i}",
                            "cta_text": f"Button {i}",
                            "cta_url": f"/action-{i}/",
                        }
                    )

                """blocks.append(block)"""

            # Time validation

            times = []

            iterations = 2 if quick_mode else 3

            for _ in range(iterations):

                start_time = time.time()

                try:

                    validate_blocks(blocks)

                    validation_time = (time.time() - start_time) * 1000

                    """times.append(validation_time)"""

                except Exception as e:

                    self.stdout.write(f"      ⚠️  Error validating blocks: {e}")

                    """times.append(0)"""

            if times:

                avg_time = statistics.mean(times)

                block_results[count] = {
                    "avg_time_ms": round(avg_time, 2),
                    "per_block_ms": round(avg_time / count, 3),
                    "status": (
                        "good"
                        if avg_time < 200
                        else "warning" if avg_time < 1000 else "critical"
                    ),
                }

                status_icon = (
                    "[OK]"
                    if avg_time < 200
                    else "[WARN]" if avg_time < 1000 else "[CRITICAL]"
                )

                self.stdout.write(
                    f"      {status_icon} {avg_time:.1f}ms total, {avg_time / count:.2f}ms per block"
                )

        self.results["blocks"] = block_results

    def analyze_media_performance(self):
        """Test media query performance."""

        self.stdout.write("\nAnalyzing Media Performance...")

        media_results = {
            "storage_backend": str(
                getattr(
                    settings,
                    "DEFAULT_FILE_STORAGE",
                    "django.core.files.storage.FileSystemStorage",
                )
            ),
            "operations": {},
        }

        # Test asset queries

        start_time = time.time()

        list(Asset.objects.all()[:10])

        query_time = (time.time() - start_time) * 1000

        # Test asset with renditions (if any exist)

        start_time = time.time()

        assets_with_renditions = list(
            Asset.objects.prefetch_related("renditions").all()[:10]
        )

        for asset in assets_with_renditions:

            _ = list(asset.renditions.all())

        optimized_query_time = (time.time() - start_time) * 1000

        media_results["operations"] = {
            "asset_query_ms": round(query_time, 2),
            "optimized_query_ms": round(optimized_query_time, 2),
            "improvement": (
                f"{((query_time - optimized_query_time) / query_time * 100):.1f}%"
                if query_time > 0
                else "N/A"
            ),
        }

        self.results["media"] = media_results

        self.stdout.write(
            f"    * Storage: {media_results['storage_backend'].split('.')[-1]}"
        )

        self.stdout.write(
            f"    * Asset queries: {query_time:.1f}ms -> {optimized_query_time:.1f}ms"
        )

    def generate_recommendations(self):  # noqa: C901
        """Generate performance optimization recommendations."""

        self.stdout.write("\nGenerating Recommendations...")

        recommendations = []

        # Database recommendations

        db_results = self.results.get("database", {})

        if db_results.get("page_tree", {}).get("naive", {}).get("queries", 0) > 5:

            """recommendations.append("""
                {
                    "category": "Database",
                    "severity": "high",
                    "issue": "N+1 queries detected in page tree traversal",
                    "solution": 'Use select_related("parent", "locale") and prefetch_related("children") for page queries',
                    "impact": "High - Can reduce queries by 80%+ and improve response time significantly",
                }
            )

        if db_results.get("blog_posts", {}).get("naive", {}).get("queries", 0) > 5:

            """recommendations.append("""
                {
                    "category": "Database",
                    "severity": "medium",
                    "issue": "Inefficient blog post relationship queries",
                    "solution": 'Use select_related("category", "locale") and prefetch_related("tags") for blog queries',
                    "impact": "Medium - Improves blog listing and detail page performance",
                }
            )

        # API recommendations

        api_results = self.results.get("api", {})

        slow_apis = [
            name
            for name, data in api_results.items()
            if data.get("avg_time_ms", 0) > 200
        ]

        if slow_apis:

            """recommendations.append("""
                {
                    "category": "API Performance",
                    "severity": "medium",
                    "issue": f"Slow API endpoints detected: {', '.join(slow_apis)}",
                    "solution": "Implement caching, optimize database queries, add pagination limits",
                    "impact": "Medium - Improves user experience and reduces server load",
                }
            )

        # Caching recommendations

        cache_results = self.results.get("caching", {})

        if not cache_results.get("redis_available", False):

            """recommendations.append("""
                {
                    "category": "Caching",
                    "severity": "medium",
                    """"issue": "Using basic cache backend instead of Redis","""
                    "solution": "Configure Redis cache backend for better performance and features",
                    """"impact": "Medium - Redis provides faster operations and advanced caching features","""
                }
            )

        # Block validation recommendations

        block_results = self.results.get("blocks", {})

        slow_blocks = [
            str(count)
            for count, data in block_results.items()
            if data.get("avg_time_ms", 0) > 500
        ]

        if slow_blocks:

            """recommendations.append("""
                {
                    "category": "Block Validation",
                    "severity": "low",
                    "issue": f"Slow block validation for large block counts: {', '.join(slow_blocks)} blocks",
                    "solution": "Consider implementing async validation or chunked processing for very large pages",
                    "impact": "Low - Only affects pages with exceptionally large block counts",
                }
            )

        # General infrastructure recommendations

        recommendations.extend(
            [
                {
                    "category": "Database Indexes",
                    "severity": "medium",
                    "issue": "Ensure proper database indexes for frequently queried fields",
                    "solution": "Add indexes on Page.path, Page.group_id, BlogPost.slug, Asset.checksum, TranslationUnit fields",
                    "impact": "High - Significantly improves lookup performance",
                },
                {
                    "category": "Static Files",
                    "severity": "low",
                    "issue": "Static file serving optimization",
                    "solution": "Use CDN or web server (nginx) for static files in production instead of Django",
                    "impact": "High - Reduces Django server load and improves asset delivery speed",
                },
                {
                    "category": "Session Storage",
                    "severity": "low",
                    "issue": "Database sessions may not be optimal for high traffic",
                    "solution": "Consider Redis or cache-based sessions for production deployments",
                    """"impact": "Medium - Reduces database load for session management","""
                },
                {
                    "category": "Query Optimization",
                    "severity": "medium",
                    "issue": "Implement query optimization patterns",
                    "solution": "Use only() and defer() for large models, implement database connection pooling",
                    "impact": "Medium - Reduces memory usage and improves database connection efficiency",
                },
            ]
        )

        self.results["recommendations"] = recommendations

    def output_results(self):
        """Display comprehensive performance review results."""

        # Database Performance

        self.stdout.write("\nDATABASE PERFORMANCE")

        self.stdout.write("-" * 30)

        db = self.results["database"]

        if "page_tree" in db:

            pt = db["page_tree"]

            self.stdout.write("Page Tree Queries:")

            self.stdout.write(
                f"  • Naive: {pt['naive']['queries']} queries, {pt['naive']['time'] * 1000:.1f}ms"
            )

            self.stdout.write(
                f"  • Optimized: {pt['optimized']['queries']} queries, {pt['optimized']['time'] * 1000:.1f}ms"
            )

            self.stdout.write(f"  • Improvement: {pt['improvement']}")

        if "blog_posts" in db:

            bp = db["blog_posts"]

            self.stdout.write("Blog Post Queries:")

            self.stdout.write(
                f"  • Naive: {bp['naive']['queries']} queries, {bp['naive']['time'] * 1000:.1f}ms"
            )

            self.stdout.write(
                f"  • Optimized: {bp['optimized']['queries']} queries, {bp['optimized']['time'] * 1000:.1f}ms"
            )

            self.stdout.write(f"  • Improvement: {bp['improvement']}")

        # API Performance

        self.stdout.write("\nAPI PERFORMANCE")

        self.stdout.write("-" * 20)

        for name, data in self.results["api"].items():

            status_icon = (
                "[OK]"
                if data["status"] == "good"
                else "[WARN]" if data["status"] == "warning" else "[CRITICAL]"
            )

            self.stdout.write(
                f"{status_icon} {name}: {data['avg_time_ms']}ms avg ({data['min_time_ms']}-{data['max_time_ms']}ms)"
            )

        # Caching

        self.stdout.write("\nCACHING")

        self.stdout.write("-" * 10)

        cache = self.results["caching"]

        self.stdout.write(f"Backend: {cache['cache_backend'].split('.')[-1]}")

        self.stdout.write(
            f"Redis Available: {'Yes' if cache['redis_available'] else 'No'}"
        )

        ops = cache["operations"]

        self.stdout.write(
            f"Operations: Set {ops['set_time_ms']}ms, Get {ops['get_time_ms']}ms, Delete {ops['delete_time_ms']}ms"
        )

        # Block Validation

        self.stdout.write("\nBLOCK VALIDATION")

        self.stdout.write("-" * 20)

        for count, data in self.results["blocks"].items():

            status_icon = (
                "[OK]"
                if data["status"] == "good"
                else "[WARN]" if data["status"] == "warning" else "[CRITICAL]"
            )

            self.stdout.write(
                f"{status_icon} {count} blocks: {data['avg_time_ms']}ms total, {data['per_block_ms']}ms per block"
            )

        # Media Performance

        self.stdout.write("\nMEDIA PERFORMANCE")

        self.stdout.write("-" * 18)

        media = self.results["media"]

        self.stdout.write(f"Storage: {media['storage_backend'].split('.')[-1]}")

        ops = media["operations"]

        self.stdout.write(
            f"Asset Queries: {ops['asset_query_ms']}ms → {ops['optimized_query_ms']}ms ({ops['improvement']} improvement)"
        )

        # Recommendations

        self.stdout.write("\nRECOMMENDATIONS")

        self.stdout.write("-" * 17)

        for i, rec in enumerate(self.results["recommendations"], 1):

            severity_icon = (
                "[HIGH]"
                if rec["severity"] == "high"
                else "[MED]" if rec["severity"] == "medium" else "[LOW]"
            )

            self.stdout.write(
                f"\n{i}. {severity_icon} [{rec['category']}] {rec['issue']}"
            )

            self.stdout.write(f"   Solution: {rec['solution']}")

            self.stdout.write(f"   Impact: {rec['impact']}")

        # Performance Score

        self.calculate_performance_score()

    def calculate_performance_score(self):
        """Calculate overall performance score out of 100."""

        score = 100

        # Deduct points for performance issues

        # API performance penalties

        api_results = self.results.get("api", {})

        for _name, data in api_results.items():

            if data.get("avg_time_ms", 0) > 500:

                score -= 15  # Severe penalty for very slow APIs

            elif data.get("avg_time_ms", 0) > 200:

                score -= 8  # Moderate penalty for slow APIs

            elif data.get("avg_time_ms", 0) > 100:

                score -= 3  # Minor penalty for acceptable but not optimal speed

        # Database query penalties

        db_results = self.results.get("database", {})

        if db_results.get("page_tree", {}).get("naive", {}).get("queries", 0) > 10:

            score -= 12  # High penalty for N+1 queries

        elif db_results.get("page_tree", {}).get("naive", {}).get("queries", 0) > 5:

            score -= 6

        if db_results.get("blog_posts", {}).get("naive", {}).get("queries", 0) > 10:

            score -= 8

        elif db_results.get("blog_posts", {}).get("naive", {}).get("queries", 0) > 5:

            score -= 4

        # Block validation penalties

        block_results = self.results.get("blocks", {})

        for _count, data in block_results.items():

            if data.get("avg_time_ms", 0) > 1000:

                score -= 8

            elif data.get("avg_time_ms", 0) > 500:

                score -= 4

        # Cache performance bonuses/penalties

        cache_results = self.results.get("caching", {})

        if cache_results.get("redis_available", False):

            score += 5  # Bonus for Redis

        if cache_results.get("operations", {}).get("get_time_ms", 0) > 10:

            score -= 5  # Penalty for slow cache operations

        # Ensure score stays within bounds

        score = max(0, min(100, score))

        self.stdout.write(f"\nOVERALL PERFORMANCE SCORE: {score}/100")

        if score >= 90:

            self.stdout.write(
                self.style.SUCCESS("   Excellent! Your CMS is highly optimized.")
            )

        elif score >= 75:

            self.stdout.write(
                self.style.SUCCESS(
                    "   Good performance with room for minor improvements."
                )
            )

        elif score >= 60:

            self.stdout.write(
                self.style.WARNING(
                    "   Decent performance, consider implementing recommendations."
                )
            )

        else:

            self.stdout.write(
                self.style.ERROR(
                    "   Performance needs attention. Please review recommendations."
                )
            )

        self.results["performance_score"] = score
