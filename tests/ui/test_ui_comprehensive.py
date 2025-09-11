#!/usr/bin/env python3
"""
Comprehensive UI Testing Framework for BLAST Web Interface

A robust testing framework that discovers URLs from AGR BLAST service configuration,
automates checkbox interactions, and validates BLAST searches with biological sequences.

Features:
- Automatic URL discovery from AGR configuration files
- Checkbox discovery and interaction automation
- Biologically relevant test sequences
- Screenshot capture and visual validation
- Comprehensive reporting with markdown output
- Error handling and retry mechanisms
"""

import json
import yaml
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import tempfile
import base64

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager


# Use the same conserved biological sequences as CLI framework
UNIVERSAL_SEQUENCES = {
    "nucl": {
        # 18S rRNA partial sequence - highly conserved across eukaryotes
        "FB": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "WB": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA", 
        "SGD": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "ZFIN": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "RGD": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "XB": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "universal": "ATGGATGATGATATCGCCGCGCTCGTCGTCGACAACGGCTCCGGCATGTGCAAGGCCGGCTTCGCGGGCGACGATGCCCCCCGGGCCGTCTTCCCCTCCATCGTCCACCGCAAATGCTTCTAG"
    },
    "prot": {
        # Heat shock protein 70 conserved domain
        "FB": "MAKAAAIGIDLGTTYSCVGVFQHGKVEIIANDQGNRTTPSYVAFTDTERLIGDAAKNQVAMNPTNTVFDAKRLIGRRFDDPSVQSDMKHWPFMVVNDAGRPKVQVEYKGETKSFYPEEISSMVLTKMKEIAEAYLGKTVTNAVVTVPAYFNDSQRQATKDAGTIAGLNVLRIINEPTAAAIAYGLDKKVGAERNVLIFDLGGGTFDVSILTIEDGIFEVKSTAGDTHLGGEDFDNRMVNHFIAEFKRKHKKDISENKRAVRRLRTACERAKRTLSSSTQASIEIDSLYEGIDFYTSITRARFEELNADLFRGTLDPVEKALRDAKLDKSQIHDIVLVGGSTRIPKIQKLLQDFFNGKELNKSINPDEAVAYGAAVQAAILSGDKSENVQDLLLLDVAPLSLGLETAGGVMTALIKRNSTIPTKQTQIFTTYSDNQPGVLIQVYEGERAMTKDNNLLGRFELSGIPPAPRGVPQIEVTFDIDANGILNVTATDKSTGKANKITITNDKGRLSKEDIERMVQEAEKYKAEDEKLKTGDIDKDNDGAYVLRGIEKQNKTDDNLRVSLFLLKALEKEPQKTGPEEEKVKSKVESRPETDEKEEPRKKVEALKDEEKKEEKQETDAKQVLETDQEGKQSQKDQEDHILQEPKSQE",
        # Actin protein sequence - highly conserved cytoskeletal protein
        "WB": "MDDDIAALVVDNGSGMCKAGFAGDDAPRAVFPSIVGRPRHQGVMVGMGQKDSYVGDEAQSKRGILTLKYPIEHGIVTNWDDMEKIWHHTFYNELRVAPEEHPVLLTEAPLNPKANREKMTQIMFETFNTPAMYVAIQAVLSLYASGRTTGIVMDSGDGVTHTVPIYEGYALPHAILRLDLAGRDLTDYLMKILTERGYSFTTTAEREIVRDIKEKLCYVALDFEQEMATAASSSSLEKSYELPDGQVITIGNERFRCPEALFQPSFLGMESCGIHETTFNSIMKCDVDIRKDLYANTVLSGGTTMYPGIADRMQKEITALAPSTMKIKIIAPPERKYSVWIGGSILASLSTFQQMWISKQEYDESGPSIVHRKCF",
        "SGD": "MTTFIGNSTAIQELFKRISEQFTAMFRRKAFLHWYTGEGMDEMEFTEAESNMNDLVSEYQQYQDATAADDDILMENQFTSDTPVQHVIYQGKDAASEEQLFKDLMKKLESLDLDRIGSEVVLSREKTLERIAGRSIIFDKGDENTIKKFLRLFNSNAEPKLGEQVRDVDNAALTQLTEDKLSHKWKELEVYYLRHDDLGKYIPNFGKLVEELGDLYLGQMDSKDSAVHDWEVGMFDDSYMSTLRSKAAYYQKMGFQGDGSHDVEIVDDAKDLEADLQWVTDGDKKWYKIAKLCLDCKDMLISGSLIAFLKTMFNAGAQQELSSGILTKASLLHKQGMLQYSAEETVVDDVSDKALIRSGGSAELLIKFYKRQHGYKRLFEEFGITGKFLLGSDLNPYNQDVEQVMNRLKDAMAAANPLKLKDSLIEVAMKTGDQKKEMIKRAQNEKRQVDAIERMGYVRSLLAETAYIVKNVNPDYILHAKDAGKVLKLIIKGHAFKTDEFLAIFRNAGSKLQPGEIFEQLEDRFMGLDKKTSDLVRSISDEKQRILLHGRRKLVVGKAIDQCNIMGTPAVIAACSADFDFVNPPLNFYDGVRLKIVGAKRVLDQQFGGMGYVHGFVGVARAFIPRTHQQENDFKKFVIQEGQGVTTAKGLAEDQINLHKKDKVYVIEPFMKIVQGDDAYKAYAATGETLTDEDVRFFRNLVGQVQLSADTKGYDTSIGGEVIALIDLSAKTLAYAAGFDNISGGSGYTGVGDSLYDYAIHGKSKSAELTSAKLRQIKEILYDSAPDTVKQTPVSQKLKAVVLMVGRNKEPAYQNLKRMTYAAALQRRPGVVDKKYYAAIPDLQKSIKMFETPQTLQRSQKSQMFPMKSTKKR",
        "ZFIN": "MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFKTDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA",
        "RGD": "MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFKTDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA",
        "XB": "MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFKTDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA",
        "universal": "MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFKTDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA"
    }
}


