#!/usr/bin/env python3
"""
validate_databases.py

Standalone CLI tool for validating BLAST databases.
Can be run independently of the main pipeline for manual validation, QA, or CI/CD integration.

Usage:
    python validate_databases.py --mod FB --validation-path /var/sequenceserver-data/blast
    python validate_databases.py --mod SGD --html-report --json-export
    python validate_databases.py --all-mods --html-report

Authors: Paulo Nuin, Adam Wright
Date: January 2025
"""

import logging
import sys
from pathlib import Path

import click

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from terminal import log_error, log_success, log_warning, print_header, print_status
from validation import DatabaseValidator
from validation_reporter import ValidationReporter


def setup_logger():
    """Setup basic logger for CLI tool."""
    logger = logging.getLogger("validate_databases")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


@click.command()
@click.option(
    "-m",
    "--mod",
    help="Model organism to validate (FB, SGD, WB, ZFIN, RGD, XB)",
    type=click.Choice(["FB", "SGD", "WB", "ZFIN", "RGD", "XB"], case_sensitive=False),
)
@click.option(
    "--all-mods",
    is_flag=True,
    default=False,
    help="Validate all MODs",
)
@click.option(
    "--validation-path",
    default="/var/sequenceserver-data/blast",
    help="Base path to BLAST databases (default: /var/sequenceserver-data/blast)",
)
@click.option(
    "--html-report",
    is_flag=True,
    default=False,
    help="Generate HTML validation report",
)
@click.option(
    "--json-export",
    is_flag=True,
    default=False,
    help="Export validation results as JSON",
)
@click.option(
    "--report-dir",
    default="../reports",
    help="Directory for saving reports (default: ../reports)",
)
@click.option(
    "--log-dir",
    default="../logs",
    help="Directory for log files (default: ../logs)",
)
@click.option(
    "--evalue",
    default="10",
    help="E-value threshold for BLAST (default: 10)",
)
@click.option(
    "--word-size",
    default="7",
    help="BLAST word size (default: 7)",
)
@click.option(
    "--skip-file-checks",
    is_flag=True,
    default=False,
    help="Skip file integrity checks",
)
@click.option(
    "--skip-integrity-checks",
    is_flag=True,
    default=False,
    help="Skip blastdbcmd integrity checks",
)
def validate(
    mod: str,
    all_mods: bool,
    validation_path: str,
    html_report: bool,
    json_export: bool,
    report_dir: str,
    log_dir: str,
    evalue: str,
    word_size: str,
    skip_file_checks: bool,
    skip_integrity_checks: bool,
):
    """
    Validate BLAST databases for quality assurance.

    This standalone tool performs comprehensive database validation including:
    - File integrity checks (.nin, .nhr, .nsq files)
    - Database functionality (blastdbcmd -info)
    - Search capability (BLAST with conserved sequences)
    - Detailed logging and optional HTML/JSON reports

    Examples:
        # Validate single MOD
        python validate_databases.py --mod FB

        # Validate all MODs with HTML report
        python validate_databases.py --all-mods --html-report

        # Validate with JSON export for CI/CD
        python validate_databases.py --mod SGD --json-export

        # Custom validation path
        python validate_databases.py --mod WB --validation-path /custom/path
    """
    print_header("AGR BLAST Database Validation Tool")

    # Validate arguments
    if not mod and not all_mods:
        log_error("Please specify --mod or --all-mods")
        sys.exit(1)

    if mod and all_mods:
        log_error("Cannot specify both --mod and --all-mods")
        sys.exit(1)

    # Setup logger
    logger = setup_logger()

    try:
        # Initialize validator
        print_status("Initializing validator...", "info")
        validator = DatabaseValidator(
            logger=logger,
            evalue=evalue,
            word_size=word_size,
            log_dir=log_dir,
            enable_file_checks=not skip_file_checks,
            enable_integrity_checks=not skip_integrity_checks,
        )

        # Determine MOD filter
        mod_filter = None if all_mods else mod

        # Run validation
        print_status(f"Validating databases in: {validation_path}", "info")
        validation_results = validator.validate_all(validation_path, mod_filter=mod_filter)

        if not validation_results:
            log_warning("No databases found or validation failed")
            sys.exit(2)

        # Calculate overall statistics
        total_dbs = sum(r.get("total", 0) for r in validation_results.values())
        total_passed = sum(r.get("passed", 0) for r in validation_results.values())
        total_failed = sum(r.get("failed", 0) for r in validation_results.values())
        success_rate = (total_passed / max(1, total_dbs)) * 100

        # Print summary
        print("\n" + "=" * 60)
        print(f"Validation Summary")
        print("=" * 60)
        print(f"Total Databases: {total_dbs}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 60 + "\n")

        # Generate reports if requested
        if html_report or json_export:
            print_status("Generating reports...", "info")
            reporter = ValidationReporter(report_dir=report_dir)

            # Prepare results for reporting
            report_data = {
                "mod": "All MODs" if all_mods else mod,
                "timestamp": validator.validation_log_file,
                "evalue": evalue,
                "word_size": word_size,
                "total_databases": total_dbs,
                "passed": total_passed,
                "failed": total_failed,
                "duration": "N/A",
                "all_results": validation_results,
            }

            if html_report:
                html_path = reporter.generate_html_report(report_data)
                log_success(f"HTML report generated: {html_path}")

            if json_export:
                json_path = reporter.generate_json_export(report_data)
                log_success(f"JSON export created: {json_path}")

        # Log validation log location
        print_status(
            f"Detailed validation log: {validator.validation_log_file}", "info"
        )

        # Exit with appropriate code
        if total_failed > 0:
            log_warning(
                f"Validation completed with {total_failed} failures - see logs for details"
            )
            sys.exit(2)  # Exit code 2 for validation failures
        else:
            log_success("All databases validated successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        print_status("\nValidation interrupted by user", "warning")
        sys.exit(130)
    except Exception as e:
        log_error(f"Validation error: {str(e)}")
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        sys.exit(1)


@click.command()
@click.option(
    "--validation-path",
    default="/var/sequenceserver-data/blast",
    help="Base path to BLAST databases",
)
def list_databases(validation_path: str):
    """List all available databases for validation."""
    print_header("Available Databases")

    base = Path(validation_path)
    if not base.exists():
        log_error(f"Validation path does not exist: {validation_path}")
        sys.exit(1)

    mods = ["FB", "SGD", "WB", "ZFIN", "RGD", "XB"]

    print(f"Base path: {validation_path}\n")

    total_dbs = 0
    for mod in mods:
        mod_path = base / mod
        if not mod_path.exists():
            print(f"{mod}: No databases found")
            continue

        # Count databases
        nin_files = list(mod_path.rglob("*.nin"))
        pin_files = list(mod_path.rglob("*.pin"))
        db_count = len(set([f.stem for f in nin_files + pin_files]))

        if db_count > 0:
            print(f"{mod}: {db_count} databases")
            total_dbs += db_count

            # Show releases if organized by release
            releases = [
                d.name for d in mod_path.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]
            if releases:
                print(f"  Releases: {', '.join(sorted(releases))}")
        else:
            print(f"{mod}: No databases found")

    print(f"\nTotal: {total_dbs} databases across all MODs")


@click.group()
def cli():
    """AGR BLAST Database Validation CLI"""
    pass


cli.add_command(validate)
cli.add_command(list_databases, name="list")


if __name__ == "__main__":
    cli()
