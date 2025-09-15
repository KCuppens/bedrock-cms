#!/usr/bin/env python3
"""
Advanced Coverage Analysis and Reporting Tools for Bedrock CMS
Provides comprehensive coverage analysis, trending, and optimization suggestions
"""

import json
import os
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CoverageMetrics:
    """Coverage metrics for a file or module"""

    name: str
    statements: int
    missing: int
    excluded: int
    coverage: float
    missing_lines: List[str]
    branches: Optional[int] = None
    partial_branches: Optional[int] = None
    branch_coverage: Optional[float] = None


@dataclass
class CoverageReport:
    """Complete coverage report"""

    timestamp: datetime
    total_statements: int
    total_missing: int
    total_coverage: float
    file_metrics: List[CoverageMetrics]
    branch_coverage: Optional[float] = None


class CoverageAnalyzer:
    """Advanced coverage analysis and reporting"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_root = project_root / "backend"
        self.coverage_file = self.backend_root / ".coverage"
        self.coverage_xml = self.backend_root / "coverage.xml"
        self.coverage_json = self.backend_root / "coverage.json"
        self.html_dir = self.backend_root / "htmlcov"
        self.reports_dir = self.backend_root / "coverage_reports"
        self.db_path = self.reports_dir / "coverage_history.db"

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for coverage history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coverage_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_statements INTEGER NOT NULL,
                    total_missing INTEGER NOT NULL,
                    total_coverage REAL NOT NULL,
                    branch_coverage REAL,
                    commit_hash TEXT,
                    report_data TEXT NOT NULL
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_coverage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    statements INTEGER NOT NULL,
                    missing INTEGER NOT NULL,
                    coverage REAL NOT NULL,
                    missing_lines TEXT,
                    FOREIGN KEY (report_id) REFERENCES coverage_reports (id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON coverage_reports(timestamp)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_filename
                ON file_coverage(filename)
            """
            )

    def generate_coverage_report(self, format_type: str = "html") -> bool:
        """Generate coverage report in specified format"""
        if not self.coverage_file.exists():
            print("Error: No coverage data found. Run tests with coverage first.")
            return False

        try:
            cmd = ["python", "-m", "coverage", "report"]

            if format_type == "html":
                cmd = ["python", "-m", "coverage", "html"]
                subprocess.run(cmd, cwd=self.backend_root, check=True)
                print(f"HTML coverage report generated: {self.html_dir}/index.html")

            elif format_type == "xml":
                cmd = ["python", "-m", "coverage", "xml"]
                subprocess.run(cmd, cwd=self.backend_root, check=True)
                print(f"XML coverage report generated: {self.coverage_xml}")

            elif format_type == "json":
                cmd = ["python", "-m", "coverage", "json"]
                subprocess.run(cmd, cwd=self.backend_root, check=True)
                print(f"JSON coverage report generated: {self.coverage_json}")

            else:  # terminal
                subprocess.run(cmd, cwd=self.backend_root, check=True)

            return True

        except subprocess.CalledProcessError as e:
            print(f"Error generating coverage report: {e}")
            return False

    def parse_coverage_data(self) -> Optional[CoverageReport]:
        """Parse coverage data from various sources"""
        # Try JSON first (most complete), then XML, then terminal
        if self.coverage_json.exists():
            return self._parse_json_coverage()
        elif self.coverage_xml.exists():
            return self._parse_xml_coverage()
        else:
            # Generate and parse terminal report
            return self._parse_terminal_coverage()

    def _parse_json_coverage(self) -> Optional[CoverageReport]:
        """Parse JSON coverage report"""
        try:
            with open(self.coverage_json) as f:
                data = json.load(f)

            file_metrics = []
            for filename, file_data in data["files"].items():
                summary = file_data["summary"]

                # Get missing lines
                missing_lines = []
                if "missing_lines" in file_data:
                    missing_lines = [str(line) for line in file_data["missing_lines"]]

                metrics = CoverageMetrics(
                    name=filename,
                    statements=summary["num_statements"],
                    missing=summary["missing_lines"],
                    excluded=summary.get("excluded_lines", 0),
                    coverage=summary["percent_covered"],
                    missing_lines=missing_lines,
                    branches=summary.get("num_branches"),
                    partial_branches=summary.get("num_partial_branches"),
                    branch_coverage=summary.get("percent_covered_display"),
                )
                file_metrics.append(metrics)

            totals = data["totals"]
            return CoverageReport(
                timestamp=datetime.now(),
                total_statements=totals["num_statements"],
                total_missing=totals["missing_lines"],
                total_coverage=totals["percent_covered"],
                file_metrics=file_metrics,
                branch_coverage=totals.get("percent_covered_display"),
            )

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error parsing JSON coverage: {e}")
            return None

    def _parse_xml_coverage(self) -> Optional[CoverageReport]:
        """Parse XML coverage report"""
        try:
            tree = ET.parse(self.coverage_xml)
            root = tree.getroot()

            file_metrics = []
            for package in root.findall(".//package"):
                for class_elem in package.findall("classes/class"):
                    filename = class_elem.get("filename", "")
                    lines = class_elem.findall("lines/line")

                    total_lines = len(lines)
                    hit_lines = len([l for l in lines if int(l.get("hits", 0)) > 0])
                    missing_lines = [
                        l.get("number") for l in lines if int(l.get("hits", 0)) == 0
                    ]

                    coverage_pct = (
                        (hit_lines / total_lines * 100) if total_lines > 0 else 0
                    )

                    metrics = CoverageMetrics(
                        name=filename,
                        statements=total_lines,
                        missing=total_lines - hit_lines,
                        excluded=0,
                        coverage=coverage_pct,
                        missing_lines=missing_lines,
                    )
                    file_metrics.append(metrics)

            # Calculate totals
            total_statements = sum(m.statements for m in file_metrics)
            total_missing = sum(m.missing for m in file_metrics)
            total_coverage = (
                ((total_statements - total_missing) / total_statements * 100)
                if total_statements > 0
                else 0
            )

            return CoverageReport(
                timestamp=datetime.now(),
                total_statements=total_statements,
                total_missing=total_missing,
                total_coverage=total_coverage,
                file_metrics=file_metrics,
            )

        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Error parsing XML coverage: {e}")
            return None

    def _parse_terminal_coverage(self) -> Optional[CoverageReport]:
        """Parse coverage from terminal output"""
        try:
            result = subprocess.run(
                ["python", "-m", "coverage", "report", "--format=json"],
                cwd=self.backend_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Save output as JSON and parse
            temp_json = self.backend_root / "temp_coverage.json"
            with open(temp_json, "w") as f:
                f.write(result.stdout)

            self.coverage_json = temp_json
            report = self._parse_json_coverage()
            temp_json.unlink()  # Clean up

            return report

        except subprocess.CalledProcessError as e:
            print(f"Error generating terminal coverage report: {e}")
            return None

    def store_coverage_report(self, report: CoverageReport) -> int:
        """Store coverage report in database"""
        commit_hash = self._get_git_commit_hash()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert main report
            cursor.execute(
                """
                INSERT INTO coverage_reports
                (timestamp, total_statements, total_missing, total_coverage,
                 branch_coverage, commit_hash, report_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    report.timestamp.isoformat(),
                    report.total_statements,
                    report.total_missing,
                    report.total_coverage,
                    report.branch_coverage,
                    commit_hash,
                    json.dumps(asdict(report), default=str),
                ),
            )

            report_id = cursor.lastrowid

            # Insert file-level data
            for file_metric in report.file_metrics:
                cursor.execute(
                    """
                    INSERT INTO file_coverage
                    (report_id, filename, statements, missing, coverage, missing_lines)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        report_id,
                        file_metric.name,
                        file_metric.statements,
                        file_metric.missing,
                        file_metric.coverage,
                        json.dumps(file_metric.missing_lines),
                    ),
                )

            conn.commit()
            return report_id

    def _get_git_commit_hash(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def analyze_coverage_trends(self, days: int = 30) -> Dict:
        """Analyze coverage trends over time"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT timestamp, total_coverage, branch_coverage
                FROM coverage_reports
                WHERE datetime(timestamp) >= datetime(?)
                ORDER BY timestamp
            """,
                (cutoff_date.isoformat(),),
            )

            reports = cursor.fetchall()

        if not reports:
            return {"error": f"No reports found in the last {days} days"}

        # Calculate trends
        timestamps = [datetime.fromisoformat(r[0]) for r in reports]
        coverages = [r[1] for r in reports]
        branch_coverages = [r[2] for r in reports if r[2] is not None]

        trend_data = {
            "period_days": days,
            "total_reports": len(reports),
            "coverage_trend": {
                "current": coverages[-1] if coverages else 0,
                "previous": coverages[0] if coverages else 0,
                "change": coverages[-1] - coverages[0] if len(coverages) > 1 else 0,
                "min": min(coverages) if coverages else 0,
                "max": max(coverages) if coverages else 0,
                "average": sum(coverages) / len(coverages) if coverages else 0,
            },
        }

        if branch_coverages:
            trend_data["branch_coverage_trend"] = {
                "current": branch_coverages[-1],
                "previous": branch_coverages[0],
                "change": (
                    branch_coverages[-1] - branch_coverages[0]
                    if len(branch_coverages) > 1
                    else 0
                ),
                "average": sum(branch_coverages) / len(branch_coverages),
            }

        return trend_data

    def find_coverage_gaps(self, threshold: float = 80.0) -> Dict:
        """Find files and modules with low coverage"""
        report = self.parse_coverage_data()
        if not report:
            return {"error": "No coverage data available"}

        low_coverage_files = []
        uncovered_files = []

        for file_metric in report.file_metrics:
            if file_metric.coverage == 0:
                uncovered_files.append(
                    {"name": file_metric.name, "statements": file_metric.statements}
                )
            elif file_metric.coverage < threshold:
                low_coverage_files.append(
                    {
                        "name": file_metric.name,
                        "coverage": file_metric.coverage,
                        "statements": file_metric.statements,
                        "missing": file_metric.missing,
                        "missing_lines": file_metric.missing_lines,
                    }
                )

        # Sort by coverage (ascending) and missing lines (descending)
        low_coverage_files.sort(key=lambda x: (x["coverage"], -x["missing"]))

        return {
            "threshold": threshold,
            "total_files": len(report.file_metrics),
            "low_coverage_count": len(low_coverage_files),
            "uncovered_count": len(uncovered_files),
            "low_coverage_files": low_coverage_files,
            "uncovered_files": uncovered_files,
        }

    def suggest_testing_priorities(self) -> Dict:
        """Suggest testing priorities based on coverage analysis"""
        gaps = self.find_coverage_gaps()

        if "error" in gaps:
            return gaps

        priorities = []

        # High priority: Uncovered files with many statements
        for file_info in gaps["uncovered_files"]:
            if file_info["statements"] > 10:
                priorities.append(
                    {
                        "file": file_info["name"],
                        "priority": "HIGH",
                        "reason": f"Completely uncovered with {file_info['statements']} statements",
                        "suggested_action": "Create basic test coverage",
                    }
                )

        # Medium priority: Low coverage files with many missing lines
        for file_info in gaps["low_coverage_files"]:
            if file_info["missing"] > 20:
                priorities.append(
                    {
                        "file": file_info["name"],
                        "priority": "MEDIUM",
                        "reason": f"Low coverage ({file_info['coverage']:.1f}%) with {file_info['missing']} missing lines",
                        "suggested_action": "Improve test coverage for critical paths",
                    }
                )

        # Low priority: Files close to threshold
        for file_info in gaps["low_coverage_files"]:
            if 70 <= file_info["coverage"] < 80 and file_info["missing"] <= 10:
                priorities.append(
                    {
                        "file": file_info["name"],
                        "priority": "LOW",
                        "reason": f"Near threshold ({file_info['coverage']:.1f}%) with few missing lines",
                        "suggested_action": "Add tests for remaining edge cases",
                    }
                )

        return {
            "total_priorities": len(priorities),
            "high_priority": len([p for p in priorities if p["priority"] == "HIGH"]),
            "medium_priority": len(
                [p for p in priorities if p["priority"] == "MEDIUM"]
            ),
            "low_priority": len([p for p in priorities if p["priority"] == "LOW"]),
            "priorities": priorities,
        }

    def generate_coverage_badge(self, output_path: Optional[Path] = None) -> str:
        """Generate coverage badge data"""
        report = self.parse_coverage_data()
        if not report:
            return "Coverage: Unknown"

        coverage = report.total_coverage

        if coverage >= 90:
            color = "brightgreen"
        elif coverage >= 80:
            color = "green"
        elif coverage >= 70:
            color = "yellowgreen"
        elif coverage >= 60:
            color = "yellow"
        else:
            color = "red"

        badge_text = f"Coverage: {coverage:.1f}%"
        badge_url = f"https://img.shields.io/badge/Coverage-{coverage:.1f}%25-{color}"

        if output_path:
            badge_data = {
                "text": badge_text,
                "url": badge_url,
                "coverage": coverage,
                "color": color,
                "timestamp": datetime.now().isoformat(),
            }

            with open(output_path, "w") as f:
                json.dump(badge_data, f, indent=2)

        return badge_text

    def export_coverage_report(self, format_type: str = "json") -> str:
        """Export comprehensive coverage report"""
        report = self.parse_coverage_data()
        if not report:
            return "No coverage data available"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "json":
            output_file = self.reports_dir / f"coverage_report_{timestamp}.json"
            with open(output_file, "w") as f:
                json.dump(asdict(report), f, indent=2, default=str)

        elif format_type == "csv":
            import csv

            output_file = self.reports_dir / f"coverage_report_{timestamp}.csv"
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["File", "Statements", "Missing", "Coverage", "Missing Lines"]
                )
                for metric in report.file_metrics:
                    writer.writerow(
                        [
                            metric.name,
                            metric.statements,
                            metric.missing,
                            f"{metric.coverage:.2f}%",
                            "; ".join(
                                metric.missing_lines[:10]
                            ),  # Limit to first 10 lines
                        ]
                    )

        return str(output_file)


