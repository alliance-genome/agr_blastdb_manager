#!/usr/bin/env python3
"""
Proper BLAST UI Validation Testing

This performs ACTUAL BLAST testing by:
1. Selecting specific database checkboxes
2. Submitting BLAST searches
3. Waiting for real results
4. Validating hits are returned
5. Capturing meaningful screenshots of results
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# Test sequences for BLAST validation - highly conserved sequences likely to get hits
TEST_SEQUENCES = {
    "nucl": {
        # Multiple options for nucleotide BLAST testing
        "ribosomal_18s": ">18S_ribosomal_RNA_partial_highly_conserved\nTACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        
        "actin_beta": ">Beta_actin_gene_partial_universal\nATGGATGATGAAATCGCCGCACTCTTCCTCATGAAGATCCTCACCGAGCGCGGCTACACCTTCACCACCATGGAGAAGATCTGGCACCACACCTTCTACAATGAGCTGCGTGTGGCTCCCGAGGAGCACCCCGTGCTGCTGACCGAGGCCCCCCTGAACCCCAAAGCCAACCGCGAGAAGATGACCCAGATCATGTTTGAGACCTTCAACACCCCAGCCATGTACGTAGCCATCCAGGCTGTGCTGTCCCTGTATGCCTCTGGTCGTACCACAGGCATTGTGATGGACTCCGGAGACGGGGTCACCCACACTGTGCCCATCTACGAGGGCTATGCTCTCCCTCACGCCATCCTGCGTCTGGACCTGGCTGGCCGGGACCTGACCGACTACCTCATGAAGATC",
        
        "tubulin_alpha": ">Alpha_tubulin_gene_partial_cytoskeletal\nATGCGTGAGATTGTCCGTCACATTGGCCCCTTCCGTTCGCTCGCCCTCCTCTTGGACGACGCTTACTCCGCCGGCTACGCCGGCAAGCAGAGCCTGAAAAAGAACATGATCGCCGCCAAGTTCGACGCCAAGCACTACGCCGAGGACGGCGCCAAGATCTACGAGGACGGCGGCGTCTTCGACATGGAGGGCAACAACGACATCTTCAAGAAAGTCGCCAAGTTCGCCAACGACCCCGGCGAAGCCGAAGGCAACGTCGCCGCCGCCAACGAACAGGCCGCCGCCATCGTCGCCGAAATCTTCGACGGCGGCGGCAACGGCGGCGGCGGCGGCAACGCCGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGCAACGGC",
    },
    "prot": {
        # Multiple options for protein BLAST testing
        "hsp70_heat_shock": ">HSP70_heat_shock_protein_highly_conserved\nMAKAAAAIGIDLGTTYSCVGVFQHGKVEIIANDQGNRTTPSYVAFTDTERLIGDAKNQVAMNPTNTVFDAKRLIGRRFDDAVVQSDMKHWPFMVVNDAGRPKVQVEYKGETKSFYPEEVSSMVLTKMKEIAEAYLGYPVTNAVITVPAYFNDSQRQATKDAGVIAGLNVLRIINEPTAAAIAYGLDKKVGAERNVLIFDLGGGTFDVSILTIEGIFEVKATAGDTHLGGEDFDNRMVNHFIAEFKRKHKKDISENKRAVRRLRTACERAKRTLSSST",
        
        "cytochrome_c": ">Cytochrome_c_electron_transport_universal\nMGDVEKGKKIFVQKCAQCHTVEKGGKHKTGPNLHGLFGRKTGQAAEGYSYTDANIKKNVWDEWNDLTKNWK",
        
        "ubiquitin": ">Ubiquitin_protein_universal_regulatory\nMQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
    }
}


@dataclass
class BlastResult:
    """Results from a BLAST validation test"""
    database_name: str
    database_value: str
    sequence_type: str
    search_successful: bool
    hits_found: bool
    hit_count: Optional[int]
    first_hit_info: Optional[str]
    screenshot_path: Optional[str]
    error_message: Optional[str]
    runtime: float


class BlastValidator:
    """Validates BLAST searches by testing actual database functionality"""
    
    def __init__(self, headless: bool = True, timeout: int = 300):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.console = Console()
        self.screenshot_dir = Path("test_output/blast_validation")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_browser(self) -> bool:
        """Initialize Chrome WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            self.console.print("[green]✅ Browser initialized[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Browser setup failed: {e}[/red]")
            return False
    
    def get_database_checkboxes(self, url: str) -> List[Dict[str, str]]:
        """Get all database checkboxes with their labels"""
        self.console.print(f"[cyan]🔍 Loading {url}[/cyan]")
        
        try:
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)  # Allow page to fully load
            
            checkboxes = []
            # Get all checkboxes and inspect them
            checkbox_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            
            self.console.print(f"[dim]DEBUG: Found {len(checkbox_elements)} total checkboxes[/dim]")
            
            for i, checkbox in enumerate(checkbox_elements):
                try:
                    value = checkbox.get_attribute('value') or f"checkbox_{i}"
                    name = checkbox.get_attribute('name') or ""
                    
                    # Debug first few checkboxes
                    if i < 5:
                        self.console.print(f"[dim]  Checkbox {i}: value='{value}', name='{name}'[/dim]")
                    
                    # Look for database-like checkboxes
                    is_database = (
                        value and 
                        value != "on" and  # Default checkbox value  
                        name == "databases[]" and  # Common database checkbox name
                        len(value) > 10  # Hash-like values are long
                    )
                    
                    if is_database:
                        # Use a descriptive label since we can't get the real database name
                        db_label = f"Database {len(checkboxes)+1} ({value[:8]}...)"
                        
                        checkboxes.append({
                            'value': value,
                            'label': db_label, 
                            'element_index': i
                        })
                        if len(checkboxes) <= 5:  # Only show first 5
                            self.console.print(f"[green]    → Added database: {db_label}[/green]")
                        
                except Exception as e:
                    continue
                    
            self.console.print(f"[green]Found {len(checkboxes)} database checkboxes[/green]")
            return checkboxes
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to load page: {e}[/red]")
            return []
    
    def test_blast_search(self, url: str, database: Dict[str, str], sequence_type: str = "nucl") -> BlastResult:
        """Test BLAST search against a specific database"""
        start_time = time.time()
        database_name = database['label']
        database_value = database['value']
        
        self.console.print(f"\n[bold cyan]🧬 Testing BLAST against: {database_name}[/bold cyan]")
        
        try:
            # Load the BLAST page
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # Get ALL test sequences as a single FASTA file for better hit rate
            sequences = TEST_SEQUENCES[sequence_type]
            # Combine all sequences into one FASTA
            combined_fasta = "\n\n".join(sequences.values())
            sequence = combined_fasta
            
            sequence_count = len(sequences)
            self.console.print(f"[dim]Using {sequence_count} test sequences in FASTA format: {', '.join(sequences.keys())}[/dim]")
            
            # Find and select the specific database checkbox
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            target_checkbox = None
            
            for checkbox in checkboxes:
                if checkbox.get_attribute('value') == database_value:
                    target_checkbox = checkbox
                    break
            
            if not target_checkbox:
                return BlastResult(
                    database_name=database_name,
                    database_value=database_value,
                    sequence_type=sequence_type,
                    search_successful=False,
                    hits_found=False,
                    hit_count=None,
                    first_hit_info=None,
                    screenshot_path=None,
                    error_message="Database checkbox not found",
                    runtime=time.time() - start_time
                )
            
            # Select the checkbox (with better interaction handling)
            if not target_checkbox.is_selected():
                try:
                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", target_checkbox)
                    time.sleep(0.5)
                    
                    # Try normal click first
                    target_checkbox.click()
                except Exception as e:
                    # If normal click fails, try JavaScript click
                    self.console.print(f"[yellow]⚠️  Normal click failed, trying JavaScript click: {str(e)[:100]}[/yellow]")
                    self.driver.execute_script("arguments[0].click();", target_checkbox)
                
                time.sleep(1)
            
            self.console.print(f"[green]✅ Selected database: {database_name}[/green]")
            
            # Find sequence input area and enter sequence
            sequence_input = None
            for selector in ["textarea[name='sequence']", "#sequence", "textarea"]:
                try:
                    sequence_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not sequence_input:
                return BlastResult(
                    database_name=database_name,
                    database_value=database_value,
                    sequence_type=sequence_type,
                    search_successful=False,
                    hits_found=False,
                    hit_count=None,
                    first_hit_info=None,
                    screenshot_path=None,
                    error_message="Sequence input field not found",
                    runtime=time.time() - start_time
                )
            
            # Clear and enter sequence
            sequence_input.clear()
            sequence_input.send_keys(sequence)
            self.console.print(f"[green]✅ Entered {len(sequence)} characters ({sequence_count} FASTA sequences)[/green]")
            
            # Find and click BLAST button
            blast_button = None
            for selector in ["input[type='submit']", "button[type='submit']", "#blast_button", ".blast-button"]:
                try:
                    blast_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if blast_button.is_displayed() and blast_button.is_enabled():
                        break
                except:
                    continue
            
            if not blast_button:
                return BlastResult(
                    database_name=database_name,
                    database_value=database_value,
                    sequence_type=sequence_type,
                    search_successful=False,
                    hits_found=False,
                    hit_count=None,
                    first_hit_info=None,
                    screenshot_path=None,
                    error_message="BLAST submit button not found",
                    runtime=time.time() - start_time
                )
            
            # Submit BLAST search
            blast_button.click()
            self.console.print(f"[yellow]⏳ BLAST search submitted, waiting for results...[/yellow]")
            
            # Wait for results page to load (BLAST can take a long time)
            self.console.print("[yellow]⏳ Waiting for BLAST results (this may take several minutes)...[/yellow]")
            
            try:
                # Wait longer and check for more specific result indicators
                WebDriverWait(self.driver, 300).until(  # 5 minutes timeout
                    lambda driver: 
                    # Check for results page URL patterns
                    any(pattern in driver.current_url.lower() for pattern in ["/result", "/blast_result", "results"]) or
                    # Check for result content indicators
                    len(driver.find_elements(By.CSS_SELECTOR, ".alignment-container, .blast-alignment, .hit-table, #blast-results")) > 0 or
                    # Check for "no hits found" message
                    any(msg in driver.page_source.lower() for msg in [
                        "no hits found", "no significant similarity", "no matches found",
                        "no sequences producing significant alignments", "query coverage per subject"
                    ]) or
                    # Check for error messages
                    any(err in driver.page_source.lower() for err in ["error", "failed", "timeout"]) or
                    # Check if we're no longer on the search form page
                    (not any(form in driver.page_source.lower() for form in ["blast!", "nucleotide databases", "protein databases"]))
                )
                
                # Additional wait after detection to ensure page is fully loaded
                time.sleep(5)
                
            except TimeoutException:
                return BlastResult(
                    database_name=database_name,
                    database_value=database_value,
                    sequence_type=sequence_type,
                    search_successful=False,
                    hits_found=False,
                    hit_count=None,
                    first_hit_info=None,
                    screenshot_path=None,
                    error_message="BLAST search timed out",
                    runtime=time.time() - start_time
                )
            
            # Analyze results
            page_source = self.driver.page_source.lower()
            
            # Check for hits
            hits_found = False
            hit_count = None
            first_hit_info = None
            
            if "no hits" in page_source or "no significant similarity" in page_source:
                hits_found = False
                hit_count = 0
            else:
                # Look for result indicators
                hit_indicators = [
                    ".hit", ".alignment", ".blast-hit", 
                    "table tr", ".result-row"
                ]
                
                for selector in hit_indicators:
                    try:
                        hit_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(hit_elements) > 1:  # More than just headers
                            hits_found = True
                            hit_count = len(hit_elements) - 1  # Subtract header
                            
                            # Get first hit info
                            try:
                                first_hit = hit_elements[1]  # Skip header
                                first_hit_info = first_hit.text[:100]  # First 100 chars
                            except:
                                first_hit_info = "Hit details not extractable"
                            break
                    except:
                        continue
            
            # Take screenshot of results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{database_name.replace(' ', '_')}_{sequence_type}_{timestamp}.png"
            screenshot_path = self.screenshot_dir / screenshot_filename
            
            try:
                self.driver.save_screenshot(str(screenshot_path))
                self.console.print(f"[green]📸 Results screenshot saved: {screenshot_path}[/green]")
            except:
                screenshot_path = None
            
            # Determine success
            search_successful = True  # We got to results page
            
            if hits_found:
                self.console.print(f"[green]✅ SUCCESS: Found {hit_count} hits in {database_name}[/green]")
            else:
                self.console.print(f"[yellow]⚠️  NO HITS: Search completed but no hits found in {database_name}[/yellow]")
                
            # Also print URL for debugging
            self.console.print(f"[dim]Final URL: {self.driver.current_url}[/dim]")
            
            return BlastResult(
                database_name=database_name,
                database_value=database_value,
                sequence_type=sequence_type,
                search_successful=search_successful,
                hits_found=hits_found,
                hit_count=hit_count,
                first_hit_info=first_hit_info,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                error_message=None,
                runtime=time.time() - start_time
            )
            
        except Exception as e:
            return BlastResult(
                database_name=database_name,
                database_value=database_value,
                sequence_type=sequence_type,
                search_successful=False,
                hits_found=False,
                hit_count=None,
                first_hit_info=None,
                screenshot_path=None,
                error_message=str(e),
                runtime=time.time() - start_time
            )
    
    def run_validation_tests(self, base_url: str, mod: str, max_databases: int = 3) -> List[BlastResult]:
        """Run BLAST validation tests against multiple databases"""
        if not self.setup_browser():
            return []
        
        results = []
        
        try:
            # Discover configurations (same logic as before but simplified)
            from pathlib import Path
            import json
            
            config_dir = Path("../agr_blast_service_configuration/conf")
            mod_dir = config_dir / mod
            
            if not mod_dir.exists():
                self.console.print(f"[red]❌ Configuration directory not found: {mod_dir}[/red]")
                return []
            
            # Find latest environment
            config_files = list(mod_dir.glob(f"databases.{mod}.*.json"))
            if not config_files:
                self.console.print(f"[red]❌ No configuration files found for {mod}[/red]")
                return []
            
            # Get the latest environment (sort by filename)
            latest_config = sorted(config_files, key=lambda x: x.name, reverse=True)[0]
            
            # Extract environment name
            env_name = latest_config.stem.split('.')[-1]  # e.g., FB2025_03
            url = f"{base_url}/{mod}/{env_name}"
            
            self.console.print(f"[cyan]🎯 Testing latest environment: {mod}/{env_name}[/cyan]")
            
            # Get available databases
            databases = self.get_database_checkboxes(url)
            
            if not databases:
                return []
            
            # Limit number of databases to test
            test_databases = databases[:max_databases]
            
            self.console.print(f"[cyan]Testing {len(test_databases)} databases...[/cyan]")
            
            # Test each database
            for i, database in enumerate(test_databases, 1):
                self.console.print(f"\n[bold]--- Test {i}/{len(test_databases)} ---[/bold]")
                
                result = self.test_blast_search(url, database, "nucl")
                results.append(result)
                
                # Brief pause between tests
                time.sleep(2)
            
            return results
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def print_results_summary(self, results: List[BlastResult]):
        """Print a clear summary of BLAST validation results"""
        if not results:
            self.console.print("[red]❌ No results to summarize[/red]")
            return
        
        self.console.print(f"\n[bold cyan]📊 BLAST VALIDATION RESULTS[/bold cyan]")
        
        successful_searches = sum(1 for r in results if r.search_successful)
        searches_with_hits = sum(1 for r in results if r.hits_found)
        
        self.console.print(f"[green]✅ Successful searches: {successful_searches}/{len(results)}[/green]")
        self.console.print(f"[green]🎯 Searches with hits: {searches_with_hits}/{len(results)}[/green]")
        
        # Individual results
        for i, result in enumerate(results, 1):
            status = "✅ PASS" if result.search_successful and result.hits_found else "⚠️ NO HITS" if result.search_successful else "❌ FAIL"
            hit_info = f" ({result.hit_count} hits)" if result.hit_count else ""
            self.console.print(f"  {i}. {status}: {result.database_name}{hit_info}")
            if result.error_message:
                self.console.print(f"     💥 Error: {result.error_message}")
            if result.screenshot_path:
                self.console.print(f"     📸 Screenshot: {result.screenshot_path}")


