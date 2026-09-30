# test_ui.py
"""
test_ui.py

This module provides automated UI testing functionality for the BLAST web interface.
It uses Playwright to automate browser interactions and test various BLAST
database configurations.

Features:
- Configurable test parameters for different MODs and sequence types
- Screenshot capture of test results
- Progress tracking with rich console output
- Flexible test configuration via JSON

Browsers are managed by Playwright: run `uv run playwright install chromium`
once, or pass `--browser-channel chrome` to drive an installed Google Chrome.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import click
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def by_id(element_id: str) -> str:
    """CSS selector for an id that may not be a valid CSS identifier."""
    return f'[id="{element_id}"]'


SEQUENCE_INPUT = '[name="sequence"]'
SUBMIT_BUTTON = by_id("method")
RESULTS_VIEW = by_id("view")


class BlastUITester:
    """
    Handles automated testing of the BLAST web interface.

    One browser is launched per run; every tested database gets a fresh
    browser context (its own cookies, storage and page), so items stay
    isolated without paying for a browser start each time.
    """

    def __init__(
        self,
        base_url: str = "https://blast.alliancegenome.org/blast",
        browser_channel: Optional[str] = None,
        wait_timeout: int = 30,
        result_timeout: int = 600,
    ):
        self.base_url = base_url
        self.browser_channel = browser_channel
        self.wait_timeout = wait_timeout  # seconds, for page loads and elements
        self.result_timeout = result_timeout  # seconds, for BLAST results
        self.screenshot_count = 0
        self._playwright = None
        self.browser = None
        self.page = None

    def setup_browser(self, headless: bool = True) -> None:
        """Launch the browser (once) and open a fresh page for the next item."""
        if self.browser is None:
            self._playwright = sync_playwright().start()
            try:
                self.browser = self._playwright.chromium.launch(
                    headless=headless, channel=self.browser_channel
                )
            except PlaywrightError as e:
                console.log(f"[red]Failed to launch browser: {str(e)}[/red]")
                console.log(
                    "[yellow]Install the Playwright browser with: "
                    "uv run playwright install chromium "
                    "(or pass --browser-channel chrome to use an installed Chrome)[/yellow]"
                )
                self.cleanup()
                raise
            console.log("[green]✓ Browser initialized successfully[/green]")

        self.close_page()
        context = self.browser.new_context(viewport={"width": 1920, "height": 1080})
        context.set_default_timeout(self.wait_timeout * 1000)
        self.page = context.new_page()

    def close_page(self) -> None:
        """Close the current page and its context, keeping the browser."""
        if self.page:
            try:
                self.page.context.close()
            finally:
                self.page = None

    def cleanup(self) -> None:
        """Safely close the page, the browser and Playwright."""
        self.close_page()
        if self.browser:
            self.browser.close()
            self.browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def search_url(self, mod: str, test_type: str) -> str:
        return f"{self.base_url}/{mod}/{test_type}"

    def run_test(
        self, mod: str, items: List[str], test_type: str, sequence: str, output_dir: Path
    ) -> None:
        """
        Run UI tests for specified BLAST configurations.

        Args:
            mod: Model organism database identifier
            items: List of UI elements to test
            test_type: Type of BLAST search
            sequence: Input sequence for BLAST
            output_dir: Directory for saving screenshots
        """
        # Ensure output directory exists
        output_path = output_dir / mod
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                for item in items:
                    progress.add_task(f"Testing {item}", total=None)

                    try:
                        self.setup_browser()
                        page = self.page
                        page.goto(self.search_url(mod, test_type))

                        # Select database, enter the sequence and submit
                        page.locator(by_id(item)).click()
                        page.locator(SEQUENCE_INPUT).fill(sequence)
                        page.locator(SUBMIT_BUTTON).click()

                        # Wait for results and capture screenshot
                        page.locator(RESULTS_VIEW).wait_for(
                            state="attached", timeout=self.result_timeout * 1000
                        )
                        screenshot_path = output_path / f"{item}.png"
                        page.screenshot(path=str(screenshot_path))
                        console.log(f"Screenshot saved: {screenshot_path}")

                    except PlaywrightTimeoutError:
                        console.log(f"[red]Timeout waiting for results: {item}[/red]")
                    except PlaywrightError as e:
                        console.log(f"[red]Browser error for {item}: {str(e)}[/red]")
                        self._error_screenshot(output_path / f"{item}_browser_error.png")
                    except Exception as e:
                        console.log(f"[red]Unexpected error for {item}: {str(e)}[/red]")
                        self._error_screenshot(output_path / f"{item}_error.png")
                    finally:
                        self.close_page()
        finally:
            self.cleanup()

    def _error_screenshot(self, path: Path) -> None:
        if self.page:
            try:
                self.page.screenshot(path=str(path))
                console.log(f"Error screenshot saved: {path}")
            except Exception:
                pass

    def take_screenshot(
        self, output_path: Path, filename: str, description: str = ""
    ) -> bool:
        """Take a screenshot with optional description."""
        try:
            if not self.page:
                return False

            self.screenshot_count += 1
            screenshot_path = (
                output_path / f"{self.screenshot_count:03d}_{filename}.png"
            )
            self.page.screenshot(path=str(screenshot_path))
            console.log(f"Screenshot saved: {screenshot_path}")
            if description:
                console.log(f"Description: {description}")
            return True
        except Exception as e:
            console.log(f"[red]Failed to take screenshot: {str(e)}[/red]")
            return False

    def wait_for_element(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for an element matching a CSS selector to be attached."""
        if timeout is None:
            timeout = self.wait_timeout
        try:
            self.page.locator(selector).first.wait_for(
                state="attached", timeout=timeout * 1000
            )
            return True
        except PlaywrightTimeoutError:
            console.log(f"[yellow]Timeout waiting for element {selector}[/yellow]")
            return False

    def verify_page_elements(self, expected_elements: List[str]) -> Dict[str, bool]:
        """Verify that elements with the expected ids are visible on the page."""
        return {
            element_id: self.page.locator(by_id(element_id)).first.is_visible()
            for element_id in expected_elements
        }

    def run_comprehensive_test(
        self,
        mod: str,
        items: List[str],
        test_type: str,
        sequence: str,
        output_dir: Path,
        headless: bool = True,
    ) -> Dict:
        """Run comprehensive UI tests with detailed reporting."""
        results = {
            "total_tests": len(items),
            "successful": 0,
            "failed": 0,
            "details": [],
        }

        output_path = output_dir / mod / "comprehensive"
        output_path.mkdir(parents=True, exist_ok=True)

        # Results are polled in slices so progress screenshots can be taken.
        attempts = 10
        attempt_timeout = max(1, self.result_timeout // attempts)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                for i, item in enumerate(items, 1):
                    test_result = {
                        "item": item,
                        "success": False,
                        "errors": [],
                        "screenshots": [],
                    }
                    progress.add_task(f"[{i}/{len(items)}] Testing {item}", total=None)

                    try:
                        self.setup_browser(headless)
                        page = self.page
                        page.goto(self.search_url(mod, test_type))

                        # Take initial screenshot
                        self.take_screenshot(
                            output_path, f"{item}_01_initial", "Initial page load"
                        )

                        # Verify page loaded correctly
                        element_check = self.verify_page_elements(["sequence", "method"])
                        if not all(element_check.values()):
                            missing = [k for k, v in element_check.items() if not v]
                            test_result["errors"].append(f"Missing elements: {missing}")

                        # Select database (Playwright scrolls it into view)
                        if not self.wait_for_element(by_id(item), 15):
                            test_result["errors"].append(
                                f"Database checkbox {item} not found"
                            )
                            continue
                        page.locator(by_id(item)).click()
                        self.take_screenshot(
                            output_path,
                            f"{item}_02_database_selected",
                            f"Database {item} selected",
                        )

                        # Input sequence
                        if not self.wait_for_element(SEQUENCE_INPUT, 10):
                            test_result["errors"].append("Sequence input box not found")
                            continue
                        page.locator(SEQUENCE_INPUT).fill(sequence)
                        self.take_screenshot(
                            output_path, f"{item}_03_sequence_entered", "Sequence entered"
                        )

                        # Submit search
                        if not self.wait_for_element(SUBMIT_BUTTON, 10):
                            test_result["errors"].append("Submit button not found")
                            continue
                        page.locator(SUBMIT_BUTTON).click()
                        self.take_screenshot(
                            output_path, f"{item}_04_submitted", "Search submitted"
                        )

                        # Wait for results with progress screenshots
                        result_found = False
                        for attempt in range(1, attempts + 1):
                            if self.wait_for_element(RESULTS_VIEW, attempt_timeout):
                                result_found = True
                                break
                            self.take_screenshot(
                                output_path,
                                f"{item}_05_waiting_{attempt:02d}",
                                f"Waiting for results - attempt {attempt}",
                            )

                        if result_found:
                            self.take_screenshot(
                                output_path, f"{item}_06_results", "Final results"
                            )
                            test_result["success"] = True
                            console.log(f"[green]✓ {item} completed successfully[/green]")
                        else:
                            test_result["errors"].append("Timeout waiting for results")

                    except Exception as e:
                        test_result["errors"].append(str(e))
                        console.log(f"[red]✗ {item} failed: {str(e)}[/red]")
                        self.take_screenshot(
                            output_path, f"{item}_99_error", f"Error occurred: {str(e)}"
                        )

                    finally:
                        # Every item counts once, including early exits above.
                        if test_result["success"]:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                        results["details"].append(test_result)
                        self.close_page()
        finally:
            self.cleanup()

        return results


@click.command()
@click.option("-m", "--mod", required=True, help="Model organism database to test")
@click.option("-t", "--type", required=True, help="Database type (e.g., fungal for SGD)")
@click.option("-s", "--single_item", type=int, default=1, help="Number of items to test")
@click.option(
    "-M",
    "--molecule",
    type=click.Choice(["nucl", "prot"]),
    default="nucl",
    help="Molecule type to test",
)
@click.option("-n", "--number_of_items", type=int, help="Number of random items to test")
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    default="config.json",
    help="Path to configuration file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="output",
    help="Output directory for screenshots",
)
@click.option(
    "--comprehensive", is_flag=True, help="Run comprehensive tests with detailed screenshots"
)
@click.option(
    "--headless/--no-headless", default=True, help="Run browser in headless mode"
)
@click.option(
    "--base-url",
    default="https://blast.alliancegenome.org/blast",
    show_default=True,
    help="BLAST web interface to test",
)
@click.option(
    "--browser-channel",
    default=None,
    help="Use an installed browser instead of Playwright's Chromium (e.g. chrome, msedge)",
)
def run_blast_tests(
    mod: str,
    type: str,
    single_item: int,
    molecule: str,
    number_of_items: Optional[int],
    config: str,
    output: str,
    comprehensive: bool,
    headless: bool,
    base_url: str,
    browser_channel: Optional[str],
) -> None:
    """
    Run automated tests for the BLAST web interface.

    This command-line tool allows testing of various BLAST database configurations
    with customizable parameters and automated browser interaction.
    """
    try:
        with open(config) as f:
            config_data = json.load(f)

        if mod not in config_data or type not in config_data[mod]:
            raise click.BadParameter(f"Invalid MOD/type combination: {mod}/{type}")

        items = config_data[mod][type]["items"]
        sequence = config_data[mod][type][molecule]

        if number_of_items and number_of_items < len(items):
            import random

            items = random.sample(items, number_of_items)
        elif single_item > 1:
            items = items[:single_item]

        tester = BlastUITester(base_url=base_url, browser_channel=browser_channel)

        if comprehensive:
            console.log(f"[blue]Running comprehensive tests for {mod}/{type}[/blue]")
            results = tester.run_comprehensive_test(
                mod, items, type, sequence, Path(output), headless
            )

            # Print summary
            console.log("\n[bold]Test Summary:[/bold]")
            console.log(f"Total tests: {results['total_tests']}")
            console.log(f"[green]Successful: {results['successful']}[/green]")
            console.log(f"[red]Failed: {results['failed']}[/red]")

            if results["failed"] > 0:
                console.log("\n[red]Failed tests:[/red]")
                for detail in results["details"]:
                    if not detail["success"]:
                        console.log(f"- {detail['item']}: {', '.join(detail['errors'])}")
        else:
            tester.run_test(mod, items, type, sequence, Path(output))

    except json.JSONDecodeError:
        console.log("[red]Error: Invalid JSON configuration file[/red]")
    except Exception as e:
        console.log(f"[red]Error: {str(e)}[/red]")
        raise click.Abort()


if __name__ == "__main__":
    run_blast_tests()
