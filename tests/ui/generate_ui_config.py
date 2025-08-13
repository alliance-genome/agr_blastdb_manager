#!/usr/bin/env python3
"""
generate_ui_config.py

Generate UI test configuration by:
1. Finding the latest release for each MOD from /var/sequenceserver-data
2. Inspecting the actual BLAST UI to find the real anchor elements
3. Creating a proper config.json for testing
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

console = Console()


class UIConfigGenerator:
    """Generate UI test configuration from actual data."""
    
    def __init__(self, base_url: str = "https://blast.alliancegenome.org/blast"):
        self.base_url = base_url
        self.data_path = Path("/var/sequenceserver-data")
        self.browser = None
        
    def setup_browser(self) -> None:
        """Initialize browser for UI inspection."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.browser = webdriver.Chrome(options=options)
            self.browser.set_page_load_timeout(30)
            console.log("[green]✓ Browser initialized[/green]")
        except Exception as e:
            console.log(f"[red]Failed to initialize browser: {str(e)}[/red]")
            raise
    
    def cleanup(self) -> None:
        """Clean up browser resources."""
        if self.browser:
            self.browser.quit()
    
    def get_latest_releases(self) -> Dict[str, str]:
        """Get the latest release for each MOD from the filesystem."""
        releases = {}
        blast_path = self.data_path / "blast"
        
        if not blast_path.exists():
            console.log(f"[red]BLAST data path not found: {blast_path}[/red]")
            return releases
        
        console.log("[blue]Finding latest releases...[/blue]")
        
        # Check each MOD directory
        for mod_dir in blast_path.iterdir():
            if not mod_dir.is_dir():
                continue
                
            mod_name = mod_dir.name
            console.log(f"Checking {mod_name}...")
            
            # Get all release directories for this MOD
            release_dirs = []
            for release_dir in mod_dir.iterdir():
                if release_dir.is_dir():
                    release_dirs.append(release_dir.name)
            
            if not release_dirs:
                console.log(f"[yellow]No releases found for {mod_name}[/yellow]")
                continue
            
            # Sort to get the latest
            if mod_name == "FB":
                # FB uses format FB2025_01, FB2025_03, etc.
                latest = max(release_dirs, key=lambda x: (
                    int(re.search(r'FB(\d{4})', x).group(1)) if re.search(r'FB(\d{4})', x) else 0,
                    int(re.search(r'_(\d+)', x).group(1)) if re.search(r'_(\d+)', x) else 0
                ))
            elif mod_name == "WB":
                # WB uses WS292, WS293, etc. (exclude 'dev')
                ws_releases = [r for r in release_dirs if r.startswith('WS') and r != 'dev']
                if ws_releases:
                    latest = max(ws_releases, key=lambda x: int(re.search(r'WS(\d+)', x).group(1)))
                else:
                    latest = "dev"
            else:
                # For SGD (main/fungal), RGD (production), ZFIN (prod)
                if "main" in release_dirs:
                    latest = "main"
                elif "fungal" in release_dirs:
                    latest = "fungal"
                elif "production" in release_dirs:
                    latest = "production"
                elif "prod" in release_dirs:
                    latest = "prod"
                else:
                    latest = max(release_dirs)  # Fallback to alphabetically last
            
            releases[mod_name] = latest
            console.log(f"[green]✓ {mod_name}: {latest}[/green]")
        
        return releases
    
    def get_database_anchors(self, mod: str, release: str) -> List[str]:
        """Get database anchor elements from the actual UI."""
        url = f"{self.base_url}/{mod}/{release}"
        console.log(f"Inspecting UI: {url}")
        
        anchors = []
        
        try:
            self.browser.get(url)
            
            # Wait for page to load
            WebDriverWait(self.browser, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for database checkboxes/inputs
            # Common patterns: input[type="checkbox"], input[id*="anchor"], etc.
            checkbox_selectors = [
                "input[type='checkbox'][id*='anchor']",
                "input[type='checkbox'][id*='_anchor']", 
                "input[type='checkbox']",
                "input[id*='anchor']",
                ".database-checkbox",
                "[data-database]"
            ]
            
            for selector in checkbox_selectors:
                try:
                    elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        element_id = element.get_attribute('id')
                        if element_id and 'anchor' in element_id.lower():
                            anchors.append(element_id)
                    
                    if anchors:
                        console.log(f"Found {len(anchors)} anchors with selector: {selector}")
                        break
                        
                except Exception as e:
                    continue
            
            # If no anchors found with checkboxes, try other elements
            if not anchors:
                # Look for any elements with 'anchor' in the id
                try:
                    elements = self.browser.find_elements(By.XPATH, "//*[contains(@id, 'anchor')]")
                    for element in elements:
                        element_id = element.get_attribute('id')
                        if element_id:
                            anchors.append(element_id)
                except Exception:
                    pass
            
            # Remove duplicates while preserving order
            anchors = list(dict.fromkeys(anchors))
            
            console.log(f"[green]Found {len(anchors)} database anchors for {mod}/{release}[/green]")
            
        except TimeoutException:
            console.log(f"[red]Timeout loading {url}[/red]")
        except WebDriverException as e:
            console.log(f"[red]Browser error for {url}: {str(e)}[/red]")
        except Exception as e:
            console.log(f"[red]Error inspecting {url}: {str(e)}[/red]")
        
        return anchors
    
    def get_test_sequences(self) -> Dict[str, str]:
        """Get standard test sequences for nucleotide and protein searches."""
        return {
            "nucl": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
            "prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPEMKLLIVDDSSGKVRAEIKQLLKQGVNPE"
        }
    
    def generate_config(self) -> Dict:
        """Generate complete UI test configuration."""
        console.log("[bold blue]Generating UI test configuration...[/bold blue]")
        
        config = {}
        releases = self.get_latest_releases()
        test_sequences = self.get_test_sequences()
        
        if not releases:
            console.log("[red]No releases found![/red]")
            return config
        
        self.setup_browser()
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                for mod, release in releases.items():
                    task_desc = f"Processing {mod}/{release}"
                    progress.add_task(task_desc, total=None)
                    
                    anchors = self.get_database_anchors(mod, release)
                    
                    if anchors:
                        config[mod] = {
                            release: {
                                "url": f"{self.base_url}/{mod}/{release}",
                                "nucl": test_sequences["nucl"],
                                "prot": test_sequences["prot"],
                                "items": sorted(anchors)  # Sort for consistency
                            }
                        }
                        console.log(f"[green]✓ {mod}/{release}: {len(anchors)} databases[/green]")
                    else:
                        console.log(f"[yellow]⚠ {mod}/{release}: No databases found[/yellow]")
                
        finally:
            self.cleanup()
        
        return config
    
    def save_config(self, config: Dict, output_path: str = "tests/UI/config.json") -> None:
        """Save configuration to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=True)
        
        console.log(f"[green]✓ Configuration saved to: {output_file}[/green]")
    
    def validate_config(self, config: Dict) -> bool:
        """Validate the generated configuration."""
        if not config:
            console.log("[red]✗ Empty configuration[/red]")
            return False
        
        console.log("[blue]Validating configuration...[/blue]")
        
        valid = True
        total_databases = 0
        
        for mod, mod_data in config.items():
            for release, release_data in mod_data.items():
                required_fields = ["url", "nucl", "prot", "items"]
                
                for field in required_fields:
                    if field not in release_data:
                        console.log(f"[red]✗ Missing {field} in {mod}/{release}[/red]")
                        valid = False
                
                if "items" in release_data:
                    db_count = len(release_data["items"])
                    total_databases += db_count
                    console.log(f"[green]✓ {mod}/{release}: {db_count} databases[/green]")
                    
                    if db_count == 0:
                        console.log(f"[yellow]⚠ {mod}/{release}: No databases found[/yellow]")
        
        console.log(f"[bold]Total databases across all MODs: {total_databases}[/bold]")
        
        if valid:
            console.log("[green]✓ Configuration is valid[/green]")
        else:
            console.log("[red]✗ Configuration has errors[/red]")
        
        return valid


def main():
    """Main function to generate UI configuration."""
    generator = UIConfigGenerator()
    
    try:
        # Generate configuration from live data
        config = generator.generate_config()
        
        if config:
            # Save configuration
            generator.save_config(config)
            
            # Validate configuration
            is_valid = generator.validate_config(config)
            
            if is_valid:
                console.log("[bold green]🎉 UI configuration generated successfully![/bold green]")
                console.log("\n[bold]Usage examples:[/bold]")
                
                for mod, mod_data in config.items():
                    for release in mod_data.keys():
                        console.log(f"python tests/UI/test_ui.py -m {mod} -t {release} -s 3 -c tests/UI/config.json")
                
            else:
                console.log("[red]❌ Configuration generated but has validation errors[/red]")
                
        else:
            console.log("[red]❌ Failed to generate configuration[/red]")
            
    except Exception as e:
        console.log(f"[red]Error: {str(e)}[/red]")
        raise


if __name__ == "__main__":
    main()