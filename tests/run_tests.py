#!/usr/bin/env python3
"""
Comprehensive test runner for AGR BLAST Database Manager.

This script provides easy access to all test categories with proper environment setup.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

console = Console()

class TestRunner:
    """Manages test execution across different categories."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
    
    def run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and return success status."""
        console.log(f"[blue]Running: {description}[/blue]")
        console.log(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            if result.returncode == 0:
                console.log(f"[green]✓ {description} completed successfully[/green]")
                if result.stdout.strip():
                    console.log(result.stdout)
                return True
            else:
                console.log(f"[red]✗ {description} failed[/red]")
                if result.stderr:
                    console.log(f"[red]Error: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.log(f"[red]Failed to run {description}: {str(e)}[/red]")
            return False
    
    def run_unit_tests(self, verbose: bool = False) -> bool:
        """Run all unit tests."""
        cmd = ["uv", "run", "pytest", "tests/unit/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd, "Unit tests")
    
    def run_integration_tests(self, verbose: bool = False) -> bool:
        """Run integration tests."""
        cmd = ["uv", "run", "pytest", "tests/integration/"]
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        return self.run_command(cmd, "Integration tests")
    
    def run_performance_tests(self, verbose: bool = False) -> bool:
        """Run performance tests."""
        cmd = ["uv", "run", "pytest", "tests/performance/test_performance.py"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd, "Performance tests")
    
    def run_ui_tests(self, mod: str = "WB", release: str = "WS297", 
                     comprehensive: bool = False) -> bool:
        """Run UI tests."""
        cmd = ["uv", "run", "python", "tests/ui/test_ui.py", "-m", mod, "-t", release]
        if comprehensive:
            cmd.append("--comprehensive")
        cmd.extend(["-c", "tests/ui/config.json"])
        
        return self.run_command(cmd, f"UI tests ({mod}/{release})")
    
    def run_cli_tests(self) -> bool:
        """Run CLI tests."""
        cmd = ["uv", "run", "python", "tests/cli/test_cli.py", "--help"]
        return self.run_command(cmd, "CLI tests (help)")
    
    def run_coverage_report(self) -> bool:
        """Generate coverage report."""
        cmd = ["uv", "run", "pytest", "tests/", "--cov=src", "--cov-report=html", "--cov-report=term"]
        return self.run_command(cmd, "Coverage report generation")
    
    def run_load_tests(self, users: int = 5, duration: str = "2m") -> bool:
        """Run load tests with Locust."""
        cmd = [
            "uv", "run", "locust", 
            "-f", "tests/performance/load_testing/locustfile.py",
            "--host=https://blast.alliancegenome.org",
            "-u", str(users), "-r", "1", "-t", duration,
            "--headless"
        ]
        return self.run_command(cmd, f"Load tests ({users} users, {duration})")
    
    def run_all_tests(self, verbose: bool = False) -> None:
        """Run all test categories and provide summary."""
        results = {}
        
        console.log("[bold blue]Running comprehensive test suite...[/bold blue]")
        
        # Unit tests
        results["Unit Tests"] = self.run_unit_tests(verbose)
        
        # Integration tests
        results["Integration Tests"] = self.run_integration_tests(verbose)
        
        # Performance tests
        results["Performance Tests"] = self.run_performance_tests(verbose)
        
        # UI tests (limited)
        results["UI Tests"] = self.run_ui_tests()
        
        # Coverage report
        results["Coverage Report"] = self.run_coverage_report()
        
        # Print summary
        self.print_summary(results)
    
    def print_summary(self, results: dict) -> None:
        """Print test execution summary."""
        console.log("\n[bold]Test Execution Summary:[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test Category", style="cyan")
        table.add_column("Status", style="green")
        
        for category, success in results.items():
            status = "✓ PASSED" if success else "✗ FAILED"
            style = "green" if success else "red"
            table.add_row(category, f"[{style}]{status}[/{style}]")
        
        console.print(table)
        
        # Overall status
        all_passed = all(results.values())
        if all_passed:
            console.log("[bold green]🎉 All tests passed![/bold green]")
        else:
            console.log("[bold red]❌ Some tests failed. Check output above.[/bold red]")
    
    def list_available_tests(self) -> None:
        """List all available test categories."""
        console.log("[bold]Available test categories:[/bold]")
        
        categories = [
            ("unit", "Unit tests for individual components", "tests/unit/"),
            ("integration", "End-to-end integration tests", "tests/integration/"),
            ("performance", "Performance and benchmarking tests", "tests/performance/"),
            ("ui", "User interface tests with Selenium", "tests/ui/"),
            ("cli", "Command-line interface tests", "tests/cli/"),
            ("load", "Load testing with Locust", "tests/performance/load_testing/")
        ]
        
        for name, description, path in categories:
            console.log(f"[cyan]{name:12}[/cyan] - {description}")
            console.log(f"             Path: {path}")


def main():
    """Main test runner interface."""
    parser = argparse.ArgumentParser(description="AGR BLAST Database Manager Test Runner")
    
    parser.add_argument("category", nargs="?", default="all",
                       choices=["all", "unit", "integration", "performance", "ui", "cli", "load", "coverage", "list"],
                       help="Test category to run")
    
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    
    # UI test options
    parser.add_argument("--mod", default="WB", help="MOD for UI tests")
    parser.add_argument("--release", default="WS297", help="Release for UI tests")
    parser.add_argument("--comprehensive", action="store_true", help="Comprehensive UI testing")
    
    # Load test options
    parser.add_argument("--users", type=int, default=5, help="Number of users for load testing")
    parser.add_argument("--duration", default="2m", help="Duration for load testing")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)
    
    if args.category == "list":
        runner.list_available_tests()
        return
    
    if args.category == "all":
        runner.run_all_tests(args.verbose)
    elif args.category == "unit":
        runner.run_unit_tests(args.verbose)
    elif args.category == "integration":
        runner.run_integration_tests(args.verbose)
    elif args.category == "performance":
        runner.run_performance_tests(args.verbose)
    elif args.category == "ui":
        runner.run_ui_tests(args.mod, args.release, args.comprehensive)
    elif args.category == "cli":
        runner.run_cli_tests()
    elif args.category == "load":
        runner.run_load_tests(args.users, args.duration)
    elif args.category == "coverage":
        runner.run_coverage_report()


if __name__ == "__main__":
    main()