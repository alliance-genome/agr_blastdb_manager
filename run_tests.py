#!/usr/bin/env python3
"""
run_tests.py

Simple test runner script for the AGR BLAST DB Manager tests.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors."""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Success!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test runner for AGR BLAST DB Manager")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--ui", action="store_true", help="Run UI tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    # If no specific tests selected, show help
    if not any([args.unit, args.integration, args.performance, args.ui, args.all, args.install]):
        parser.print_help()
        return
    
    success_count = 0
    total_count = 0
    
    # Install dependencies if requested
    if args.install or args.all:
        total_count += 1
        if run_command(["poetry", "install", "--with", "dev"], "Installing test dependencies"):
            success_count += 1
    
    # Run unit tests
    if args.unit or args.all:
        total_count += 1
        cmd = ["poetry", "run", "pytest", "tests/test_utils.py", "tests/test_terminal.py", "tests/test_create_blast_db.py", "-v"]
        if run_command(cmd, "Running unit tests"):
            success_count += 1
    
    # Run integration tests
    if args.integration or args.all:
        total_count += 1
        cmd = ["poetry", "run", "pytest", "tests/test_integration.py", "-v"]
        if run_command(cmd, "Running integration tests"):
            success_count += 1
    
    # Run performance tests
    if args.performance or args.all:
        total_count += 1
        cmd = ["poetry", "run", "pytest", "tests/test_performance.py", "-v"]
        if run_command(cmd, "Running performance tests"):
            success_count += 1
    
    # Run UI tests (basic)
    if args.ui:
        total_count += 1
        # Check if config file exists
        config_file = Path("tests/UI/config.json")
        if config_file.exists():
            cmd = ["python", "tests/UI/test_ui.py", "-m", "WB", "-t", "nematode", "-s", "1"]
            if run_command(cmd, "Running basic UI tests"):
                success_count += 1
        else:
            print("❌ UI config file not found: tests/UI/config.json")
    
    # Generate coverage report
    if args.coverage or args.all:
        total_count += 1
        cmd = ["poetry", "run", "pytest", "tests/", "--cov=src", "--cov-report=html", "--cov-report=term"]
        if run_command(cmd, "Generating coverage report"):
            success_count += 1
            print("📊 Coverage report generated in htmlcov/index.html")
    
    # Summary
    print(f"\n📋 Test Summary: {success_count}/{total_count} operations successful")
    
    if success_count == total_count:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed or couldn't run")
        sys.exit(1)


if __name__ == "__main__":
    main()