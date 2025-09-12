import io

import json

import sys


from django.core.management.base import BaseCommand


from apps.core.security_audit import print_security_audit_report, run_security_audit


"""Management command to run security audit on all API endpoints."""


class Command(BaseCommand):

    help = "Run security audit on all API endpoints"

    def add_arguments(self, parser):

        parser.add_argument(
            "--output",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )

        parser.add_argument("--file", type=str, help="Save output to file")

        parser.add_argument(
            "--verbose", action="store_true", help="Show detailed endpoint information"
        )

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Starting security audit..."))

        # Run the audit

        try:

            report = run_security_audit()

        except Exception as e:

            self.stdout.write(self.style.ERROR(f"Security audit failed: {e}"))

        # Output results

        if options["output"] == "json":

            output = json.dumps(report, indent=2)

        else:

            # Use print to capture formatted output

            old_stdout = sys.stdout

            sys.stdout = captured_output = io.StringIO()

            try:

                print_security_audit_report(report)

                output = captured_output.getvalue()

            finally:

                sys.stdout = old_stdout

        # Save to file if specified

        if options["file"]:

            try:

                with open(options["file"], "w") as f:

                    f.write(output)

                self.stdout.write(
                    self.style.SUCCESS(f"Report saved to {options['file']}")
                )

            except Exception as e:

                self.stdout.write(self.style.ERROR(f"Failed to save report: {e}"))

        else:

            # Print to console

            self.stdout.write(output)

        # Show verbose details if requested

        if options["verbose"] and options["output"] != "json":

            self._show_endpoint_details(report)

        # Summary

        issues = report["issues_found"]

        warnings = report["warnings_found"]

        if issues > 0:

            self.stdout.write(
                self.style.ERROR(
                    f"\nSecurity audit completed with {issues} critical issues and {warnings} warnings."
                )
            )

        elif warnings > 0:

            self.stdout.write(
                self.style.WARNING(
                    f"\nSecurity audit completed with {warnings} warnings."
                )
            )

        else:

            self.stdout.write(
                self.style.SUCCESS(
                    "\nSecurity audit completed successfully - no critical issues found!"
                )
            )

    def _show_endpoint_details(self, report):
        """Show detailed endpoint information."""

        self.stdout.write("\n" + "=" * 80)

        self.stdout.write("DETAILED ENDPOINT INFORMATION")

        self.stdout.write("=" * 80)

        for endpoint in report["endpoints"]:

            self.stdout.write(f"\n📍 {endpoint['path']}")

            self.stdout.write(f"   View: {endpoint.get('view_class', 'Unknown')}")

            self.stdout.write(f"   Security Score: {endpoint['security_score']}/100")

            if endpoint["permission_classes"]:

                self.stdout.write(
                    f"   Permissions: {', '.join(endpoint['permission_classes'])}"
                )

            if endpoint["throttle_classes"]:

                self.stdout.write(
                    f"   Throttling: {', '.join(endpoint['throttle_classes'])}"
                )

            if endpoint["authentication_classes"]:

                self.stdout.write(
                    f"   Authentication: {', '.join(endpoint['authentication_classes'])}"
                )

            if endpoint["issues"]:

                self.stdout.write(self.style.ERROR("   🔴 Issues:"))

                for issue in endpoint["issues"]:

                    self.stdout.write(self.style.ERROR(f"      - {issue}"))

            if endpoint["warnings"]:

                self.stdout.write(self.style.WARNING("   🟡 Warnings:"))

                for warning in endpoint["warnings"]:

                    self.stdout.write(self.style.WARNING(f"      - {warning}"))
