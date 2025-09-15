# Bedrock CMS Performance Testing Framework

A comprehensive performance testing framework for the Bedrock CMS project, providing tools for benchmarking, load testing, and performance regression detection.

## Overview

This framework provides:

- **Performance Benchmarking**: Measure and track performance metrics for individual operations
- **Load Testing**: Simulate realistic high-volume scenarios with concurrent users
- **Database Query Optimization**: Detect and prevent N+1 queries and inefficient database access
- **Memory Usage Monitoring**: Track memory consumption and detect memory leaks
- **Cache Performance Testing**: Validate caching strategies and hit rates
- **Search Performance**: Benchmark search and indexing operations
- **Translation System Performance**: Test multilingual content performance
- **API Performance**: Validate REST API response times under various loads

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements/test.txt
```

### 2. Run Basic Performance Tests

```bash
# Run performance benchmarks
python run_performance_tests.py --test-type benchmarks

# Run load tests with 10 concurrent workers
python run_performance_tests.py --test-type load --workers 10

# Run all performance tests and generate a report
python run_performance_tests.py --test-type all --report --report-file performance_report.json
```

### 3. Run Tests with Django

```bash
# Run specific test classes
python manage.py test tests.performance.test_performance_benchmarks.APIPerformanceBenchmarkTests
python manage.py test tests.performance.test_load_scenarios.HighVolumeContentTests

# Run all performance tests
python manage.py test tests.performance
```

## Framework Components

### Core Utilities (`utils.py`)

#### Performance Benchmark Context Manager

```python
from tests.performance.utils import PerformanceBenchmark

with PerformanceBenchmark(
    name="my_operation",
    query_threshold=5,
    time_threshold=0.5,
    memory_threshold=50 * 1024 * 1024  # 50MB
) as benchmark:
    # Your operation here
    perform_operation()

# Access metrics
print(f"Execution time: {benchmark.metrics.execution_time}s")
print(f"Database queries: {benchmark.metrics.database_queries}")
print(f"Memory usage: {benchmark.metrics.memory_usage} bytes")
```

#### Performance Decorators

```python
from tests.performance.utils import (
    performance_benchmark,
    query_count_limit,
    memory_usage_limit,
    response_time_limit,
    cache_performance
)

@performance_benchmark(name="test_operation", time_threshold=1.0)
@query_count_limit(3)
@memory_usage_limit(10 * 1024 * 1024)  # 10MB
@cache_performance()
def test_my_feature(self):
    # Test implementation
    pass
```

#### Database Query Counter

```python
from tests.performance.utils import DatabaseQueryCounter

with DatabaseQueryCounter(threshold=5, log_slow=True) as counter:
    # Operations that should use <= 5 queries
    MyModel.objects.select_related('foreign_key').all()

print(f"Queries executed: {counter.query_count}")
print(f"Slow queries: {len(counter.slow_queries)}")
```

#### Memory Profiler

```python
from tests.performance.utils import MemoryProfiler

with MemoryProfiler(threshold=50 * 1024 * 1024) as profiler:  # 50MB threshold
    # Memory-intensive operations
    large_data = process_large_dataset()

print(f"Memory used: {profiler.memory_usage} bytes")
print(f"Peak memory: {profiler.peak_memory} bytes")
```

### Test Data Fixtures (`fixtures.py`)

#### Bulk Data Creation

```python
from tests.performance.fixtures import PerformanceDataFixtures

fixtures = PerformanceDataFixtures(seed=42)  # Reproducible data

# Create test users
users = fixtures.create_bulk_users(100)

# Create pages with hierarchy
pages = fixtures.create_bulk_pages(500, max_depth=3)

# Create blog posts with categories/tags
blog_posts = fixtures.create_bulk_blog_posts(1000, users[:20])

# Create translations
translations = fixtures.create_bulk_translations(pages, ['es', 'fr', 'de'])

# Create analytics data
analytics = fixtures.create_analytics_data(pages, users, days=30)
```

#### Convenience Functions

```python
from tests.performance.fixtures import (
    create_multilingual_content,
    cleanup_performance_data
)

