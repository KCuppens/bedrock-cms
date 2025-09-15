#!/usr/bin/env python3
"""
Advanced Test Execution Script for Bedrock CMS
Provides comprehensive test management with multiple execution profiles
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil


@dataclass
class TestProfile:
    """Test execution profile configuration"""

    name: str
    description: str
    markers: List[str]
    parallel: bool
    timeout: int
    coverage: bool
    extra_args: List[str]


class TestExecutionManager:
    """Manage test execution with different profiles and optimizations"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_root = project_root / "backend"
        self.reports_dir = self.backend_root / "test_reports"
        self.coverage_dir = self.backend_root / "htmlcov"

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)

        # Test profiles
        self.profiles = {
            "fast": TestProfile(
                name="fast",
                description="Fast unit tests only",
                markers=["not slow", "not integration", "not e2e"],
                parallel=True,
                timeout=120,
                coverage=False,
                extra_args=["--maxfail=5"],
            ),
            "unit": TestProfile(
                name="unit",
                description="Unit tests with coverage",
                markers=["unit", "not integration", "not e2e"],
                parallel=True,
                timeout=300,
                coverage=True,
                extra_args=["--durations=10"],
            ),
            "integration": TestProfile(
                name="integration",
                description="Integration tests",
                markers=["integration"],
                parallel=False,
                timeout=600,
                coverage=True,
                extra_args=["--reuse-db"],
            ),
            "full": TestProfile(
                name="full",
                description="Complete test suite with coverage",
                markers=[],
                parallel=True,
                timeout=1200,
                coverage=True,
                extra_args=["--durations=20"],
            ),
            "smoke": TestProfile(
                name="smoke",
                description="Smoke tests for quick validation",
                markers=["smoke"],
                parallel=True,
                timeout=60,
                coverage=False,
                extra_args=["--maxfail=1"],
            ),
            "regression": TestProfile(
                name="regression",
                description="Regression tests",
                markers=["regression"],
                parallel=False,
                timeout=900,
                coverage=True,
                extra_args=["--reuse-db"],
            ),
            "security": TestProfile(
                name="security",
                description="Security-focused tests",
                markers=["security"],
                parallel=False,
                timeout=300,
                coverage=True,
                extra_args=[],
            ),
            "performance": TestProfile(
                name="performance",
                description="Performance validation tests",
                markers=["performance"],
                parallel=False,
                timeout=600,
                coverage=False,
                extra_args=["--benchmark-only"],
            ),
        }

    def run_profile(
        self,
        profile_name: str,
        apps: List[str] = None,
        verbose: int = 1,
        fail_fast: bool = False,
    ) -> int:
        """Run tests with specified profile"""
        if profile_name not in self.profiles:
            print(f"Error: Unknown profile '{profile_name}'")
            print(f"Available profiles: {list(self.profiles.keys())}")
            return 1

        profile = self.profiles[profile_name]
        print(f"\nRunning {profile.name} tests: {profile.description}")
        print("=" * 60)

        # Build pytest command
        cmd = self._build_pytest_command(profile, apps, verbose, fail_fast)

        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_root,
                timeout=profile.timeout,
                capture_output=False,
            )
            duration = time.time() - start_time

            # Generate report
            self._generate_execution_report(profile, result.returncode, duration)

            return result.returncode

        except subprocess.TimeoutExpired:
            print(f"\nTests timed out after {profile.timeout} seconds")
            return 1
        except KeyboardInterrupt:
            print("\nTests interrupted by user")
            return 1

    def _build_pytest_command(
        self, profile: TestProfile, apps: List[str], verbose: int, fail_fast: bool
    ) -> List[str]:
        """Build pytest command for profile"""
        cmd = ["python", "-m", "pytest"]

        # Add verbosity
        if verbose > 1:
            cmd.append("-v" * min(verbose, 3))

        # Add markers
        if profile.markers:
            for marker in profile.markers:
                cmd.extend(["-m", marker])

        # Add parallel execution
        if profile.parallel:
            cpu_count = os.cpu_count() or 1
            workers = min(cpu_count, 4)  # Limit to 4 workers
            cmd.extend(["-n", str(workers)])

        # Add coverage
        if profile.coverage:
            cmd.extend(
                [
                    "--cov=apps",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                    "--cov-config=.coveragerc",
                ]
            )

        # Add timeout
        cmd.extend(["--timeout", str(profile.timeout // 10)])

        # Add fail fast
        if fail_fast:
            cmd.append("--maxfail=1")

        # Add profile-specific args
        cmd.extend(profile.extra_args)

        # Add JUnit XML report
        junit_file = self.reports_dir / f"junit_{profile.name}.xml"
        cmd.extend(["--junitxml", str(junit_file)])

        # Add specific apps if provided
        if apps:
            for app in apps:
                cmd.append(f"apps/{app}")
        else:
            cmd.append("apps")

        return cmd

    def _generate_execution_report(
        self, profile: TestProfile, exit_code: int, duration: float
    ):
        """Generate execution report"""
        report = {
            "profile": profile.name,
            "description": profile.description,
            "timestamp": time.time(),
            "duration": duration,
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "system_info": {
                "cpu_count": os.cpu_count(),
                "memory_gb": psutil.virtual_memory().total / (1024**3),
                "platform": sys.platform,
            },
        }

        report_file = (
            self.reports_dir / f"execution_{profile.name}_{int(time.time())}.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nExecution Report:")
        print(f"Profile: {profile.name}")
        print(f"Duration: {duration:.2f}s")
        print(f"Status: {report['status']}")
        print(f"Report saved: {report_file}")

    def run_parallel_profiles(self, profiles: List[str]) -> Dict[str, int]:
        """Run multiple profiles in parallel"""
        print(f"Running {len(profiles)} profiles in parallel...")

        results = {}
        with ProcessPoolExecutor(max_workers=min(len(profiles), 4)) as executor:
            futures = {
                executor.submit(self.run_profile, profile): profile
                for profile in profiles
            }

            for future in as_completed(futures):
                profile = futures[future]
                try:
                    exit_code = future.result()
                    results[profile] = exit_code
                    status = "PASSED" if exit_code == 0 else "FAILED"
                    print(f"Profile {profile}: {status}")
                except Exception as e:
                    print(f"Profile {profile} failed with exception: {e}")
                    results[profile] = 1

        return results

    def analyze_test_trends(self, days: int = 7) -> Dict:
        """Analyze test execution trends"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        reports = []

        # Collect recent reports
        for report_file in self.reports_dir.glob("execution_*.json"):
            try:
                with open(report_file) as f:
                    report = json.load(f)
                    if report.get("timestamp", 0) > cutoff_time:
                        reports.append(report)
            except (json.JSONDecodeError, IOError):
                continue

        if not reports:
            return {"error": "No recent reports found"}

        # Analyze trends
        profile_stats = {}
        for report in reports:
            profile = report["profile"]
            if profile not in profile_stats:
                profile_stats[profile] = {
                    "executions": 0,
                    "total_duration": 0,
                    "failures": 0,
                    "success_rate": 0,
                }

            stats = profile_stats[profile]
            stats["executions"] += 1
            stats["total_duration"] += report["duration"]
            if report["exit_code"] != 0:
                stats["failures"] += 1

        # Calculate derived metrics
        for profile, stats in profile_stats.items():
            stats["average_duration"] = stats["total_duration"] / stats["executions"]
            stats["success_rate"] = (
                (stats["executions"] - stats["failures"]) / stats["executions"] * 100
            )

        return {
            "analysis_period_days": days,
            "total_reports": len(reports),
            "profile_statistics": profile_stats,
        }

    def cleanup_reports(self, keep_days: int = 30):
        """Clean up old test reports"""
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        cleaned = 0

        for report_file in self.reports_dir.glob("*.xml"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                cleaned += 1

        for report_file in self.reports_dir.glob("*.json"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                cleaned += 1

        print(f"Cleaned up {cleaned} old report files")

    def list_profiles(self):
        """List available test profiles"""
        print("\nAvailable Test Profiles:")
        print("=" * 50)
        for name, profile in self.profiles.items():
            parallel_str = "parallel" if profile.parallel else "sequential"
            coverage_str = "with coverage" if profile.coverage else "no coverage"
            print(f"{name:12} - {profile.description}")
            print(
                f"{'':12}   {parallel_str}, {coverage_str}, {profile.timeout}s timeout"
            )
            if profile.markers:
                print(f"{'':12}   markers: {', '.join(profile.markers)}")
            print()


def main():
    """Main entry point for test execution script"""
    parser = argparse.ArgumentParser(
        description="Advanced test execution for Bedrock CMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fast                    # Run fast tests
  %(prog)s unit --apps accounts    # Run unit tests for accounts app
  %(prog)s full -v                 # Run full test suite with verbose output
  %(prog)s --parallel fast unit    # Run multiple profiles in parallel
  %(prog)s --list                  # List available profiles
  %(prog)s --analyze               # Analyze test trends
        """,
    )

    # Main arguments
    parser.add_argument("profile", nargs="?", help="Test profile to run")
    parser.add_argument("--apps", nargs="+", help="Specific apps to test")
    parser.add_argument(
        "-v", "--verbose", action="count", default=1, help="Increase verbosity"
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first failure"
    )

    # Multiple profiles
    parser.add_argument(
        "--parallel",
        nargs="+",
        metavar="PROFILE",
        help="Run multiple profiles in parallel",
    )

    # Utility commands
    parser.add_argument("--list", action="store_true", help="List available profiles")
    parser.add_argument("--analyze", action="store_true", help="Analyze test trends")
    parser.add_argument(
        "--analyze-days", type=int, default=7, help="Days to analyze (default: 7)"
    )
    parser.add_argument("--cleanup", action="store_true", help="Clean up old reports")
    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=30,
        help="Keep reports for N days (default: 30)",
    )

    args = parser.parse_args()

    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "backend" / "manage.py").exists():
            break
        project_root = project_root.parent
    else:
        print("Error: Could not find project root (looking for backend/manage.py)")
        return 1

    manager = TestExecutionManager(project_root)

    # Handle utility commands
    if args.list:
        manager.list_profiles()
        return 0

    if args.analyze:
        trends = manager.analyze_test_trends(args.analyze_days)
        print(f"\nTest Trends Analysis ({args.analyze_days} days):")
        print("=" * 50)
        print(json.dumps(trends, indent=2))
        return 0

    if args.cleanup:
        manager.cleanup_reports(args.cleanup_days)
        return 0

    # Handle parallel execution
    if args.parallel:
        results = manager.run_parallel_profiles(args.parallel)
        failed_profiles = [p for p, code in results.items() if code != 0]

        if failed_profiles:
            print(f"\nFailed profiles: {failed_profiles}")
            return 1
        else:
            print(f"\nAll profiles passed!")
            return 0

    # Handle single profile execution
    if not args.profile:
        parser.print_help()
        return 1

    return manager.run_profile(
        args.profile, apps=args.apps, verbose=args.verbose, fail_fast=args.fail_fast
    )


if __name__ == "__main__":
    sys.exit(main())
