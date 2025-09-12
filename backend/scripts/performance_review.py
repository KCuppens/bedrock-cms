#!/usr/bin/env python
"""
Performance review script for Bedrock CMS.
Analyzes database queries, caching, API performance, and identifies bottlenecks.
"""

import json
import os
import statistics
import sys
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection, reset_queries
from django.test import Client
from django.utils import timezone

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.development")

import django

django.setup()

from apps.blog.models import BlogPost
from apps.cms.blocks.validation import validate_blocks
from apps.cms.models import Page
from apps.media.models import Asset


class PerformanceReviewer:
    """Comprehensive performance analysis for Bedrock CMS."""

    def __init__(self):
        self.results = {
            "database": {},
            "api": {},
            "caching": {},
            "blocks": {},
            "media": {},
            "recommendations": [],
        }
        self.client = Client()

    def run_full_review(self):
        """Run complete performance review."""
        print("🚀 Starting Comprehensive Performance Review")
        print("=" * 60)

        # Database performance
        print("\n📊 Analyzing Database Performance...")
        self.analyze_database_queries()

        # API performance
        print("\n🌐 Testing API Response Times...")
        self.analyze_api_performance()

        # Caching analysis
        print("\n💾 Reviewing Caching Implementation...")
        self.analyze_caching()

        # Block validation performance
        print("\n🧩 Testing Block Validation Performance...")
        self.analyze_block_performance()

        # Media handling
        print("\n🖼️ Analyzing Media Performance...")
        self.analyze_media_performance()

        # Generate recommendations
        print("\n💡 Generating Recommendations...")
        self.generate_recommendations()

        # Output results
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE REVIEW COMPLETE")
        print("=" * 60)
        self.output_results()

        return self.results

    def analyze_database_queries(self):
        """Analyze database query performance."""
        # Reset query log
        reset_queries()
        settings.DEBUG = True  # Enable query logging

        # Test 1: Page tree queries
        print("  • Testing page tree queries...")
        start_time = time.time()

        # Get all pages (potential N+1 issue)
        pages = list(Page.objects.all())
        for page in pages[:5]:  # Test first 5
            _ = page.parent
            _ = list(page.children.all())

        tree_time = time.time() - start_time
        tree_queries = len(connection.queries)

        reset_queries()

        # Test 2: Optimized page tree queries
        start_time = time.time()

        # Use select_related and prefetch_related
        pages_optimized = list(
            Page.objects.select_related("parent", "locale")
            .prefetch_related("children")
            .all()
        )
        for page in pages_optimized[:5]:
            _ = page.parent
            _ = list(page.children.all())

        tree_optimized_time = time.time() - start_time
        tree_optimized_queries = len(connection.queries)

        reset_queries()

        # Test 3: Blog post queries
        print("  • Testing blog post queries...")
        start_time = time.time()

        posts = list(BlogPost.objects.all())
        for post in posts[:5]:
            _ = post.category
            _ = list(post.tags.all())

        blog_time = time.time() - start_time
        blog_queries = len(connection.queries)

        reset_queries()

        # Test 4: Optimized blog queries
        start_time = time.time()

        posts_optimized = list(
            BlogPost.objects.select_related("category", "locale")
            .prefetch_related("tags")
            .all()
        )
        for post in posts_optimized[:5]:
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

        print(f"    ✓ Page tree: {tree_queries} → {tree_optimized_queries} queries")
        print(f"    ✓ Blog posts: {blog_queries} → {blog_optimized_queries} queries")

        settings.DEBUG = False  # Disable query logging

    def analyze_api_performance(self):
        """Test API endpoint performance."""
        endpoints = [
            ("GET", "/api/pages/", "Page List"),
            ("GET", "/api/pages/1/", "Page Detail"),
            ("GET", "/api/content/blog.blogpost/", "Blog List"),
            ("GET", "/api/media/assets/", "Media List"),
            ("GET", "/api/search?q=test", "Search"),
        ]

        api_results = {}

        for method, endpoint, name in endpoints:
            print(f"  • Testing {name} ({endpoint})")
            times = []

            # Run multiple tests for average
            for _ in range(5):
                start_time = time.time()
                try:
                    if method == "GET":
                        response = self.client.get(endpoint)
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    times.append(response_time)
                except Exception as e:
                    print(f"    ⚠️  Error testing {endpoint}: {e}")
                    times.append(0)

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
                    "✅" if avg_time < 100 else "⚠️" if avg_time < 500 else "🔴"
                )
                print(
                    f"    {status_icon} Avg: {avg_time:.1f}ms, Range: {min_time:.1f}-{max_time:.1f}ms"
                )

        self.results["api"] = api_results

    def analyze_caching(self):
        """Analyze caching implementation and performance."""
        print("  • Testing cache performance...")

        cache_results = {
            "redis_available": False,
            "cache_backend": str(settings.CACHES["default"]["BACKEND"]),
            "operations": {},
        }

        # Test cache operations
        test_data = {"test": "data", "timestamp": timezone.now().isoformat()}

        # Set operation
        start_time = time.time()
        cache.set("perf_test_key", test_data, 300)
        set_time = (time.time() - start_time) * 1000

        # Get operation
        start_time = time.time()
        cached_data = cache.get("perf_test_key")
        get_time = (time.time() - start_time) * 1000

        # Delete operation
        start_time = time.time()
        cache.delete("perf_test_key")
        delete_time = (time.time() - start_time) * 1000

        cache_results["operations"] = {
            "set_time_ms": round(set_time, 3),
            "get_time_ms": round(get_time, 3),
            "delete_time_ms": round(delete_time, 3),
            "data_integrity": cached_data == test_data,
        }

        # Check if using Redis
        if "redis" in cache_results["cache_backend"].lower():
            cache_results["redis_available"] = True

        self.results["caching"] = cache_results

        print(f"    ✓ Backend: {cache_results['cache_backend'].split('.')[-1]}")
        print(
            f"    ✓ Set: {set_time:.2f}ms, Get: {get_time:.2f}ms, Delete: {delete_time:.2f}ms"
        )

    def analyze_block_performance(self):
        """Test block validation performance with various sizes."""
        print("  • Testing block validation performance...")

        # Test different block counts
        test_cases = [10, 25, 50, 100]
        block_results = {}

        for count in test_cases:
            print(f"    • Testing {count} blocks...")

            # Generate test blocks
            blocks = []
            for i in range(count):
                block_type = ["rich_text", "hero", "image", "cta_band"][i % 4]
                blocks.append(
                    {
                        "type": block_type,
                        "schema_version": 1,
                        "props": {
                            "title": f"Test Block {i}",
                            "content": f"Content for block {i}"
                            * 10,  # Make it substantial
                        },
                    }
                )

            # Time validation
            times = []
            for _ in range(3):  # Run 3 times for average
                start_time = time.time()
                try:
                    validated = validate_blocks(blocks)
                    validation_time = (time.time() - start_time) * 1000
                    times.append(validation_time)
                except Exception as e:
                    print(f"      ⚠️  Error validating blocks: {e}")
                    times.append(0)

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
                    "✅" if avg_time < 200 else "⚠️" if avg_time < 1000 else "🔴"
                )
                print(
                    f"      {status_icon} {avg_time:.1f}ms total, {avg_time / count:.2f}ms per block"
                )

        self.results["blocks"] = block_results

    def analyze_media_performance(self):
        """Analyze media handling performance."""
        print("  • Testing media operations...")

        media_results = {
            "storage_backend": str(settings.DEFAULT_FILE_STORAGE),
            "operations": {},
        }

        # Test asset queries
        start_time = time.time()
        assets = list(Asset.objects.all()[:10])
        query_time = (time.time() - start_time) * 1000

        # Test asset with renditions
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

        print(f"    ✓ Storage: {media_results['storage_backend'].split('.')[-1]}")
        print(f"    ✓ Asset queries: {query_time:.1f}ms → {optimized_query_time:.1f}ms")

    def generate_recommendations(self):
        """Generate performance recommendations based on analysis."""
        recommendations = []

        # Database recommendations
        db_results = self.results.get("database", {})

        if db_results.get("page_tree", {}).get("naive", {}).get("queries", 0) > 5:
            recommendations.append(
                {
                    "category": "Database",
                    "severity": "high",
                    "issue": "N+1 queries in page tree traversal",
                    "solution": 'Use select_related("parent") and prefetch_related("children") for page queries',
                    "impact": "High - Reduces database load significantly",
                }
            )

        if db_results.get("blog_posts", {}).get("naive", {}).get("queries", 0) > 5:
            recommendations.append(
                {
                    "category": "Database",
                    "severity": "medium",
                    "issue": "Inefficient blog post queries",
                    "solution": 'Use select_related("category", "locale") and prefetch_related("tags")',
                    "impact": "Medium - Improves blog listing performance",
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
            recommendations.append(
                {
                    "category": "API",
                    "severity": "medium",
                    "issue": f"Slow API endpoints: {', '.join(slow_apis)}",
                    "solution": "Add caching, optimize queries, consider pagination",
                    "impact": "Medium - Improves user experience",
                }
            )

        # Caching recommendations
        cache_results = self.results.get("caching", {})
        if not cache_results.get("redis_available", False):
            recommendations.append(
                {
                    "category": "Caching",
                    "severity": "medium",
                    "issue": "Using database/filesystem cache instead of Redis",
                    "solution": "Configure Redis for better cache performance",
                    "impact": "Medium - Significantly faster cache operations",
                }
            )

        # Block validation recommendations
        block_results = self.results.get("blocks", {})
        slow_blocks = [
            count
            for count, data in block_results.items()
            if data.get("avg_time_ms", 0) > 500
        ]

        if slow_blocks:
            recommendations.append(
                {
                    "category": "Block Validation",
                    "severity": "low",
                    "issue": f"Slow block validation for large counts: {slow_blocks}",
                    "solution": "Consider async validation or chunked processing for large block sets",
                    "impact": "Low - Affects only very large pages",
                }
            )

        # General recommendations
        recommendations.extend(
            [
                {
                    "category": "Database",
                    "severity": "medium",
                    "issue": "Missing database indexes on frequently queried fields",
                    "solution": "Add indexes on Page.path, Page.group_id, BlogPost.slug, Asset.checksum",
                    "impact": "High - Faster lookups and filtering",
                },
                {
                    "category": "Static Files",
                    "severity": "low",
                    "issue": "Static files served by Django in development",
                    "solution": "Use CDN or nginx for static files in production",
                    "impact": "High - Reduces server load and improves asset delivery",
                },
                {
                    "category": "Sessions",
                    "severity": "low",
                    "issue": "Database sessions may not be optimal for high traffic",
                    "solution": "Consider Redis or cache-based sessions for production",
                    "impact": "Medium - Reduces database load",
                },
            ]
        )

        self.results["recommendations"] = recommendations

    def output_results(self):
        """Output comprehensive results."""

        # Database Performance
        print("\n📊 DATABASE PERFORMANCE")
        print("-" * 30)
        db = self.results["database"]

        if "page_tree" in db:
            pt = db["page_tree"]
            print("Page Tree Queries:")
            print(
                f"  • Naive: {pt['naive']['queries']} queries, {pt['naive']['time'] * 1000:.1f}ms"
            )
            print(
                f"  • Optimized: {pt['optimized']['queries']} queries, {pt['optimized']['time'] * 1000:.1f}ms"
            )
            print(f"  • Improvement: {pt['improvement']}")

        if "blog_posts" in db:
            bp = db["blog_posts"]
            print("Blog Post Queries:")
            print(
                f"  • Naive: {bp['naive']['queries']} queries, {bp['naive']['time'] * 1000:.1f}ms"
            )
            print(
                f"  • Optimized: {bp['optimized']['queries']} queries, {bp['optimized']['time'] * 1000:.1f}ms"
            )
            print(f"  • Improvement: {bp['improvement']}")

        # API Performance
        print("\n🌐 API PERFORMANCE")
        print("-" * 20)
        for name, data in self.results["api"].items():
            status_icon = (
                "✅"
                if data["status"] == "good"
                else "⚠️" if data["status"] == "warning" else "🔴"
            )
            print(
                f"{status_icon} {name}: {data['avg_time_ms']}ms avg ({data['min_time_ms']}-{data['max_time_ms']}ms)"
            )

        # Caching
        print("\n💾 CACHING")
        print("-" * 10)
        cache = self.results["caching"]
        print(f"Backend: {cache['cache_backend'].split('.')[-1]}")
        print(f"Redis Available: {'Yes' if cache['redis_available'] else 'No'}")
        ops = cache["operations"]
        print(
            f"Operations: Set {ops['set_time_ms']}ms, Get {ops['get_time_ms']}ms, Delete {ops['delete_time_ms']}ms"
        )

        # Block Validation
        print("\n🧩 BLOCK VALIDATION")
        print("-" * 20)
        for count, data in self.results["blocks"].items():
            status_icon = (
                "✅"
                if data["status"] == "good"
                else "⚠️" if data["status"] == "warning" else "🔴"
            )
            print(
                f"{status_icon} {count} blocks: {data['avg_time_ms']}ms total, {data['per_block_ms']}ms per block"
            )

        # Media Performance
        print("\n🖼️ MEDIA PERFORMANCE")
        print("-" * 18)
        media = self.results["media"]
        print(f"Storage: {media['storage_backend'].split('.')[-1]}")
        ops = media["operations"]
        print(
            f"Asset Queries: {ops['asset_query_ms']}ms → {ops['optimized_query_ms']}ms ({ops['improvement']} improvement)"
        )

        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 17)
        for i, rec in enumerate(self.results["recommendations"], 1):
            severity_icon = (
                "🔴"
                if rec["severity"] == "high"
                else "🟡" if rec["severity"] == "medium" else "🟢"
            )
            print(f"\n{i}. {severity_icon} [{rec['category']}] {rec['issue']}")
            print(f"   Solution: {rec['solution']}")
            print(f"   Impact: {rec['impact']}")

        # Performance Score
        self.calculate_performance_score()

    def calculate_performance_score(self):
        """Calculate overall performance score."""
        score = 100

        # Deduct for slow APIs
        api_results = self.results.get("api", {})
        for name, data in api_results.items():
            if data.get("avg_time_ms", 0) > 500:
                score -= 15
            elif data.get("avg_time_ms", 0) > 200:
                score -= 5

        # Deduct for inefficient queries
        db_results = self.results.get("database", {})
        if db_results.get("page_tree", {}).get("naive", {}).get("queries", 0) > 10:
            score -= 10
        if db_results.get("blog_posts", {}).get("naive", {}).get("queries", 0) > 10:
            score -= 5

        # Deduct for slow block validation
        block_results = self.results.get("blocks", {})
        for count, data in block_results.items():
            if data.get("avg_time_ms", 0) > 1000:
                score -= 5

        # Bonus for Redis
        if self.results.get("caching", {}).get("redis_available", False):
            score += 5

        score = max(0, min(100, score))  # Clamp between 0-100

        print(f"\n🎯 OVERALL PERFORMANCE SCORE: {score}/100")

        if score >= 90:
            print("   Excellent! Your CMS is highly optimized.")
        elif score >= 75:
            print("   Good performance with room for minor improvements.")
        elif score >= 60:
            print("   Decent performance, consider implementing recommendations.")
        else:
            print("   Performance needs attention. Please review recommendations.")

        self.results["performance_score"] = score


def main():
    """Main function to run performance review."""
    reviewer = PerformanceReviewer()
    results = reviewer.run_full_review()

    # Save results to file
    output_file = "performance_review_results.json"
    with open(output_file, "w") as f:
        # Convert datetime objects to strings for JSON serialization
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to: {output_file}")
    return results


if __name__ == "__main__":
    main()