# Create complete test dataset
test_data = create_multilingual_content(page_count=200, post_count=500)

# Clean up after tests
cleanup_performance_data()
```

### Performance Thresholds

The framework defines performance thresholds in `utils.py`:

```python
PERFORMANCE_THRESHOLDS = {
    'response_time': {
        'api_get': 0.2,      # 200ms for API GET requests
        'api_post': 0.5,     # 500ms for API POST requests
        'page_load': 0.3,    # 300ms for page loads
        'search': 0.4,       # 400ms for search operations
    },
    'database_queries': {
        'list_view': 5,      # Maximum 5 queries for list views
        'detail_view': 3,    # Maximum 3 queries for detail views
        'create': 4,         # Maximum 4 queries for create operations
    },
    'memory_usage': {
        'small_operation': 10 * 1024 * 1024,    # 10MB
        'medium_operation': 50 * 1024 * 1024,   # 50MB
        'large_operation': 200 * 1024 * 1024,   # 200MB
    },
    'cache_hit_rate': {
        'minimum': 0.8,      # 80% minimum cache hit rate
        'good': 0.9,         # 90% good cache hit rate
    }
}
```

## Test Categories

### 1. Performance Benchmarks (`test_performance_benchmarks.py`)

#### API Performance Tests
- Page list/detail API performance
- Blog post API performance
- Search API performance
- Bulk operations performance

#### Database Optimization Tests
- N+1 query detection
- Query count limits
- Complex filtering performance
- Aggregation performance

#### Cache Performance Tests
- Cache hit/miss rates
- Cache invalidation patterns
- Bulk cache operations

#### Memory Performance Tests
- Memory usage limits
- Memory leak detection
- Large data processing optimization

### 2. Load Testing Scenarios (`test_load_scenarios.py`)

#### High-Volume Content Tests
```python
class HighVolumeContentTests(TransactionTestCase, PerformanceTestMixin):
    def test_high_volume_page_creation(self):
        # Tests creating 100 pages concurrently

    def test_bulk_content_publishing(self):
        # Tests publishing content under load
```

#### Concurrent User Access Tests
```python
class ConcurrentUserAccessTests(APITestCase, PerformanceTestMixin):
    def test_concurrent_api_access(self):
        # Simulates multiple users accessing APIs simultaneously

    def test_multilingual_content_access(self):
        # Tests accessing translated content concurrently
```

#### Search and Indexing Load Tests
```python
class SearchAndIndexingLoadTests(TestCase, PerformanceTestMixin):
    def test_search_performance_under_load(self):
        # Tests search functionality under concurrent load

    def test_search_indexing_under_load(self):
        # Tests indexing performance with bulk operations
```

## Performance Test Mixin

Use `PerformanceTestMixin` in your test classes for enhanced capabilities:

```python
from tests.performance.utils import PerformanceTestMixin

class MyPerformanceTests(TestCase, PerformanceTestMixin):
    def setUp(self):
        super().setUp()
        # Automatic performance tracking setup

    def tearDown(self):
        super().tearDown()
        # Automatic performance metrics logging

    def test_my_feature(self):
        # Access to performance utilities
        metrics = self.measure_performance(my_function, arg1, arg2)
        self.assertLess(metrics.execution_time, 1.0)
```

## Load Test Runner

The `LoadTestRunner` class provides utilities for running concurrent load tests:

```python
from tests.performance.utils import LoadTestRunner

runner = LoadTestRunner(max_workers=10)

def my_test_operation():
    # Your test operation
    pass

results = runner.run_load_test(
    test_function=my_test_operation,
    num_operations=100,
    concurrent_workers=5,
    timeout=30
)

print(f"Success rate: {results.success_rate}%")
print(f"Average response time: {results.average_response_time}s")
print(f"Operations per second: {results.operations_per_second}")
```

## Load Test Client

Enhanced test client for API load testing:

```python
from tests.performance.utils import LoadTestClient

