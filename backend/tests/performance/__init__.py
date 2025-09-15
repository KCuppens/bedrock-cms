"""
Performance testing framework for Bedrock CMS.

This module provides comprehensive performance testing utilities including:
- Performance benchmarking decorators
- Database query counting and optimization verification
- Memory usage monitoring
- Response time measurement
- Load testing capabilities
- Performance regression detection
"""

from .fixtures import (
    PerformanceDataFixtures,
    cleanup_performance_data,
    create_bulk_blog_posts,
    create_bulk_pages,
    create_bulk_translations,
    create_multilingual_content,
    create_test_users,
)
from .utils import (
    PERFORMANCE_THRESHOLDS,
    DatabaseQueryCounter,
    MemoryProfiler,
    PerformanceBenchmark,
    ResponseTimeTracker,
    cache_performance,
    memory_usage_limit,
    performance_benchmark,
    query_count_limit,
    response_time_limit,
)

__all__ = [
    # Core performance testing classes
    "PerformanceBenchmark",
    "DatabaseQueryCounter",
    "MemoryProfiler",
    "ResponseTimeTracker",
    # Performance decorators
    "performance_benchmark",
    "query_count_limit",
    "memory_usage_limit",
    "response_time_limit",
    "cache_performance",
    # Fixtures and data generation
    "PerformanceDataFixtures",
    "create_bulk_pages",
    "create_bulk_blog_posts",
    "create_bulk_translations",
    "create_test_users",
    "create_multilingual_content",
    "cleanup_performance_data",
    # Constants
    "PERFORMANCE_THRESHOLDS",
]