def main():
    """Main CLI for coverage analysis"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Advanced coverage analysis for Bedrock CMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--generate",
        choices=["html", "xml", "json", "terminal"],
        default="html",
        help="Generate coverage report",
    )
    parser.add_argument("--analyze", action="store_true", help="Analyze coverage data")
    parser.add_argument(
        "--trends",
        type=int,
        metavar="DAYS",
        default=30,
        help="Analyze coverage trends (default: 30 days)",
    )
    parser.add_argument(
        "--gaps",
        type=float,
        metavar="THRESHOLD",
        default=80.0,
        help="Find coverage gaps below threshold",
    )
    parser.add_argument(
        "--priorities", action="store_true", help="Suggest testing priorities"
    )
    parser.add_argument(
        "--badge", type=str, metavar="OUTPUT", help="Generate coverage badge"
    )
    parser.add_argument(
        "--export", choices=["json", "csv"], help="Export coverage report"
    )
    parser.add_argument(
        "--store", action="store_true", help="Store coverage report in database"
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
        print("Error: Could not find project root")
        return 1

    analyzer = CoverageAnalyzer(project_root)

    # Generate report if requested
    if args.generate:
        success = analyzer.generate_coverage_report(args.generate)
        if not success:
            return 1

    # Store report if requested
    if args.store:
        report = analyzer.parse_coverage_data()
        if report:
            report_id = analyzer.store_coverage_report(report)
            print(f"Coverage report stored with ID: {report_id}")

    # Analysis commands
    if args.analyze:
        report = analyzer.parse_coverage_data()
        if report:
            print(f"\nCoverage Analysis:")
            print(f"Total Coverage: {report.total_coverage:.2f}%")
            print(f"Total Statements: {report.total_statements}")
            print(f"Missing Statements: {report.total_missing}")
            if report.branch_coverage:
                print(f"Branch Coverage: {report.branch_coverage:.2f}%")

    if args.trends:
        trends = analyzer.analyze_coverage_trends(args.trends)
        print(f"\nCoverage Trends ({args.trends} days):")
        print(json.dumps(trends, indent=2))

    if args.gaps:
        gaps = analyzer.find_coverage_gaps(args.gaps)
        print(f"\nCoverage Gaps (threshold: {args.gaps}%):")
        print(json.dumps(gaps, indent=2))

    if args.priorities:
        priorities = analyzer.suggest_testing_priorities()
        print("\nTesting Priorities:")
        print(json.dumps(priorities, indent=2))

    if args.badge:
        badge_path = Path(args.badge) if args.badge != "stdout" else None
        badge = analyzer.generate_coverage_badge(badge_path)
        print(f"\nCoverage Badge: {badge}")

    if args.export:
        export_file = analyzer.export_coverage_report(args.export)
        print(f"Coverage report exported to: {export_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