@dataclass
class CheckboxInfo:
    """Information about a discovered checkbox"""
    id: str
    text: str
    value: str
    genus: Optional[str] = None
    species: Optional[str] = None
    seqtype: Optional[str] = None
    selected: bool = False


@dataclass
class UITestResult:
    """Container for UI test results"""
    url: str
    mod: str
    environment: str
    sequence_type: str
    checkboxes_found: int
    checkboxes_tested: int
    search_successful: bool
    results_found: bool
    screenshots: List[str]
    runtime: float
    error_message: Optional[str] = None


class CheckboxDiscovery:
    """Discovers checkboxes on BLAST interface and saves to temp config file"""
    
    def __init__(self, base_url: str = "https://blast.alliancegenome.org/blast", headless: bool = False):
        self.base_url = base_url
        self.headless = headless
        self.driver = None
        self.console = Console()
        self.temp_config_file = Path("temp_checkbox_config.json")
        
    def setup_browser(self) -> bool:
        """Initialize Chrome WebDriver for discovery (visible mode recommended)"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')
                
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 30)
            
            self.console.print("[green]✅ Browser initialized for discovery[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to initialize browser: {e}[/red]")
            return False
    
    def discover_checkboxes(self, url: str, mod: str, environment: str) -> List[CheckboxInfo]:
        """Discover all checkboxes on a BLAST interface page"""
        self.console.print(f"[cyan]🔍 Discovering checkboxes on: {url}[/cyan]")
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Allow page to load
            
            # Find all checkboxes
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            discovered_checkboxes = []
            
            for i, checkbox in enumerate(checkboxes):
                try:
                    # Get checkbox attributes
                    checkbox_id = checkbox.get_attribute('id') or f"checkbox_{i}"
                    checkbox_value = checkbox.get_attribute('value') or ""
                    
                    # Try to find associated label
                    label_text = ""
                    try:
                        # Method 1: Look for label with for attribute
                        if checkbox_id:
                            label = self.driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                            label_text = label.text.strip()
                    except:
                        try:
                            # Method 2: Look for parent label
                            label = checkbox.find_element(By.XPATH, "./parent::label")
                            label_text = label.text.strip()
                        except:
                            try:
                                # Method 3: Look for sibling text
                                parent = checkbox.find_element(By.XPATH, "./..")
                                label_text = parent.text.strip()
                            except:
                                label_text = f"Unknown_{i}"
                    
                    # Create CheckboxInfo with existing structure
                    checkbox_info = CheckboxInfo(
                        id=checkbox_id,
                        text=label_text,
                        value=checkbox_value,
                        selected=checkbox.is_selected()
                    )
                    
                    discovered_checkboxes.append(checkbox_info)
                    
                except Exception as e:
                    self.console.print(f"[yellow]⚠️  Error processing checkbox {i}: {e}[/yellow]")
                    continue
            
            self.console.print(f"[green]✅ Discovered {len(discovered_checkboxes)} checkboxes[/green]")
            return discovered_checkboxes
            
        except Exception as e:
            self.console.print(f"[red]❌ Error discovering checkboxes: {e}[/red]")
            return []
    
    def save_checkbox_config(self, discovered_data: Dict[str, Any]):
        """Save discovered checkbox data to temporary config file"""
        try:
            with open(self.temp_config_file, 'w') as f:
                json.dump(discovered_data, f, indent=2, default=str)
            
            self.console.print(f"[green]💾 Checkbox configuration saved to: {self.temp_config_file}[/green]")
            self.console.print(f"[dim]Config contains {sum(len(env_data.get('checkboxes', [])) for mod_data in discovered_data.values() for env_data in mod_data.values())} total checkboxes[/dim]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to save config: {e}[/red]")
    
    def run_discovery(self, configurations: Dict[str, Any]) -> bool:
        """Run discovery mode on all configurations"""
        if not self.setup_browser():
            return False
        
        discovered_data = {}
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                
                total_configs = sum(len(envs) for envs in configurations.values())
                discovery_task = progress.add_task("Discovering checkboxes...", total=total_configs)
                
                for mod, environments in configurations.items():
                    discovered_data[mod] = {}
                    
                    for env, config in environments.items():
                        url = f"{self.base_url}/{mod}/{env}"
                        
                        # Discover checkboxes
                        checkboxes = self.discover_checkboxes(url, mod, env)
                        
                        # Convert CheckboxInfo objects to dictionaries
                        checkbox_dicts = []
                        for cb in checkboxes:
                            checkbox_dicts.append({
                                'id': cb.id,
                                'text': cb.text,
                                'value': cb.value,
                                'selected': cb.selected
                            })
                        
                        discovered_data[mod][env] = {
                            'url': url,
                            'checkboxes': checkbox_dicts,
                            'total_checkboxes': len(checkboxes),
                            'discovery_timestamp': datetime.now().isoformat()
                        }
                        
                        progress.update(discovery_task, advance=1)
                        time.sleep(1)  # Brief pause between discoveries
            
            # Save the discovered configuration
            self.save_checkbox_config(discovered_data)
            return True
            
        finally:
            if self.driver:
                self.driver.quit()


class SystematicTester:
    """Systematic testing of individual checkboxes from saved config"""
    
    def __init__(self, config_file: Path = Path("temp_checkbox_config.json"), headless: bool = True):
        self.config_file = config_file
        self.headless = headless
        self.console = Console()
        self.screenshot_dir = Path("test_output/ui_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
    def load_checkbox_config(self) -> Dict[str, Any]:
        """Load checkbox configuration from saved temp file"""
        try:
            if not self.config_file.exists():
                self.console.print(f"[red]❌ Config file not found: {self.config_file}[/red]")
                self.console.print("[yellow]Run discovery mode first with --discovery flag[/yellow]")
                return {}
                
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            self.console.print(f"[green]✅ Loaded checkbox config with {sum(len(env_data.get('checkboxes', [])) for mod_data in config.values() for env_data in mod_data.values())} total checkboxes[/green]")
            return config
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to load config: {e}[/red]")
            return {}
    
    def test_individual_checkbox(self, url: str, checkbox_data: Dict[str, Any], mod: str, env: str, sequence_type: str = "nucl") -> UITestResult:
        """Test a single checkbox systematically"""
        tester = UITester(headless=self.headless)
        
        # Initialize browser before testing
        if not tester.setup_browser():
            return UITestResult(
                url=url, mod=mod, environment=env, sequence_type=sequence_type,
                checkboxes_found=0, checkboxes_tested=0, search_successful=False,
                results_found=False, screenshots=[], runtime=0.0,
                error_message="Failed to initialize browser"
            )
        
        try:
            # Run the test with limited checkboxes (1 checkbox)
            result = tester.run_blast_search(url, mod, env, sequence_type, max_checkboxes=1)
        finally:
            # Always clean up the browser
            if tester.driver:
                tester.driver.quit()
                
        return result
    
    def get_latest_environments(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter config to only include the latest environment per MOD"""
        latest_config = {}
        
        for mod, environments in config.items():
            if not environments:
                continue
                
            # Sort environments to find the latest (highest version)
            sorted_envs = sorted(environments.keys(), reverse=True)
            latest_env = sorted_envs[0]
            
            latest_config[mod] = {latest_env: environments[latest_env]}
            self.console.print(f"[dim]Selected latest environment for {mod}: {latest_env}[/dim]")
        
        return latest_config
    
    def run_systematic_tests(self, max_checkboxes_per_url: int = None, latest_only: bool = True) -> List[UITestResult]:
        """Run systematic testing of individual checkboxes"""
        config = self.load_checkbox_config()
        if not config:
            return []
        
        # Filter to latest environments only
        if latest_only:
            config = self.get_latest_environments(config)
            self.console.print("[dim]Testing latest environments only. Use latest_only=False to test all.[/dim]")
        
        results = []
        
        try:
            total_checkboxes = sum(len(env_data.get('checkboxes', [])) for mod_data in config.values() for env_data in mod_data.values())
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                
                test_task = progress.add_task("Testing individual checkboxes...", total=total_checkboxes)
                
                for mod, environments in config.items():
                    for env, env_data in environments.items():
                        url = env_data['url']
                        checkboxes = env_data.get('checkboxes', [])
                        
                        # Limit checkboxes to test if specified
                        if max_checkboxes_per_url:
                            checkboxes = checkboxes[:max_checkboxes_per_url]
                        
                        self.console.print(f"\n[cyan]🧪 Testing {len(checkboxes)} checkboxes for {mod}/{env}[/cyan]")
                        
                        for i, checkbox_data in enumerate(checkboxes, 1):
                            checkbox_label = checkbox_data.get('text', 'Unknown')
                            self.console.print(f"[dim]Testing checkbox {i}/{len(checkboxes)}: {checkbox_label}[/dim]")
                            
                            # Test this specific checkbox
                            result = self.test_individual_checkbox(url, checkbox_data, mod, env, "nucl")
                            results.append(result)
                            
                            # Show clear pass/fail status
                            if result.search_successful and result.results_found:
                                self.console.print(f"[green]✅ PASS: Checkbox {i} - Search successful with results[/green]")
                            elif result.search_successful and not result.results_found:
                                self.console.print(f"[yellow]⚠️  PARTIAL: Checkbox {i} - Search successful but no results[/yellow]")
                            else:
                                self.console.print(f"[red]❌ FAIL: Checkbox {i} - {result.error_message or 'Search failed'}[/red]")
                            
                            progress.update(test_task, advance=1)
                            time.sleep(0.5)  # Brief pause between tests
            
            return results
            
        except Exception as e:
            self.console.print(f"[red]❌ Error during systematic testing: {e}[/red]")
            return results