@click.command()
@click.option("-m", "--mod", type=click.Choice(['FB', 'WB', 'SGD', 'ZFIN', 'RGD', 'XB']), 
              required=True, help="Model organism database to test")
@click.option("--max-databases", type=int, default=3, 
              help="Maximum number of databases to test")
@click.option("--base-url", default="https://blast.alliancegenome.org/blast", 
              help="Base URL for BLAST interface")
@click.option("--headless/--no-headless", default=True, 
              help="Run browser in headless mode")
@click.option("--timeout", default=300, help="Timeout for BLAST searches in seconds (default: 5 minutes)")
def main(mod, max_databases, base_url, headless, timeout):
    """
    BLAST Validation Testing - Tests actual BLAST functionality
    
    This performs REAL BLAST testing by:
    - Selecting specific database checkboxes  
    - Submitting BLAST searches with test sequences
    - Waiting for actual results to load
    - Validating that hits are returned
    - Capturing meaningful screenshots of results
    
    Examples:
        # Test FB with visible browser
        uv run python tests/ui/test_blast_validation.py -m FB --no-headless
        
        # Test 5 databases in WB  
        uv run python tests/ui/test_blast_validation.py -m WB --max-databases 5
    """
    console = Console()
    console.print(f"[bold green]🧬 Starting BLAST Validation for {mod}[/bold green]")
    
    validator = BlastValidator(headless=headless, timeout=timeout)
    results = validator.run_validation_tests(base_url, mod, max_databases)
    
    validator.print_results_summary(results)


if __name__ == "__main__":
    main()