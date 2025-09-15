#!/usr/bin/env python3
"""
Test Performance Optimization Tools for Bedrock CMS
Provides test performance monitoring, optimization suggestions, and flaky test detection
"""

import gc
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psutil


@dataclass
class TestPerformanceMetric:
    """Performance metrics for a single test"""

    test_name: str
    duration: float
    memory_peak_mb: float
    memory_delta_mb: float
    cpu_percent: float
    status: str  # passed, failed, skipped
    timestamp: datetime
    run_id: str


@dataclass
class TestSuitePerformance:
    """Performance metrics for entire test suite"""

    run_id: str
    timestamp: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    peak_memory_mb: float
    average_memory_mb: float
    cpu_usage_percent: float
    parallel_workers: int
    test_metrics: List[TestPerformanceMetric]


class PerformanceMonitor:
    """Monitor test performance in real-time"""

    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.start_time = None
        self.memory_samples = deque(maxlen=1000)  # Last 1000 memory samples
        self.cpu_samples = deque(maxlen=1000)  # Last 1000 CPU samples

    def start_monitoring(self, interval: float = 0.1):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        tracemalloc.start()

        def monitor():
            process = psutil.Process()
            while self.monitoring:
                try:
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()

                    self.memory_samples.append(
                        {
                            "timestamp": time.time(),
                            "rss_mb": memory_info.rss / 1024 / 1024,
                            "vms_mb": memory_info.vms / 1024 / 1024,
                        }
                    )

                    self.cpu_samples.append(
                        {"timestamp": time.time(), "cpu_percent": cpu_percent}
                    )

                    time.sleep(interval)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return summary"""
        self.monitoring = False
        tracemalloc.stop()

        if not self.memory_samples or not self.cpu_samples:
            return {}

        memory_values = [s["rss_mb"] for s in self.memory_samples]
        cpu_values = [
            s["cpu_percent"] for s in self.cpu_samples if s["cpu_percent"] > 0
        ]

        return {
            "duration": time.time() - self.start_time if self.start_time else 0,
            "peak_memory_mb": max(memory_values) if memory_values else 0,
            "average_memory_mb": statistics.mean(memory_values) if memory_values else 0,
            "memory_stddev_mb": (
                statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            ),
            "average_cpu_percent": statistics.mean(cpu_values) if cpu_values else 0,
            "peak_cpu_percent": max(cpu_values) if cpu_values else 0,
            "memory_samples": len(self.memory_samples),
            "cpu_samples": len(self.cpu_samples),
        }


class TestOptimizer:
    """Analyze and optimize test performance"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_root = project_root / "backend"
        self.reports_dir = self.backend_root / "test_reports"
        self.db_path = self.reports_dir / "test_performance.db"

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize performance tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_duration REAL NOT NULL,
                    total_tests INTEGER NOT NULL,
                    passed_tests INTEGER NOT NULL,
                    failed_tests INTEGER NOT NULL,
                    skipped_tests INTEGER NOT NULL,
                    peak_memory_mb REAL NOT NULL,
                    average_memory_mb REAL NOT NULL,
                    cpu_usage_percent REAL NOT NULL,
                    parallel_workers INTEGER NOT NULL,
                    git_commit TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    duration REAL NOT NULL,
                    memory_peak_mb REAL NOT NULL,
                    memory_delta_mb REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES test_runs (run_id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_name ON test_metrics(test_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_run_timestamp ON test_runs(timestamp)
            """
            )

    def analyze_test_performance(
        self, junit_file: Path
    ) -> Optional[TestSuitePerformance]:
        """Analyze test performance from JUnit XML file"""
        if not junit_file.exists():
            return None

        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(junit_file)
            root = tree.getroot()

            test_metrics = []
            run_id = f"run_{int(time.time())}"

            total_duration = float(root.get("time", 0))
            total_tests = int(root.get("tests", 0))
            failures = int(root.get("failures", 0))
            errors = int(root.get("errors", 0))
            skipped = int(root.get("skipped", 0))
            passed = total_tests - failures - errors - skipped

            # Parse individual test cases
            for testcase in root.findall(".//testcase"):
                test_name = (
                    f"{testcase.get('classname', '')}.{testcase.get('name', '')}"
                )
                duration = float(testcase.get("time", 0))

                # Determine status
                if testcase.find("failure") is not None:
                    status = "failed"
                elif testcase.find("error") is not None:
                    status = "failed"
                elif testcase.find("skipped") is not None:
                    status = "skipped"
                else:
                    status = "passed"

                metric = TestPerformanceMetric(
                    test_name=test_name,
                    duration=duration,
                    memory_peak_mb=0,  # Not available in JUnit XML
                    memory_delta_mb=0,  # Not available in JUnit XML
                    cpu_percent=0,  # Not available in JUnit XML
                    status=status,
                    timestamp=datetime.now(),
                    run_id=run_id,
                )
                test_metrics.append(metric)

            return TestSuitePerformance(
                run_id=run_id,
                timestamp=datetime.now(),
                total_duration=total_duration,
                total_tests=total_tests,
                passed_tests=passed,
                failed_tests=failures + errors,
                skipped_tests=skipped,
                peak_memory_mb=0,  # Not available in JUnit XML
                average_memory_mb=0,  # Not available in JUnit XML
                cpu_usage_percent=0,  # Not available in JUnit XML
                parallel_workers=1,  # Not available in JUnit XML
                test_metrics=test_metrics,
            )

        except Exception as e:
            print(f"Error parsing JUnit file: {e}")
            return None

    def store_performance_data(self, performance: TestSuitePerformance):
        """Store performance data in database"""
        git_commit = self._get_git_commit_hash()

        with sqlite3.connect(self.db_path) as conn:
            # Store test run summary
            conn.execute(
                """
                INSERT OR REPLACE INTO test_runs
                (run_id, timestamp, total_duration, total_tests, passed_tests,
                 failed_tests, skipped_tests, peak_memory_mb, average_memory_mb,
                 cpu_usage_percent, parallel_workers, git_commit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    performance.run_id,
                    performance.timestamp.isoformat(),
                    performance.total_duration,
                    performance.total_tests,
                    performance.passed_tests,
                    performance.failed_tests,
                    performance.skipped_tests,
                    performance.peak_memory_mb,
                    performance.average_memory_mb,
                    performance.cpu_usage_percent,
                    performance.parallel_workers,
                    git_commit,
                ),
            )

            # Store individual test metrics
            for metric in performance.test_metrics:
                conn.execute(
                    """
                    INSERT INTO test_metrics
                    (run_id, test_name, duration, memory_peak_mb, memory_delta_mb,
                     cpu_percent, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metric.run_id,
                        metric.test_name,
                        metric.duration,
                        metric.memory_peak_mb,
                        metric.memory_delta_mb,
                        metric.cpu_percent,
                        metric.status,
                        metric.timestamp.isoformat(),
                    ),
                )

            conn.commit()

    def _get_git_commit_hash(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def identify_slow_tests(
        self, threshold_seconds: float = 1.0, days: int = 30
    ) -> Dict:
        """Identify consistently slow tests"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT test_name, AVG(duration) as avg_duration,
                       MIN(duration) as min_duration, MAX(duration) as max_duration,
                       COUNT(*) as run_count, STDEV(duration) as duration_stddev
                FROM test_metrics
                WHERE datetime(timestamp) >= datetime(?) AND status = 'passed'
                GROUP BY test_name
                HAVING avg_duration > ?
                ORDER BY avg_duration DESC
            """,
                (cutoff_date.isoformat(), threshold_seconds),
            )

            slow_tests = []
            for row in cursor.fetchall():
                slow_tests.append(
                    {
                        "test_name": row[0],
                        "avg_duration": row[1],
                        "min_duration": row[2],
                        "max_duration": row[3],
                        "run_count": row[4],
                        "duration_stddev": row[5] or 0,
                        "consistency": (
                            "stable" if (row[5] or 0) < row[1] * 0.2 else "variable"
                        ),
                    }
                )

        return {
            "threshold_seconds": threshold_seconds,
            "analysis_period_days": days,
            "slow_test_count": len(slow_tests),
            "slow_tests": slow_tests,
        }

    def detect_flaky_tests(self, min_runs: int = 5, days: int = 30) -> Dict:
        """Detect flaky tests (tests that sometimes fail)"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT test_name,
                       COUNT(*) as total_runs,
                       SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_runs,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                       AVG(duration) as avg_duration
                FROM test_metrics
                WHERE datetime(timestamp) >= datetime(?)
                GROUP BY test_name
                HAVING total_runs >= ? AND failed_runs > 0 AND passed_runs > 0
                ORDER BY failed_runs DESC, total_runs DESC
            """,
                (cutoff_date.isoformat(), min_runs),
            )

            flaky_tests = []
            for row in cursor.fetchall():
                failure_rate = row[3] / row[1] * 100
                flaky_tests.append(
                    {
                        "test_name": row[0],
                        "total_runs": row[1],
                        "passed_runs": row[2],
                        "failed_runs": row[3],
                        "failure_rate": failure_rate,
                        "avg_duration": row[4],
                        "flakiness": (
                            "high"
                            if failure_rate > 20
                            else "medium" if failure_rate > 5 else "low"
                        ),
                    }
                )

        return {
            "analysis_period_days": days,
            "min_runs": min_runs,
            "flaky_test_count": len(flaky_tests),
            "flaky_tests": flaky_tests,
        }

    def analyze_test_trends(self, days: int = 30) -> Dict:
        """Analyze test performance trends"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get test run trends
            cursor.execute(
                """
                SELECT timestamp, total_duration, total_tests, peak_memory_mb,
                       cpu_usage_percent, passed_tests, failed_tests
                FROM test_runs
                WHERE datetime(timestamp) >= datetime(?)
                ORDER BY timestamp
            """,
                (cutoff_date.isoformat(),),
            )

            runs = cursor.fetchall()

        if not runs:
            return {"error": f"No test runs found in the last {days} days"}

        # Calculate trends
        durations = [r[1] for r in runs]
        memory_usage = [r[3] for r in runs]
        cpu_usage = [r[4] for r in runs]
        test_counts = [r[2] for r in runs]

        return {
            "analysis_period_days": days,
            "total_runs": len(runs),
            "duration_trend": {
                "current": durations[-1] if durations else 0,
                "average": statistics.mean(durations) if durations else 0,
                "min": min(durations) if durations else 0,
                "max": max(durations) if durations else 0,
                "change_from_first": (
                    durations[-1] - durations[0] if len(durations) > 1 else 0
                ),
            },
            "memory_trend": {
                "current_mb": memory_usage[-1] if memory_usage else 0,
                "average_mb": statistics.mean(memory_usage) if memory_usage else 0,
                "peak_mb": max(memory_usage) if memory_usage else 0,
            },
            "test_count_trend": {
                "current": test_counts[-1] if test_counts else 0,
                "average": statistics.mean(test_counts) if test_counts else 0,
                "growth": (
                    test_counts[-1] - test_counts[0] if len(test_counts) > 1 else 0
                ),
            },
        }

    def generate_optimization_recommendations(self) -> Dict:
        """Generate test optimization recommendations"""
        slow_tests = self.identify_slow_tests()
        flaky_tests = self.detect_flaky_tests()
        trends = self.analyze_test_trends()

        recommendations = []

        # Slow test recommendations
        if slow_tests["slow_test_count"] > 0:
            high_impact_slow = [
                t for t in slow_tests["slow_tests"] if t["avg_duration"] > 5
            ]
            if high_impact_slow:
                recommendations.append(
                    {
                        "category": "Performance",
                        "priority": "HIGH",
                        "issue": f"{len(high_impact_slow)} tests taking >5 seconds",
                        "recommendation": "Optimize slow tests by using fixtures, mocking external calls, or parallel execution",
                        "affected_tests": [
                            t["test_name"] for t in high_impact_slow[:5]
                        ],
                    }
                )

        # Flaky test recommendations
        if flaky_tests["flaky_test_count"] > 0:
            high_flaky = [
                t for t in flaky_tests["flaky_tests"] if t["flakiness"] == "high"
            ]
            if high_flaky:
                recommendations.append(
                    {
                        "category": "Reliability",
                        "priority": "HIGH",
                        "issue": f"{len(high_flaky)} highly flaky tests (>20% failure rate)",
                        "recommendation": "Investigate race conditions, timing issues, or test isolation problems",
                        "affected_tests": [t["test_name"] for t in high_flaky[:5]],
                    }
                )

        # Memory usage recommendations
        if "memory_trend" in trends and trends["memory_trend"]["peak_mb"] > 512:
            recommendations.append(
                {
                    "category": "Memory",
                    "priority": "MEDIUM",
                    "issue": f"Peak memory usage: {trends['memory_trend']['peak_mb']:.1f}MB",
                    "recommendation": "Consider memory optimization: cleanup fixtures, limit test data size, use database transactions",
                    "affected_tests": [],
                }
            )

        # Test suite growth recommendations
        if (
            "test_count_trend" in trends
            and trends["test_count_trend"]["growth"] > 100
            and trends["duration_trend"]["change_from_first"] > 60
        ):
            recommendations.append(
                {
                    "category": "Scalability",
                    "priority": "MEDIUM",
                    "issue": "Test suite duration increasing with test count growth",
                    "recommendation": "Implement parallel execution, test segmentation, or selective test running",
                    "affected_tests": [],
                }
            )

        return {
            "total_recommendations": len(recommendations),
            "high_priority": len(
                [r for r in recommendations if r["priority"] == "HIGH"]
            ),
            "medium_priority": len(
                [r for r in recommendations if r["priority"] == "MEDIUM"]
            ),
            "recommendations": recommendations,
            "analysis_summary": {
                "slow_tests": slow_tests["slow_test_count"],
                "flaky_tests": flaky_tests["flaky_test_count"],
                "recent_runs": trends.get("total_runs", 0),
            },
        }

    def benchmark_test_configurations(self, configurations: List[Dict]) -> Dict:
        """Benchmark different test configurations"""
        results = {}

        for config in configurations:
            print(f"Benchmarking configuration: {config['name']}")

            # Build pytest command with configuration
            cmd = ["python", "-m", "pytest", "apps/accounts/tests/test_simple.py"]
            cmd.extend(config.get("args", []))

            # Run benchmark
            monitor = PerformanceMonitor()
            monitor.start_monitoring()

            start_time = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.backend_root,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                duration = time.time() - start_time
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                duration = 300
                exit_code = -1

            performance_stats = monitor.stop_monitoring()

            results[config["name"]] = {
                "duration": duration,
                "exit_code": exit_code,
                "success": exit_code == 0,
                **performance_stats,
                "configuration": config,
            }

        return results


def main():
    """Main CLI for test optimization tools"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test performance optimization tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--analyze-junit", type=str, help="Analyze performance from JUnit XML file"
    )
    parser.add_argument(
        "--slow-tests",
        type=float,
        default=1.0,
        help="Identify slow tests (threshold in seconds)",
    )
    parser.add_argument("--flaky-tests", action="store_true", help="Detect flaky tests")
    parser.add_argument(
        "--trends", type=int, default=30, help="Analyze trends over N days"
    )
    parser.add_argument(
        "--recommend", action="store_true", help="Generate optimization recommendations"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Benchmark different configurations"
    )
    parser.add_argument("--days", type=int, default=30, help="Analysis period in days")
    parser.add_argument("--export", type=str, help="Export results to file")

    args = parser.parse_args()

    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "backend" / "manage.py").exists():
            break
        project_root = project_root.parent
    else:
        print("Error: Could not find project root")
        return 1

    optimizer = TestOptimizer(project_root)

    results = {}

    if args.analyze_junit:
        junit_file = Path(args.analyze_junit)
        performance = optimizer.analyze_test_performance(junit_file)
        if performance:
            optimizer.store_performance_data(performance)
            results["junit_analysis"] = asdict(performance)
            print(f"Analyzed JUnit file: {junit_file}")

    if args.slow_tests:
        slow_tests = optimizer.identify_slow_tests(args.slow_tests, args.days)
        results["slow_tests"] = slow_tests
        print(f"\nSlow Tests (>{args.slow_tests}s):")
        print(json.dumps(slow_tests, indent=2))

    if args.flaky_tests:
        flaky_tests = optimizer.detect_flaky_tests(days=args.days)
        results["flaky_tests"] = flaky_tests
        print(f"\nFlaky Tests:")
        print(json.dumps(flaky_tests, indent=2))

    if args.trends:
        trends = optimizer.analyze_test_trends(args.trends)
        results["trends"] = trends
        print(f"\nTest Trends ({args.trends} days):")
        print(json.dumps(trends, indent=2))

    if args.recommend:
        recommendations = optimizer.generate_optimization_recommendations()
        results["recommendations"] = recommendations
        print(f"\nOptimization Recommendations:")
        print(json.dumps(recommendations, indent=2))

    if args.benchmark:
        configurations = [
            {"name": "sequential", "args": []},
            {"name": "parallel_2", "args": ["-n", "2"]},
            {"name": "parallel_4", "args": ["-n", "4"]},
        ]
        benchmark_results = optimizer.benchmark_test_configurations(configurations)
        results["benchmark"] = benchmark_results
        print(f"\nBenchmark Results:")
        print(json.dumps(benchmark_results, indent=2))

    if args.export and results:
        export_path = Path(args.export)
        with open(export_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults exported to: {export_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
