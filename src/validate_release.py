#!/usr/bin/env python3
"""
Release Database Validator

Standalone script for validating BLAST databases for a specific MOD release.
This can be run independently or integrated into CI/CD pipelines.
"""

import sys
from pathlib import Path

import click

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database_validator import DatabaseValidator
from terminal import print_header, print_status


@click.command()
@click.option(
    "-m", "--mod", 
    required=True,
    type=click.Choice(['FB', 'SGD', 'WB', 'ZFIN', 'RGD'], case_sensitive=False),
    help="Model organism database (FB, SGD, WB, ZFIN, RGD)"
)
@click.option(
    "-r", "--release", 
    required=True,
    help="Release version (e.g., FB2025_03, WS297, main, prod)"
)
@click.option(
    "-b", "--base-path",
    default="/var/sequenceserver-data/blast",
    help="Base path to BLAST databases"
)
@click.option(
    "-l", "--log-dir",
    default="../logs",
    help="Directory for log files"
)
@click.option(
    "-t", "--test-sequences",
    default="../tests/fixtures",
    help="Directory containing test sequences"
)
@click.option(
    "--json-report",
    is_flag=True,
    default=False,
    help="Output detailed JSON report"
)
def validate_release(mod: str, release: str, base_path: str, log_dir: str, 
                    test_sequences: str, json_report: bool):
    """
    Validate all BLAST databases for a specific MOD release.
    
    This script performs comprehensive validation including:
    - File integrity checks
    - Database functionality tests  
    - Sequence search validation
    - Detailed logging and reporting
    
    Example usage:
    python validate_release.py -m FB -r FB2025_03
    python validate_release.py -m SGD -r main --json-report
    """
    
    print_header(f"Database Release Validation: {mod} {release}")
    
    try:
        # Initialize validator
        validator = DatabaseValidator(log_dir=log_dir, test_sequences_dir=test_sequences)
        
        print_status(f"Starting validation of {mod} {release}", "info")
        
        # Run comprehensive validation
        results = validator.validate_release(mod, release, base_path)
        
        # Handle results
        if 'error' in results:
            print_status(f"Validation failed: {results['error']}", "error")
            sys.exit(1)
        
        # Print summary
        summary = results.get('summary', {})
        total = summary.get('passed', 0) + summary.get('failed', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        
        print(f"\n=== Validation Results ===")
        print(f"Total databases: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/max(1,total))*100:.1f}%")
        print(f"Validation time: {summary.get('total_time_seconds', 0):.1f} seconds")
        
        # Output JSON report if requested
        if json_report:
            import json
            report_file = Path(log_dir) / f"validation_summary_{mod}_{release}.json"
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed JSON report: {report_file}")
        
        # Exit with appropriate code
        if failed > 0:
            print_status(f"Validation completed with {failed} failures", "warning")
            sys.exit(2)  # Warning exit code
        else:
            print_status("All databases validated successfully", "success")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print_status("Validation interrupted by user", "warning")
        sys.exit(130)
    except Exception as e:
        print_status(f"Validation error: {str(e)}", "error")
        sys.exit(1)


@click.command()
@click.option(
    "-b", "--base-path",
    default="/var/sequenceserver-data/blast",
    help="Base path to BLAST databases"
)
def list_releases(base_path: str):
    """List all available MOD releases for validation"""
    
    print_header("Available Releases for Validation")
    
    base = Path(base_path)
    if not base.exists():
        print_status(f"Base path not found: {base_path}", "error")
        sys.exit(1)
    
    mods = ['FB', 'SGD', 'WB', 'ZFIN', 'RGD']
    
    for mod in mods:
        mod_path = base / mod
        if not mod_path.exists():
            print(f"{mod}: No releases found")
            continue
            
        releases = [d.name for d in mod_path.iterdir() if d.is_dir()]
        if releases:
            print(f"{mod}: {', '.join(sorted(releases))}")
        else:
            print(f"{mod}: No releases found")


# Create CLI group
@click.group()
def cli():
    """BLAST Database Release Validation Tools"""
    pass


cli.add_command(validate_release, name='validate')
cli.add_command(list_releases, name='list')


if __name__ == "__main__":
    cli()