class ConfigurationDiscovery:
    """Discovers URLs and configurations from AGR BLAST service configuration"""
    
    def __init__(self, config_dir: str = "../agr_blast_service_configuration/conf"):
        self.config_dir = Path(config_dir)
        self.console = Console()
    
    def discover_configurations(self, mod: str = None, base_url: str = "https://blast.alliancegenome.org/blast") -> Dict[str, Dict[str, Any]]:
        """Discover all available configurations from AGR service config"""
        configurations = {}
        
        if not self.config_dir.exists():
            self.console.print(f"[red]❌ Configuration directory not found: {self.config_dir}[/red]")
            return configurations
        
        # Read global configuration
        global_config_path = self.config_dir / "global.yaml"
        if global_config_path.exists():
            with open(global_config_path, 'r') as f:
                global_config = yaml.safe_load(f)
        else:
            global_config = {}
        
        # Process each MOD
        mods_to_process = [mod] if mod else ["FB", "WB", "SGD", "ZFIN", "RGD", "XB"]
        
        for mod_name in mods_to_process:
            mod_dir = self.config_dir / mod_name
            if not mod_dir.exists():
                continue
            
            configurations[mod_name] = {}
            
            # Find database configuration files
            config_files = list(mod_dir.glob(f"databases.{mod_name}.*.json"))
            
            for config_file in config_files:
                # Extract environment from filename: databases.FB.FB2025_03.json -> FB2025_03
                parts = config_file.stem.split('.')
                if len(parts) >= 3:
                    environment = parts[2]
                    
                    # Load configuration
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    # Extract database information
                    databases = []
                    if 'data' in config_data:
                        for db in config_data['data']:
                            databases.append({
                                'title': db.get('blast_title', ''),
                                'genus': db.get('genus', ''),
                                'species': db.get('species', ''),
                                'seqtype': db.get('seqtype', ''),
                                'description': db.get('description', '')
                            })
                    
                    configurations[mod_name][environment] = {
                        'url': f"{base_url}/{mod_name}/{environment}",
                        'databases': databases,
                        'config_file': str(config_file)
                    }
        
        return configurations
    
    def get_latest_environment(self, mod: str) -> Optional[str]:
        """Get the latest environment for a MOD based on naming convention"""
        configurations = self.discover_configurations(mod)
        if mod not in configurations:
            return None
        
        environments = list(configurations[mod].keys())
        if not environments:
            return None
        
        # Sort environments to get the latest
        environments.sort(reverse=True)
        return environments[0]


