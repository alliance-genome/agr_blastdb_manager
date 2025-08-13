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
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

console = Console()


class BlastUITester:
    """
    Handles automated testing of the BLAST web interface.
    """

    def __init__(self, base_url: str = "https://blast.alliancegenome.org/blast"):
        self.base_url = base_url
        self.browser = None
        self.wait_timeout = 30
        self.screenshot_count = 0

    def setup_browser(self, headless: bool = True) -> None:
        """Initialize the Chrome WebDriver with optimized settings."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Faster loading
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set up Chrome service
        try:
            self.browser = webdriver.Chrome(options=options)
            self.browser.set_page_load_timeout(self.wait_timeout)
            self.browser.implicitly_wait(10)
        except Exception as e:
            console.log(f"[red]Failed to initialize browser: {str(e)}[/red]")
            raise

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
                    # Capture error screenshot
                    if self.browser:
                        error_screenshot = output_path / f"{item}_browser_error.png"
                        try:
                            self.browser.save_screenshot(str(error_screenshot))
                            console.log(f"Error screenshot saved: {error_screenshot}")
                        except Exception:
                            pass
                except Exception as e:
                    console.log(f"[red]Unexpected error for {item}: {str(e)}[/red]")
                    # Capture error screenshot
                    if self.browser:
                        error_screenshot = output_path / f"{item}_error.png"
                        try:
                            self.browser.save_screenshot(str(error_screenshot))
                            console.log(f"Error screenshot saved: {error_screenshot}")
                        except Exception:
                            pass
                finally:
                    self.cleanup()

    def take_screenshot(self, output_path: Path, filename: str, description: str = "") -> bool:
        """Take a screenshot with optional description."""
        try:
            if not self.browser:
                return False
            
            self.screenshot_count += 1
            screenshot_path = output_path / f"{self.screenshot_count:03d}_{filename}.png"
            
            success = self.browser.save_screenshot(str(screenshot_path))
            if success:
                console.log(f"Screenshot saved: {screenshot_path}")
                if description:
                    console.log(f"Description: {description}")
                return True
            return False
        except Exception as e:
            console.log(f"[red]Failed to take screenshot: {str(e)}[/red]")
            return False

    def wait_for_element(self, by: str, value: str, timeout: int = None) -> bool:
        """Wait for element to be present with custom timeout."""
        try:
            if timeout is None:
                timeout = self.wait_timeout
            
            WebDriverWait(self.browser, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            console.log(f"[yellow]Timeout waiting for element {by}={value}[/yellow]")
            return False

    def verify_page_elements(self, expected_elements: List[str]) -> Dict[str, bool]:
        """Verify that expected elements are present on the page."""
        results = {}
        for element_id in expected_elements:
            try:
                element = self.browser.find_element(By.ID, element_id)
                results[element_id] = element.is_displayed()
            except NoSuchElementException:
                results[element_id] = False
        return results

    def run_comprehensive_test(self, mod: str, items: List[str], test_type: str,
                             sequence: str, output_dir: Path, headless: bool = True) -> Dict:
        """Run comprehensive UI tests with detailed reporting."""
        results = {
            "total_tests": len(items),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        output_path = output_dir / mod / "comprehensive"
        output_path.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for i, item in enumerate(items, 1):
                test_result = {"item": item, "success": False, "errors": [], "screenshots": []}
                task_desc = f"[{i}/{len(items)}] Testing {item}"
                progress.add_task(task_desc, total=None)
                
                try:
                    self.setup_browser(headless)
                    url = f"{self.base_url}/{mod}/{test_type}"
                    self.browser.get(url)
                    
                    # Take initial screenshot
                    self.take_screenshot(output_path, f"{item}_01_initial", "Initial page load")
                    
                    # Verify page loaded correctly
                    expected_elements = ["sequence", "method"]
                    element_check = self.verify_page_elements(expected_elements)
                    if not all(element_check.values()):
                        missing = [k for k, v in element_check.items() if not v]
                        test_result["errors"].append(f"Missing elements: {missing}")
                    
                    # Select database
                    if self.wait_for_element(By.ID, item, 15):
                        checkbox = self.browser.find_element(By.ID, item)
                        self.browser.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        checkbox.click()
                        
                        # Take screenshot after selecting database
                        self.take_screenshot(output_path, f"{item}_02_database_selected", 
                                           f"Database {item} selected")
                    else:
                        test_result["errors"].append(f"Database checkbox {item} not found")
                        continue
                    
                    # Input sequence
                    if self.wait_for_element(By.NAME, "sequence", 10):
                        input_box = self.browser.find_element(By.NAME, "sequence")
                        input_box.clear()
                        input_box.send_keys(sequence)
                        
                        # Take screenshot after entering sequence
                        self.take_screenshot(output_path, f"{item}_03_sequence_entered", 
                                           "Sequence entered")
                    else:
                        test_result["errors"].append("Sequence input box not found")
                        continue
                    
                    # Submit search
                    if self.wait_for_element(By.ID, "method", 10):
                        submit_button = self.browser.find_element(By.ID, "method")
                        submit_button.click()
                        
                        # Take screenshot after submission
                        self.take_screenshot(output_path, f"{item}_04_submitted", 
                                           "Search submitted")
                    else:
                        test_result["errors"].append("Submit button not found")
                        continue
                    
                    # Wait for results with progress screenshots
                    result_found = False
                    for attempt in range(1, 11):  # Up to 10 attempts over 600 seconds
                        if self.wait_for_element(By.ID, "view", 60):
                            result_found = True
                            break
                        else:
                            # Take progress screenshot
                            self.take_screenshot(output_path, f"{item}_05_waiting_{attempt:02d}", 
                                               f"Waiting for results - attempt {attempt}")
                    
                    if result_found:
                        # Take final results screenshot
                        self.take_screenshot(output_path, f"{item}_06_results", "Final results")
                        test_result["success"] = True
                        results["successful"] += 1
                        console.log(f"[green]✓ {item} completed successfully[/green]")
                    else:
                        test_result["errors"].append("Timeout waiting for results")
                        results["failed"] += 1
                
                except Exception as e:
                    test_result["errors"].append(str(e))
                    results["failed"] += 1
                    console.log(f"[red]✗ {item} failed: {str(e)}[/red]")
                    
                    # Take error screenshot
                    if self.browser:
                        self.take_screenshot(output_path, f"{item}_99_error", 
                                           f"Error occurred: {str(e)}")
                
                finally:
                    results["details"].append(test_result)
                    self.cleanup()
        
        return results


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
@click.option("--comprehensive", is_flag=True, 
              help="Run comprehensive tests with detailed screenshots")
@click.option("--headless/--no-headless", default=True,
              help="Run browser in headless mode")
def run_blast_tests(mod: str, type: str, single_item: int,
                    molecule: str, number_of_items: Optional[int],
                    config: str, output: str, comprehensive: bool,
                    headless: bool) -> None:
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
        
        if comprehensive:
            console.log(f"[blue]Running comprehensive tests for {mod}/{type}[/blue]")
            results = tester.run_comprehensive_test(mod, items, type, sequence, Path(output), headless)
            
            # Print summary
            console.log(f"\n[bold]Test Summary:[/bold]")
            console.log(f"Total tests: {results['total_tests']}")
            console.log(f"[green]Successful: {results['successful']}[/green]")
            console.log(f"[red]Failed: {results['failed']}[/red]")
            
            if results['failed'] > 0:
                console.log(f"\n[red]Failed tests:[/red]")
                for detail in results['details']:
                    if not detail['success']:
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