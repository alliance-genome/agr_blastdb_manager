# test_ui.py
"""
test_ui.py

This module provides automated UI testing functionality for the BLAST web interface.
It uses Selenium WebDriver to automate browser interactions and test various BLAST
database configurations.

Features:
- Configurable test parameters for different MODs and sequence types
- Screenshot capture of test results
- Progress tracking with rich console output
- Flexible test configuration via JSON
"""

import json
import time
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

console = Console()


class BlastUITester:
    """
    Handles automated testing of the BLAST web interface.
    """

    def __init__(self, base_url: str = "https://blast.alliancegenome.org/blast"):
        self.base_url = base_url
        self.browser = None

    def setup_browser(self) -> None:
        """Initialize the Chrome WebDriver with optimized settings."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.browser = webdriver.Chrome(options=options)

    def cleanup(self) -> None:
        """Safely close the browser instance."""
        if self.browser:
            self.browser.quit()

    def run_test(self, mod: str, items: List[str], test_type: str,
                 sequence: str, output_dir: Path) -> None:
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

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
        ) as progress:

            for item in items:
                task_desc = f"Testing {item}"
                progress.add_task(task_desc, total=None)

                try:
                    self.setup_browser()
                    url = f"{self.base_url}/{mod}/{test_type}"
                    self.browser.get(url)

                    # Select database
                    checkbox = WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable((By.ID, item))
                    )
                    checkbox.click()

                    # Input sequence
                    input_box = WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable((By.NAME, "sequence"))
                    )
                    input_box.send_keys(sequence)

                    # Submit search
                    submit_button = WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable((By.ID, "method"))
                    )
                    submit_button.click()

                    # Wait for results and capture screenshot
                    WebDriverWait(self.browser, 600).until(
                        EC.presence_of_element_located((By.ID, "view"))
                    )
                    screenshot_path = output_path / f"{item}.png"
                    self.browser.save_screenshot(str(screenshot_path))
                    console.log(f"Screenshot saved: {screenshot_path}")

                except TimeoutException:
                    console.log(f"[red]Timeout waiting for results: {item}[/red]")
                except WebDriverException as e:
                    console.log(f"[red]Browser error for {item}: {str(e)}[/red]")
                except Exception as e:
                    console.log(f"[red]Unexpected error for {item}: {str(e)}[/red]")
                finally:
                    self.cleanup()


@click.command()
@click.option("-m", "--mod", required=True, help="Model organism database to test")
@click.option("-t", "--type", required=True, help="Database type (e.g., fungal for SGD)")
@click.option("-s", "--single_item", type=int, default=1, help="Number of items to test")
@click.option("-M", "--molecule", type=click.Choice(['nucl', 'prot']),
              default="nucl", help="Molecule type to test")
@click.option("-n", "--number_of_items", type=int, help="Number of random items to test")
@click.option("-c", "--config", type=click.Path(exists=True),
              default="config.json", help="Path to configuration file")
@click.option("-o", "--output", type=click.Path(),
              default="output", help="Output directory for screenshots")
def run_blast_tests(mod: str, type: str, single_item: int,
                    molecule: str, number_of_items: Optional[int],
                    config: str, output: str) -> None:
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

        tester = BlastUITester()
        tester.run_test(mod, items, type, sequence, Path(output))

    except json.JSONDecodeError:
        console.log("[red]Error: Invalid JSON configuration file[/red]")
    except Exception as e:
        console.log(f"[red]Error: {str(e)}[/red]")
        raise click.Abort()


if __name__ == "__main__":
    run_blast_tests()