class UITester:
    """Comprehensive UI testing framework with checkbox automation"""
    
    def __init__(self, base_url: str = "https://blast.alliancegenome.org/blast", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.console = Console()
        self.driver = None
        self.wait = None
        self.results: List[UITestResult] = []
        self.screenshot_dir = Path("test_output/ui_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_browser(self) -> bool:
        """Initialize Chrome WebDriver with optimized settings"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-web-security')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Setup Chrome service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 30)
            
            self.console.print("[green]✅ Browser initialized successfully[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to initialize browser: {e}[/red]")
            return False
    
    def get_test_sequence(self, mod: str, sequence_type: str) -> str:
        """Get appropriate test sequence for MOD and sequence type"""
        if mod in UNIVERSAL_SEQUENCES[sequence_type]:
            return UNIVERSAL_SEQUENCES[sequence_type][mod]
        else:
            return UNIVERSAL_SEQUENCES[sequence_type]["universal"]
    
    def take_screenshot(self, name: str, description: str = "") -> str:
        """Take a screenshot and save it with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshot_dir / filename
        
        try:
            self.driver.save_screenshot(str(filepath))
            if description:
                self.console.print(f"[blue]📸 Screenshot: {description}[/blue]")
            return str(filepath)
        except Exception as e:
            self.console.print(f"[yellow]⚠️  Screenshot failed: {e}[/yellow]")
            return ""
    
    def analyze_checkboxes(self, checkbox_elements: List) -> List[CheckboxInfo]:
        """Analyze checkbox elements and extract information"""
        checkboxes = []
        
        try:
            for i, checkbox in enumerate(checkbox_elements):
                try:
                    checkbox_id = checkbox.get_attribute("id") or checkbox.get_attribute("name") or f"checkbox_{i}"
                    checkbox_value = checkbox.get_attribute("value") or ""
                    
                    # Find associated label or nearby text
                    label_text = ""
                    try:
                        # Try to find label by 'for' attribute
                        if checkbox.get_attribute("id"):
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{checkbox.get_attribute('id')}']")
                            label_text = label.text.strip()
                    except NoSuchElementException:
                        try:
                            # Try to find parent label
                            parent = checkbox.find_element(By.XPATH, "./..")
                            label_text = parent.text.strip()
                        except:
                            try:
                                # Try to find following sibling text
                                sibling = checkbox.find_element(By.XPATH, "./following-sibling::text()[1]")
                                if sibling:
                                    label_text = sibling.strip()
                            except:
                                try:
                                    # Try to get text from parent element
                                    parent = checkbox.find_element(By.XPATH, "./..")
                                    if parent and parent.text:
                                        # Extract just the text, removing child element text
                                        label_text = parent.get_attribute("textContent").strip()
                                except:
                                    pass
                    
                    # Extract genus/species if possible
                    genus, species = None, None
                    if label_text:
                        # Common patterns for organism names
                        parts = label_text.split()
                        if len(parts) >= 2:
                            genus = parts[0]
                            species = parts[1]
                    
                    # Determine sequence type from context
                    seqtype = None
                    text_lower = label_text.lower()
                    if "protein" in text_lower or "prot" in text_lower:
                        seqtype = "prot"
                    elif "nucleotide" in text_lower or "nucl" in text_lower or "genome" in text_lower or "rna" in text_lower:
                        seqtype = "nucl"
                    
                    if checkbox_id or checkbox_value or label_text:
                        checkboxes.append(CheckboxInfo(
                            id=checkbox_id,
                            text=label_text,
                            value=checkbox_value,
                            genus=genus,
                            species=species,
                            seqtype=seqtype,
                            selected=checkbox.is_selected()
                        ))
                        
                except Exception as e:
                    self.console.print(f"[yellow]⚠️  Error processing checkbox: {e}[/yellow]")
            
            self.console.print(f"[cyan]🔍 Found {len(checkboxes)} checkboxes[/cyan]")
            return checkboxes
            
        except Exception as e:
            self.console.print(f"[red]❌ Error discovering checkboxes: {e}[/red]")
            return []
    
    def run_blast_search(self, url: str, mod: str, environment: str, sequence_type: str = "nucl", max_checkboxes: int = 3) -> UITestResult:
        """Run a comprehensive BLAST search test with checkbox automation"""
        start_time = time.time()
        screenshots = []
        
        try:
            # Get all checkbox elements first (before discover_checkboxes modifies page state)
            self.driver.get(url)
            self.take_screenshot("page_loaded", f"Loaded {url}")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # Get all checkbox elements for later selection
            all_checkbox_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            
            # Analyze checkboxes from the elements we already have
            checkboxes = self.analyze_checkboxes(all_checkbox_elements)
            screenshots.append(self.take_screenshot("checkboxes_discovered", "Checkboxes discovered"))
            
            if not checkboxes:
                return UITestResult(
                    url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                    checkboxes_found=0, checkboxes_tested=0, search_successful=False,
                    results_found=False, screenshots=screenshots, runtime=time.time() - start_time,
                    error_message="No checkboxes found"
                )
            
            # Filter checkboxes by sequence type if possible
            target_checkboxes = [cb for cb in checkboxes if cb.seqtype == sequence_type or cb.seqtype is None]
            if not target_checkboxes:
                target_checkboxes = checkboxes
            
            # Limit number of checkboxes to test
            test_checkboxes = target_checkboxes[:max_checkboxes]
            
            # Get test sequence
            sequence = self.get_test_sequence(mod, sequence_type)
            
            # Select checkboxes - use the original checkbox elements to avoid ID conflicts
            checkboxes_tested = 0
            for i, checkbox_info in enumerate(test_checkboxes):
                try:
                    # Instead of searching by ID (which may be duplicated), 
                    # find the checkbox by its position in the original list
                    if i < len(all_checkbox_elements):
                        checkbox_element = all_checkbox_elements[i]
                    else:
                        # Fallback to original search method
                        checkbox_element = None
                        if checkbox_info.id and not checkbox_info.id.startswith("checkbox_"):
                            try:
                                checkbox_element = self.driver.find_element(By.ID, checkbox_info.id)
                            except NoSuchElementException:
                                try:
                                    # Try with quotes around the ID (for IDs with special characters)
                                    checkbox_element = self.driver.find_element(By.CSS_SELECTOR, f'input[id="{checkbox_info.id}"]')
                                except NoSuchElementException:
                                    try:
                                        # Try as name attribute
                                        checkbox_element = self.driver.find_element(By.CSS_SELECTOR, f'input[name="{checkbox_info.id}"]')
                                    except NoSuchElementException:
                                        pass
                    
                    if not checkbox_element and checkbox_info.value:
                        try:
                            checkbox_element = self.driver.find_element(By.CSS_SELECTOR, f"input[value='{checkbox_info.value}']")
                        except NoSuchElementException:
                            pass
                    
                    # Try to find by nearby text if we have it
                    if not checkbox_element and checkbox_info.text:
                        try:
                            # Look for checkbox near text containing the organism name
                            if checkbox_info.genus and checkbox_info.species:
                                xpath = f"//text()[contains(., '{checkbox_info.genus}') and contains(., '{checkbox_info.species}')]/ancestor-or-self::*/input[@type='checkbox']"
                                checkbox_element = self.driver.find_element(By.XPATH, xpath)
                        except NoSuchElementException:
                            pass
                    
                    if checkbox_element and not checkbox_element.is_selected():
                        # Scroll to element first
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", checkbox_element)
                        time.sleep(0.5)
                        
                        # Try clicking
                        try:
                            checkbox_element.click()
                        except:
                            # Fallback to JavaScript click
                            self.driver.execute_script("arguments[0].click();", checkbox_element)
                        
                        checkboxes_tested += 1
                        self.console.print(f"[green]✅ Selected checkbox: {checkbox_info.text[:50] or checkbox_info.id}[/green]")
                        time.sleep(0.5)  # Brief pause between selections
                        
                except Exception as e:
                    self.console.print(f"[yellow]⚠️  Could not select checkbox {checkbox_info.text[:30] or checkbox_info.id}: {str(e)[:100]}[/yellow]")
            
            screenshots.append(self.take_screenshot("checkboxes_selected", f"Selected {checkboxes_tested} checkboxes"))
            
            # Find and fill sequence textarea
            sequence_area = None
            sequence_selectors = [
                "textarea[name='sequence']",
                "textarea#sequence", 
                "textarea.sequence",
                "textarea[placeholder*='sequence']",
                "textarea"
            ]
            
            for selector in sequence_selectors:
                try:
                    sequence_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not sequence_area:
                return UITestResult(
                    url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                    checkboxes_found=len(checkboxes), checkboxes_tested=checkboxes_tested,
                    search_successful=False, results_found=False, screenshots=screenshots,
                    runtime=time.time() - start_time, error_message="Sequence input not found"
                )
            
            # Clear and enter sequence
            sequence_area.clear()
            sequence_area.send_keys(sequence)
            screenshots.append(self.take_screenshot("sequence_entered", f"Entered {len(sequence)} character sequence"))
            
            # Find and click BLAST button
            blast_button = None
            button_selectors = [
                "input[type='submit'][value*='BLAST']",
                "button[type='submit']",
                "input[value='BLAST']",
                "button:contains('BLAST')",
                ".blast-submit",
                "#blast-submit"
            ]
            
            for selector in button_selectors:
                try:
                    blast_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not blast_button:
                # Try finding by text content
                try:
                    blast_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'BLAST')] | //input[contains(@value, 'BLAST')]")
                except NoSuchElementException:
                    pass
            
            if not blast_button:
                return UITestResult(
                    url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                    checkboxes_found=len(checkboxes), checkboxes_tested=checkboxes_tested,
                    search_successful=False, results_found=False, screenshots=screenshots,
                    runtime=time.time() - start_time, error_message="BLAST button not found"
                )
            
            # Click BLAST button
            self.driver.execute_script("arguments[0].click();", blast_button)
            screenshots.append(self.take_screenshot("blast_submitted", "BLAST search submitted"))
            
            # Wait for results page
            try:
                # Wait for either results or error message
                self.wait.until(
                    lambda driver: "result" in driver.current_url.lower() or 
                                 len(driver.find_elements(By.CSS_SELECTOR, ".result, .results, #results, .blast-results")) > 0 or
                                 len(driver.find_elements(By.CSS_SELECTOR, ".error, .warning")) > 0
                )
                
                screenshots.append(self.take_screenshot("results_page", "Results page loaded"))
                
                # Check for results
                results_found = False
                try:
                    result_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".result, .results, .blast-results, .alignment, .hit, table")
                    results_found = len(result_elements) > 0
                except:
                    pass
                
                runtime = time.time() - start_time
                
                return UITestResult(
                    url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                    checkboxes_found=len(checkboxes), checkboxes_tested=checkboxes_tested,
                    search_successful=True, results_found=results_found, screenshots=screenshots,
                    runtime=runtime
                )
                
            except TimeoutException:
                screenshots.append(self.take_screenshot("timeout", "Search timed out"))
                return UITestResult(
                    url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                    checkboxes_found=len(checkboxes), checkboxes_tested=checkboxes_tested,
                    search_successful=False, results_found=False, screenshots=screenshots,
                    runtime=time.time() - start_time, error_message="Search timed out"
                )
        
        except Exception as e:
            screenshots.append(self.take_screenshot("error", f"Error occurred: {str(e)[:50]}"))
            return UITestResult(
                url=url, mod=mod, environment=environment, sequence_type=sequence_type,
                checkboxes_found=0, checkboxes_tested=0, search_successful=False,
                results_found=False, screenshots=screenshots, runtime=time.time() - start_time,
                error_message=str(e)
            )
    
    def run_comprehensive_tests(self, configurations: Dict[str, Dict[str, Any]], 
                               sequence_type: str = "nucl", max_urls: int = None) -> bool:
        """Run comprehensive tests across discovered configurations"""
        
        self.console.print(f"\n[bold blue]🧪 AGR BLAST UI Testing Framework[/bold blue]")
        self.console.print(f"[cyan]Testing {sequence_type} sequences across discovered configurations[/cyan]\n")
        
        if not self.setup_browser():
            return False
        
        try:
            # Flatten configurations into test URLs
            test_urls = []
            for mod, environments in configurations.items():
                for env, config in environments.items():
                    test_urls.append((mod, env, config['url']))
            
            if max_urls:
                test_urls = test_urls[:max_urls]
            
            self.console.print(f"[green]✅ Found {len(test_urls)} URLs to test[/green]")
            
            # Run tests with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                console=self.console
            ) as progress:
                
                task = progress.add_task("Running UI tests...", total=len(test_urls))
                
                for mod, environment, url in test_urls:
                    progress.update(task, description=f"Testing {mod}/{environment}")
                    
                    result = self.run_blast_search(url, mod, environment, sequence_type)
                    self.results.append(result)
                    
                    status = "✅" if result.search_successful else "❌"
                    self.console.print(f"   {status} {mod}/{environment}: {result.checkboxes_tested} checkboxes tested")
                    
                    progress.advance(task)
            
            self.generate_report()
            return True
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        self.console.print(f"\n[bold green]📊 UI Test Results Summary[/bold green]")
        
        # Statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r.search_successful)
        failed = total - successful
        total_checkboxes = sum(r.checkboxes_found for r in self.results)
        tested_checkboxes = sum(r.checkboxes_tested for r in self.results)
        results_found = sum(1 for r in self.results if r.results_found)
        avg_runtime = sum(r.runtime for r in self.results) / total if total > 0 else 0
        
        # Summary table
        summary = Table(title="UI Test Summary")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")
        
        summary.add_row("Total URLs Tested", str(total))
        summary.add_row("Successful Searches", str(successful))
        summary.add_row("Failed Searches", str(failed))
        summary.add_row("Success Rate", f"{(successful/total*100):.1f}%" if total > 0 else "0%")
        summary.add_row("Total Checkboxes Found", str(total_checkboxes))
        summary.add_row("Checkboxes Tested", str(tested_checkboxes))
        summary.add_row("URLs with Results", str(results_found))
        summary.add_row("Average Runtime", f"{avg_runtime:.2f}s")
        
        self.console.print(summary)
        
        # Show failures
        failures = [r for r in self.results if not r.search_successful]
        if failures:
            self.console.print(f"\n[red]❌ Failed Tests ({len(failures)}):[/red]")
            for result in failures[:5]:
                error = result.error_message or "Unknown error"
                if len(error) > 60:
                    error = error[:60] + "..."
                self.console.print(f"   {result.mod}/{result.environment}: {error}")
        
        # Show successful tests with results
        successful_with_results = [r for r in self.results if r.search_successful and r.results_found]
        if successful_with_results:
            self.console.print(f"\n[green]🏆 Successful Tests with Results ({len(successful_with_results)}):[/green]")
            for result in successful_with_results[:5]:
                self.console.print(f"   {result.mod}/{result.environment}: {result.checkboxes_tested} checkboxes tested ({result.runtime:.2f}s)")
    
    def generate_markdown_report(self, filename: str):
        """Generate detailed markdown report with screenshots"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r.search_successful)
        failed = total - successful
        total_checkboxes = sum(r.checkboxes_found for r in self.results)
        tested_checkboxes = sum(r.checkboxes_tested for r in self.results)
        results_found = sum(1 for r in self.results if r.results_found)
        avg_runtime = sum(r.runtime for r in self.results) / total if total > 0 else 0
        
        markdown_content = f"""# BLAST UI Testing Report

