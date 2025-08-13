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
import warnings

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib3.exceptions import InsecureRequestWarning

# Try to import cloudscraper if available
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

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
        options.add_argument('--disable-web-security')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors-spki-list')
        
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
    
    def get_database_anchors_requests(self, mod: str, release: str) -> List[str]:
        """Get database anchor elements using requests library (fallback)."""
        url = f"{self.base_url}/{mod}/{release}"
        anchors = []
        
        # Try cloudscraper first if available
        if HAS_CLOUDSCRAPER:
            console.log(f"[yellow]Fetching with cloudscraper: {url}[/yellow]")
            try:
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url, timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find ALL elements with id containing '_anchor' (including subdivisions)
                for element in soup.find_all(id=re.compile(r'.*_anchor')):
                    anchor_id = element.get('id')
                    if anchor_id:
                        anchors.append(anchor_id)
                
                console.log(f"[green]Found {len(anchors)} anchors via cloudscraper[/green]")
                return anchors
            except Exception as e:
                console.log(f"[yellow]Cloudscraper failed, trying requests session: {e}[/yellow]")
        
        # Fallback to regular requests with session
        console.log(f"[yellow]Fetching with requests session: {url}[/yellow]")
        try:
            # Create a session with browser headers
            session = requests.Session()
            session.verify = False
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Make request with session
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find ALL elements with id containing '_anchor'
            for element in soup.find_all(id=re.compile(r'.*_anchor')):
                anchor_id = element.get('id')
                if anchor_id:
                    anchors.append(anchor_id)
            
            console.log(f"[green]Found {len(anchors)} anchors via requests[/green]")
            
        except Exception as e:
            console.log(f"[red]Requests error: {str(e)}[/red]")
        
        return anchors
    
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
            
            # Give time for JavaScript to render
            time.sleep(3)
            
            # Look for ALL elements with id containing 'anchor' (main and subdivisions)
            # This should capture both Genus_anchor and Genus_species_anchor patterns
            elements_with_anchor = self.browser.find_elements(By.XPATH, "//*[contains(@id, '_anchor')]")
            console.log(f"[yellow]Found {len(elements_with_anchor)} elements with '_anchor' in id[/yellow]")
            
            for element in elements_with_anchor:
                element_id = element.get_attribute('id')
                if element_id:
                    anchors.append(element_id)
                    # Only log first few to avoid clutter
                    if len(anchors) <= 10:
                        console.log(f"  Anchor: {element_id}")
            
            if len(anchors) > 10:
                console.log(f"  ... and {len(anchors) - 10} more anchors")
            
            # Also try to find nested/subdivision anchors by looking for patterns
            # Some sites might use different patterns for subdivisions
            subdivision_patterns = [
                "//*[contains(@id, '_') and contains(@id, '_anchor')]",  # Genus_species_anchor
                "//div[contains(@class, 'species')]//a",  # Species within divs
                "//li[contains(@class, 'database')]//a"   # Database list items
            ]
            
            for pattern in subdivision_patterns:
                try:
                    sub_elements = self.browser.find_elements(By.XPATH, pattern)
                    if sub_elements:
                        console.log(f"[cyan]Found {len(sub_elements)} elements with pattern: {pattern}[/cyan]")
                        for elem in sub_elements[:3]:  # Show first 3 examples
                            elem_id = elem.get_attribute('id') or elem.get_attribute('name')
                            if elem_id and elem_id not in anchors:
                                anchors.append(elem_id)
                                console.log(f"    Subdivision: {elem_id}")
                except Exception:
                    pass
            
            # Remove duplicates while preserving order
            anchors = list(dict.fromkeys(anchors))
            
            console.log(f"[green]Found {len(anchors)} unique database anchors for {mod}/{release}[/green]")
            
            # Log examples of found anchors for debugging
            if anchors:
                examples = anchors[:5]
                console.log(f"  Examples: {', '.join(examples)}")
                if len(anchors) > 5:
                    console.log(f"  ... and {len(anchors) - 5} more")
            
        except TimeoutException:
            console.log(f"[red]Timeout loading {url}[/red]")
        except WebDriverException as e:
            console.log(f"[red]Browser error for {url}: {str(e)}[/red]")
            # Try fallback method with requests
            console.log(f"[yellow]Falling back to requests method...[/yellow]")
            anchors = self.get_database_anchors_requests(mod, release)
        except Exception as e:
            console.log(f"[red]Error inspecting {url}: {str(e)}[/red]")
        
        return anchors
    
    def get_test_sequences(self) -> Dict[str, str]:
        """Get standard test sequences for nucleotide and protein searches."""
        return {
            "nucl": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
            "prot": "MKLLIVDDSSGKVRAEIKQLLKQGVNPEMKLLIVDDSSGKVRAEIKQLLKQGVNPE"
        }
    
    def generate_config(self, use_selenium: bool = True) -> Dict:
        """Generate complete UI test configuration."""
        console.log("[bold blue]Generating UI test configuration...[/bold blue]")
        
        config = {}
        # Use hardcoded releases from current config
        releases = {
            "FB": "FB2025_03",
            "RGD": "production",
            "SGD": "main",
            "WB": "WS297",
            "ZFIN": "prod"
        }
        test_sequences = self.get_test_sequences()
        
        console.log(f"[green]Using existing releases: {releases}[/green]")
        
        # Try to set up browser if using Selenium
        if use_selenium:
            try:
                self.setup_browser()
            except Exception as e:
                console.log(f"[yellow]Browser setup failed: {e}[/yellow]")
                console.log("[yellow]Falling back to requests-only mode[/yellow]")
                use_selenium = False
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                for mod, release in releases.items():
                    task_desc = f"Processing {mod}/{release}"
                    progress.add_task(task_desc, total=None)
                    
                    # Use requests method directly if Selenium is disabled
                    if not use_selenium:
                        anchors = self.get_database_anchors_requests(mod, release)
                    else:
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate UI test configuration')
    parser.add_argument('--no-selenium', action='store_true', 
                       help='Skip Selenium and use requests only (for server environments)')
    args = parser.parse_args()
    
    generator = UIConfigGenerator()
    
    try:
        # Generate configuration from live data
        config = generator.generate_config(use_selenium=not args.no_selenium)
        
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