client = LoadTestClient()
client.force_authenticate(user=test_user)

# Make requests (automatically tracked)
response = client.get('/api/v1/cms/pages/')
response = client.post('/api/v1/cms/pages/', data=page_data)

# Get performance statistics
stats = client.get_performance_stats()
print(f"Average response time: {stats['avg_response_time']}s")
print(f"Total requests: {stats['total_requests']}")
```

## Best Practices

### 1. Test Data Management

- Use `PerformanceDataFixtures` with seeds for reproducible tests
- Clean up test data with `cleanup_performance_data()`
- Use transactions for atomic test data creation

### 2. Performance Assertions

```python
# Use appropriate thresholds
@query_count_limit(PERFORMANCE_THRESHOLDS['database_queries']['list_view'])
def test_page_list(self):
    pass

# Test cache performance
@cache_performance()
def test_cached_operation(self):
    # First call (cache miss)
    result1 = get_cached_data()
    # Second call (cache hit)
    result2 = get_cached_data()
```

### 3. Memory Testing

```python
@memory_usage_limit(PERFORMANCE_THRESHOLDS['memory_usage']['large_operation'])
def test_bulk_operation(self):
    # Process data in chunks to optimize memory
    for chunk in chunked_data:
        process_chunk(chunk)
```

### 4. Load Testing

```python
# Use realistic data volumes
test_data = create_multilingual_content(page_count=500, post_count=1000)

# Test with appropriate concurrency
results = runner.run_load_test(
    test_function=api_request,
    num_operations=200,
    concurrent_workers=10,  # Realistic concurrent user count
    timeout=30
)

# Assert reasonable performance
self.assertGreater(results.success_rate, 95)  # 95% success rate
self.assertLess(results.average_response_time, 1.0)  # < 1 second
```

## Integration with CI/CD

Add performance tests to your CI pipeline:

```yaml
# GitHub Actions example
- name: Run Performance Tests
  run: |
    python run_performance_tests.py --test-type benchmarks --report --report-file performance_report.json

- name: Upload Performance Report
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: performance_report.json
```

## Performance Monitoring

The framework integrates with Django's existing performance monitoring:

- Uses `PerformanceMonitoringMiddleware` for request tracking
- Leverages `QueryCountLimitMiddleware` for database monitoring
- Integrates with cache hit rate tracking
- Provides memory usage monitoring

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Use memory profiling to identify memory-intensive operations
2. **Slow Database Queries**: Enable slow query logging and use `DatabaseQueryCounter`
3. **Poor Cache Performance**: Use cache performance decorators to track hit rates
4. **Test Data Cleanup**: Always use `cleanup_performance_data()` in tearDown methods

### Debugging Performance Issues

```python
# Enable detailed logging
import logging
logging.getLogger('performance.testing').setLevel(logging.DEBUG)

# Use performance benchmark for detailed metrics
with PerformanceBenchmark("debug_operation") as benchmark:
    problematic_operation()

print(f"Metrics: {benchmark.metrics.to_dict()}")
```

## Contributing

When adding new performance tests:

1. Follow the existing patterns and use the provided utilities
2. Set appropriate performance thresholds based on the operation type
3. Include both success and failure scenarios
4. Document any specific setup requirements
5. Use meaningful test names and add docstrings

## Performance Metrics Reference

### Key Performance Indicators

- **Response Time**: Time taken to complete an operation
- **Database Queries**: Number of database queries executed
- **Memory Usage**: Peak memory consumption during operation
- **Cache Hit Rate**: Percentage of cache hits vs. misses
- **Operations per Second**: Throughput under load
- **Success Rate**: Percentage of successful operations under load

### Acceptable Performance Ranges

- API GET requests: < 200ms
- API POST requests: < 500ms
- Database queries per request: < 5 for list views, < 3 for detail views
- Memory usage: < 50MB for typical operations
- Cache hit rate: > 80% minimum, > 90% good
- Load test success rate: > 95%