**Generated:** {timestamp}

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Total URLs Tested** | {total} |
| **Successful Searches** | {successful} |
| **Failed Searches** | {failed} |
| **Success Rate** | {(successful/total*100):.1f}% |
| **Total Checkboxes Found** | {total_checkboxes} |
| **Checkboxes Tested** | {tested_checkboxes} |
| **URLs with Results** | {results_found} |
| **Average Runtime** | {avg_runtime:.2f}s |

## ✅ Test Results

### All Tests ({total} total)

| MOD | Environment | URL | Checkboxes Found | Checkboxes Tested | Search Success | Results Found | Runtime (s) | Screenshots | Error |
|-----|-------------|-----|------------------|-------------------|----------------|---------------|-------------|-------------|-------|
"""
        
        # Add all results
        for result in self.results:
            search_status = "✅" if result.search_successful else "❌"
            results_status = "✅" if result.results_found else "❌"
            error = result.error_message[:50] + "..." if result.error_message and len(result.error_message) > 50 else (result.error_message or "")
            screenshots_count = len(result.screenshots)
            
            markdown_content += f"| {result.mod} | {result.environment} | {result.url} | {result.checkboxes_found} | {result.checkboxes_tested} | {search_status} | {results_status} | {result.runtime:.2f} | {screenshots_count} | {error} |\n"
        
        # Add test details
        markdown_content += f"""
---

## 📋 Test Details

- **Test Framework:** AGR BLAST UI Testing Framework
- **Report Generated:** {timestamp}
- **Base URL:** {self.base_url}
- **Screenshot Directory:** {self.screenshot_dir}
- **Browser:** Chrome (headless mode)
- **Test Sequences:** Biologically conserved sequences (18S rRNA, HSP70, Actin, Histone H3)

### Testing Methodology
1. **URL Discovery:** Automatic discovery from AGR BLAST service configuration files
2. **Checkbox Detection:** Automated discovery of all available database checkboxes
3. **Sequence Input:** Biologically relevant conserved sequences for cross-species compatibility
4. **Search Execution:** Automated BLAST search submission and result validation
5. **Screenshot Capture:** Visual documentation of each test step

### Configuration Sources
- Configuration files from `agr_blast_service_configuration/conf/`
- Latest available environments for each MOD
- Dynamic URL generation based on MOD and environment

*This report was automatically generated by the AGR BLAST UI Testing Framework.*
"""
        
        # Write to file
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(markdown_content)
        
        self.console.print(f"\n[green]📄 Markdown report saved to: {output_path}[/green]")


@click.command()
@click.option("-m", "--mod", type=click.Choice(['FB', 'WB', 'SGD', 'ZFIN', 'RGD', 'XB']),
              help="Model organism database to test")
@click.option("--sequence-type", type=click.Choice(['nucl', 'prot']), default='nucl',
              help="Type of sequence to test")
@click.option("--max-urls", type=int, help="Maximum URLs to test")
@click.option("--max-checkboxes", type=int, default=3, help="Maximum checkboxes to test per URL")
@click.option("--base-url", default="https://blast.alliancegenome.org/blast", 
              help="Base URL for BLAST interface")
@click.option("--config-dir", default="../agr_blast_service_configuration/conf",
              help="Path to AGR configuration directory")
@click.option("--markdown-report", help="Generate markdown report (specify filename)")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--discovery", is_flag=True, default=False, help="Discovery mode: find checkboxes and save to temp config file")
@click.option("--systematic", is_flag=True, default=False, help="Systematic mode: test individual checkboxes from saved config")
def main(mod, sequence_type, max_urls, max_checkboxes, base_url, config_dir, markdown_report, headless, discovery, systematic):
    """
    Comprehensive UI testing for BLAST web interface.
    
    Automatically discovers URLs from AGR BLAST service configuration,
    finds and tests checkboxes, and validates search functionality.
    
    Examples:
        # Discovery mode: Find and save all checkboxes (visible browser recommended)
        uv run python3 tests/ui/test_ui_comprehensive.py -m FB --discovery --no-headless
        
        # Systematic mode: Test individual checkboxes from saved config
        uv run python3 tests/ui/test_ui_comprehensive.py --systematic --max-checkboxes 5
        
        # Default comprehensive mode: Test multiple checkboxes at once  
        uv run python3 tests/ui/test_ui_comprehensive.py -m FB --sequence-type prot
        
        # Test with markdown report
        uv run python3 tests/ui/test_ui_comprehensive.py -m WB --markdown-report "reports/wb_ui_test.md"
    """
    console = Console()
    
    # Handle discovery mode
    if discovery:
        console.print("[bold blue]🔍 Running in Discovery Mode[/bold blue]")
        console.print("[dim]This will discover checkboxes and save them to temp_checkbox_config.json[/dim]")
        
        # Discover configurations first
        config_discovery = ConfigurationDiscovery(config_dir)
        configurations = config_discovery.discover_configurations(mod, base_url)
        
        if not configurations:
            console.print("[red]❌ No configurations discovered[/red]")
            return
        
        # Run checkbox discovery
        checkbox_discovery = CheckboxDiscovery(base_url, headless=headless)
        success = checkbox_discovery.run_discovery(configurations)
        
        if success:
            console.print("[green]✅ Discovery completed! Use --systematic to test individual checkboxes.[/green]")
        else:
            console.print("[red]❌ Discovery failed[/red]")
        return
    
    # Handle systematic testing mode
    if systematic:
        console.print("[bold green]🧪 Running in Systematic Testing Mode[/bold green]")
        console.print("[dim]This will test individual checkboxes from saved config[/dim]")
        
        systematic_tester = SystematicTester(headless=headless)
        results = systematic_tester.run_systematic_tests(max_checkboxes)
        
        if results:
            # Calculate detailed stats
            total_tests = len(results)
            passed_tests = sum(1 for r in results if r.search_successful and r.results_found)
            partial_tests = sum(1 for r in results if r.search_successful and not r.results_found)
            failed_tests = sum(1 for r in results if not r.search_successful)
            
            # Print detailed summary
            console.print(f"\n[bold cyan]📊 SYSTEMATIC TESTING RESULTS[/bold cyan]")
            console.print(f"[green]✅ PASSED: {passed_tests}/{total_tests} tests[/green] (Search successful + results found)")
            if partial_tests > 0:
                console.print(f"[yellow]⚠️  PARTIAL: {partial_tests}/{total_tests} tests[/yellow] (Search successful but no results)")
            if failed_tests > 0:
                console.print(f"[red]❌ FAILED: {failed_tests}/{total_tests} tests[/red] (Search failed)")
            
            overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            console.print(f"[bold]🎯 Overall Success Rate: {overall_success_rate:.1f}%[/bold]")
            
            # Generate report
            if markdown_report:
                report_generator = ReportGenerator()
                report_generator.generate_markdown_report(results, markdown_report)
                console.print(f"[dim]📄 Report saved to: {markdown_report}[/dim]")
        else:
            console.print("[red]❌ No tests were run[/red]")
        return
    
    # Default comprehensive mode (original functionality)
    console.print("[bold cyan]🚀 Running in Comprehensive Mode[/bold cyan]")
    
    # Discover configurations
    discovery = ConfigurationDiscovery(config_dir)
    configurations = discovery.discover_configurations(mod, base_url)
    
    if not configurations:
        console = Console()
        console.print("[red]❌ No configurations discovered[/red]")
        return
    
    # Run tests
    tester = UITester(base_url, headless)
    success = tester.run_comprehensive_tests(configurations, sequence_type, max_urls)
    
    # Generate markdown report if requested
    if markdown_report and success:
        tester.generate_markdown_report(markdown_report)
    
    if success:
        tester.console.print("\n[green]🎉 UI testing completed![/green]")
    else:
        tester.console.print("\n[red]💥 UI testing failed![/red]")


if __name__ == "__main__":
    main()