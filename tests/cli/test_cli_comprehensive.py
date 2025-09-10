#!/usr/bin/env python3
"""
Comprehensive CLI Testing Framework for BLAST Database Manager

A streamlined, robust testing framework that discovers and tests all locally available
BLAST databases using universal test sequences.

Features:
- Automatic database discovery
- Universal test sequences for all MODs
- Parallel testing for performance
- Comprehensive reporting
- Simple configuration
"""

import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import time
import logging
from dataclasses import dataclass

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel


# Universal test sequences - using highly conserved biological sequences
UNIVERSAL_SEQUENCES = {
    "nucl": {
        # 18S rRNA partial sequence - highly conserved across eukaryotes
        "FB": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        "WB": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA", 
        "SGD": "TACCTGGTTGATCCTGCCAGTAGTCATATGCTTGTCTCAAAGATTAAGCCATGCATGTCTAAGTATAAACAAATTGACGGAAGGGCACCACCAGGAGTGGAGCCTGCGGCTTAATTTGACTCAACACGGGGAAACTCACCAGGTCCAGA",
        # Actin gene partial sequence - universal cytoskeletal protein
        "universal": "ATGGATGATGATATCGCCGCGCTCGTCGTCGACAACGGCTCCGGCATGTGCAAGGCCGGCTTCGCGGGCGACGATGCCCCCCGGGCCGTCTTCCCCTCCATCGTCCACCGCAAATGCTTCTAG"
    },
    "prot": {
        # Heat shock protein 70 conserved domain
        "FB": "MAKAAAIGIDLGTTYSCVGVFQHGKVEIIANDQGNRTTPSYVAFTDTERLIGDAAKNQVAMNPTNTVFDAKRLIGRRFDDPSVQSDMKHWPFMVVNDAGRPKVQVEYKGETKSFYPEEISSMVLTKMKEIAEAYLGKTVTNAVVTVPAYFNDSQRQATKDAGTIAGLNVLRIINEPTAAAIAYGLDKKVGAERNVLIFDLGGGTFDVSILTIEDGIFEVKSTAGDTHLGGEDFDNRMVNHFIAEFKRKHKKDISENKRAVRRLRTACERAKRTLSSSTQASIEIDSLYEGIDFYTSITRARFEELNADLFRGTLDPVEKALRDAKLDKSQIHDIVLVGGSTRIPKIQKLLQDFFNGKELNKSINPDEAVAYGAAVQAAILSGDKSENVQDLLLLDVAPLSLGLETAGGVMTALIKRNSTIPTKQTQIFTTYSDNQPGVLIQVYEGERAMTKDNNLLGRFELSGIPPAPRGVPQIEVTFDIDANGILNVTATDKSTGKANKITITNDKGRLSKEDIERMVQEAEKYKAEDEKLKTGDIDKDNDGAYVLRGIEKQNKTDDNLRVSLFLLKALEKEPQKTGPEEEKVKSKVESRPETDEKEEPRKKVEALKDEEKKEEKQETDAKQVLETDQEGKQSQKDQEDHILQEPKSQE",
        # Actin protein sequence - highly conserved cytoskeletal protein
        "WB": "MDDDIAALVVDNGSGMCKAGFAGDDAPRAVFPSIVGRPRHQGVMVGMGQKDSYVGDEAQSKRGILTLKYPIEHGIVTNWDDMEKIWHHTFYNELRVAPEEHPVLLTEAPLNPKANREKMTQIMFETFNTPAMYVAIQAVLSLYASGRTTGIVMDSGDGVTHTVPIYEGYALPHAILRLDLAGRDLTDYLMKILTERGYSFTTTAEREIVRDIKEKLCYVALDFEQEMATAASSSSLEKSYELPDGQVITIGNERFRCPEALFQPSFLGMESCGIHETTFNSIMKCDVDIRKDLYANTVLSGGTTMYPGIADRMQKEITALAPSTMKIKIIAPPERKYSVWIGGSILASLSTFQQMWISKQEYDESGPSIVHRKCF",
        "SGD": "MTTFIGNSTAIQELFKRISEQFTAMFRRKAFLHWYTGEGMDEMEFTEAESNMNDLVSEYQQYQDATAADDDILMENQFTSDTPVQHVIYQGKDAASEEQLFKDLMKKLESLDLDRIGSEVVLSREKTLERIAGRSIIFDKGDENTIKKFLRLFNSNAEPKLGEQVRDVDNAALTQLTEDKLSHKWKELEVYYLRHDDLGKYIPNFGKLVEELGDLYLGQMDSKDSAVHDWEVGMFDDSYMSTLRSKAAYYQKMGFQGDGSHDVEIVDDAKDLEADLQWVTDGDKKWYKIAKLCLDCKDMLISGSLIAFLKTMFNAGAQQELSSGILTKASLLHKQGMLQYSAEETVVDDVSDKALIRSGGSAELLIKFYKRQHGYKRLFEEFGITGKFLLGSDLNPYNQDVEQVMNRLKDAMAAANPLKLKDSLIEVAMKTGDQKKEMIKRAQNEKRQVDAIERMGYVRSLLAETAYIVKNVNPDYILHAKDAGKVLKLIIKGHAFKTDEFLAIFRNAGSKLQPGEIFEQLEDRFMGLDKKTSDLVRSISDEKQRILLHGRRKLVVGKAIDQCNIMGTPAVIAACSADFDFVNPPLNFYDGVRLKIVGAKRVLDQQFGGMGYVHGFVGVARAFIPRTHQQENDFKKFVIQEGQGVTTAKGLAEDQINLHKKDKVYVIEPFMKIVQGDDAYKAYAATGETLTDEDVRFFRNLVGQVQLSADTKGYDTSIGGEVIALIDLSAKTLAYAAGFDNISGGSGYTGVGDSLYDYAIHGKSKSAELTSAKLRQIKEILYDSAPDTVKQTPVSQKLKAVVLMVGRNKEPAYQNLKRMTYAAALQRRPGVVDKKYYAAIPDLQKSIKMFETPQTLQRSQKSQMFPMKSTKKR",
        # Universal - Histone H3 core domain (highly conserved)
        "universal": "MARTKQTARKSTGGKAPRKQLATKAARKSAPATGGVKKPHRYRPGTVALREIRRYQKSTELLIRKLPFQRLVREIAQDFKTDLRFQSSAVMALQEACEAYLVGLFEDTNLCAIHAKRVTIMPKDIQLARRIRGERA"
    }
}


@dataclass
class BlastResult:
    """Container for BLAST search results"""
    database_path: str
    database_name: str
    blast_type: str
    success: bool
    hits: int
    runtime: float
    error_message: Optional[str] = None


class DatabaseDiscovery:
    """Discovers available BLAST databases with flexible release/environment discovery"""
    
    def __init__(self, data_dir: str = "data/blast"):
        self.data_dir = Path(data_dir)
        self.console = Console()
    
    def get_available_environments(self, mod: str) -> List[str]:
        """Get all available environments/releases for a given MOD"""
        mod_dir = self.data_dir / mod
        if not mod_dir.exists():
            return []
        
        # Look for subdirectories that contain databases
        environments = []
        for subdir in mod_dir.iterdir():
            if subdir.is_dir():
                # Check if this directory contains database files
                has_dbs = any(subdir.rglob("*.nin")) or any(subdir.rglob("*.pin"))
                if has_dbs:
                    environments.append(subdir.name)
        
        return sorted(environments)
    
    def discover_databases(self, mod: str = None, environment: str = None) -> Dict[str, List[str]]:
        """Discover all available BLAST databases with flexible environment discovery"""
        databases = {"nucl": [], "prot": []}
        
        if not self.data_dir.exists():
            self.console.print(f"[red]❌ Data directory not found: {self.data_dir}[/red]")
            return databases
        
        # If no environment specified, auto-discover available environments
        if mod and not environment:
            available_envs = self.get_available_environments(mod)
            if available_envs:
                self.console.print(f"[yellow]💡 Available environments for {mod}: {', '.join(available_envs)}[/yellow]")
                # Use all available environments
                for env in available_envs:
                    env_databases = self._discover_for_environment(mod, env)
                    databases["nucl"].extend(env_databases["nucl"])
                    databases["prot"].extend(env_databases["prot"])
                return databases
        
        # Specific MOD and environment
        if mod and environment:
            return self._discover_for_environment(mod, environment)
        
        # Search all MODs and environments
        search_pattern = "**/*.nin"
        nucl_files = list(self.data_dir.glob(search_pattern))
        
        search_pattern = "**/*.pin"
        prot_files = list(self.data_dir.glob(search_pattern))
        
        # Extract database paths (remove .nin/.pin extension)
        for nin_file in nucl_files:
            db_path = str(nin_file)[:-4]  # Remove .nin
            databases["nucl"].append(db_path)
        
        for pin_file in prot_files:
            db_path = str(pin_file)[:-4]  # Remove .pin
            databases["prot"].append(db_path)
        
        return databases
    
    def _discover_for_environment(self, mod: str, environment: str) -> Dict[str, List[str]]:
        """Discover databases for a specific MOD and environment"""
        databases = {"nucl": [], "prot": []}
        
        # Search within specific MOD/environment path
        search_path = self.data_dir / mod / environment
        if not search_path.exists():
            self.console.print(f"[yellow]⚠️  Path not found: {search_path}[/yellow]")
            return databases
        
        # Find nucleotide databases
        nucl_files = list(search_path.rglob("*.nin"))
        for nin_file in nucl_files:
            db_path = str(nin_file)[:-4]  # Remove .nin
            databases["nucl"].append(db_path)
        
        # Find protein databases  
        prot_files = list(search_path.rglob("*.pin"))
        for pin_file in prot_files:
            db_path = str(pin_file)[:-4]  # Remove .pin
            databases["prot"].append(db_path)
        
        return databases


class CLITester:
    """Streamlined CLI testing framework"""
    
    def __init__(self, data_dir: str = "data/blast"):
        self.console = Console()
        self.discovery = DatabaseDiscovery(data_dir)
        self.results: List[BlastResult] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_test_sequence(self, mod: str, molecule_type: str) -> str:
        """Get appropriate test sequence for MOD and molecule type"""
        if mod in UNIVERSAL_SEQUENCES[molecule_type]:
            return UNIVERSAL_SEQUENCES[molecule_type][mod]
        else:
            return UNIVERSAL_SEQUENCES[molecule_type]["universal"]
    
    def determine_blast_program(self, db_path: str, molecule_type: str) -> Optional[str]:
        """Determine BLAST program based on database type and query type"""
        has_nucl = Path(f"{db_path}.nin").exists()
        has_prot = Path(f"{db_path}.pin").exists()
        
        if molecule_type == "nucl":
            return "blastn" if has_nucl else "blastx" if has_prot else None
        elif molecule_type == "prot":
            return "blastp" if has_prot else "tblastn" if has_nucl else None
        
        return None
    
    def run_single_blast(self, db_path: str, sequence: str, blast_program: str, output_dir: str) -> BlastResult:
        """Run a single BLAST search"""
        start_time = time.time()
        db_name = Path(db_path).name
        
        # Create temporary query file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            f.write(f">test_query\n{sequence}\n")
            query_file = f.name
        
        # Setup output file
        output_file = Path(output_dir) / f"{db_name}_{blast_program}.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Run BLAST
            cmd = [
                blast_program,
                "-db", db_path,
                "-query", query_file,
                "-out", str(output_file),
                "-outfmt", "6",
                "-num_threads", "2",
                "-evalue", "1e-3",
                "-max_target_seqs", "10"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            runtime = time.time() - start_time
            
            if result.returncode == 0:
                # Count hits
                hits = 0
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        hits = len([line for line in f if line.strip()])
                
                return BlastResult(
                    database_path=db_path,
                    database_name=db_name,
                    blast_type=blast_program,
                    success=True,
                    hits=hits,
                    runtime=runtime
                )
            else:
                return BlastResult(
                    database_path=db_path,
                    database_name=db_name,
                    blast_type=blast_program,
                    success=False,
                    hits=0,
                    runtime=runtime,
                    error_message=result.stderr
                )
        
        except subprocess.TimeoutExpired:
            return BlastResult(
                database_path=db_path,
                database_name=db_name,
                blast_type=blast_program,
                success=False,
                hits=0,
                runtime=time.time() - start_time,
                error_message="Timeout after 60 seconds"
            )
        except Exception as e:
            return BlastResult(
                database_path=db_path,
                database_name=db_name,
                blast_type=blast_program,
                success=False,
                hits=0,
                runtime=time.time() - start_time,
                error_message=str(e)
            )
        finally:
            # Cleanup
            try:
                os.unlink(query_file)
            except:
                pass
    
    def run_tests(self, mod: str, environment: str = None, molecule_type: str = "nucl", 
                  max_dbs: int = None, parallel_jobs: int = 4, output_dir: str = "test_output",
                  markdown_report: str = None) -> bool:
        """Run comprehensive tests"""
        
        # Print banner
        self.console.print("\n[bold blue]🧪 AGR BLAST Database CLI Testing Framework[/bold blue]")
        self.console.print(f"[cyan]Testing {mod} databases ({molecule_type})[/cyan]\n")
        
        # Discover databases
        self.console.print("[yellow]🔍 Discovering databases...[/yellow]")
        databases = self.discovery.discover_databases(mod, environment)
        
        if molecule_type not in databases or not databases[molecule_type]:
            self.console.print(f"[red]❌ No {molecule_type} databases found for {mod}[/red]")
            return False
        
        db_list = databases[molecule_type]
        if max_dbs:
            db_list = db_list[:max_dbs]
        
        self.console.print(f"[green]✅ Found {len(db_list)} databases to test[/green]")
        
        # Get test sequence
        sequence = self.get_test_sequence(mod, molecule_type)
        self.console.print(f"[cyan]🧬 Using {len(sequence)} bp test sequence[/cyan]\n")
        
        # Setup output directory
        output_path = Path(output_dir) / mod
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Run tests with progress bar
        self.console.print("[yellow]🚀 Running BLAST searches...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Testing databases...", total=len(db_list))
            
            with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
                # Submit jobs
                futures = []
                for db_path in db_list:
                    blast_program = self.determine_blast_program(db_path, molecule_type)
                    if blast_program:
                        future = executor.submit(
                            self.run_single_blast,
                            db_path, sequence, blast_program, str(output_path)
                        )
                        futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    result = future.result()
                    self.results.append(result)
                    progress.advance(task)
        
        # Generate report
        test_config = {
            'mod': mod,
            'environment': environment,
            'molecule_type': molecule_type,
            'max_dbs': max_dbs,
            'parallel_jobs': parallel_jobs
        }
        
        if markdown_report:
            self.generate_markdown_report(markdown_report, test_config)
        
        self.generate_report()
        return True
    
    def generate_report(self, markdown_file: str = None):
        """Generate comprehensive test report"""
        self.console.print("\n[bold green]📊 Test Results Summary[/bold green]")
        
        # Statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        total_hits = sum(r.hits for r in self.results if r.success)
        avg_runtime = sum(r.runtime for r in self.results) / total if total > 0 else 0
        
        # Summary table
        summary = Table(title="Test Summary")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")
        
        summary.add_row("Total Tests", str(total))
        summary.add_row("Successful", str(successful))
        summary.add_row("Failed", str(failed))
        summary.add_row("Success Rate", f"{(successful/total*100):.1f}%" if total > 0 else "0%")
        summary.add_row("Total Hits", str(total_hits))
        summary.add_row("Avg Runtime", f"{avg_runtime:.2f}s")
        
        self.console.print(summary)
        
        # Show failures if any
        failures = [r for r in self.results if not r.success]
        if failures:
            self.console.print(f"\n[red]❌ Failed Tests ({len(failures)}):[/red]")
            for result in failures[:5]:  # Show first 5 failures
                error = result.error_message or "Unknown error"
                if len(error) > 60:
                    error = error[:60] + "..."
                self.console.print(f"   {result.database_name}: {error}")
            
            if len(failures) > 5:
                self.console.print(f"   ... and {len(failures) - 5} more failures")
        
        # Show top performers
        successful_results = [r for r in self.results if r.success and r.hits > 0]
        if successful_results:
            successful_results.sort(key=lambda x: x.hits, reverse=True)
            self.console.print(f"\n[green]🏆 Top Performers:[/green]")
            
            for result in successful_results[:5]:  # Top 5
                self.console.print(
                    f"   {result.database_name}: {result.hits} hits ({result.runtime:.2f}s)"
                )
        
        # Generate markdown report if requested
        if markdown_file:
            self.generate_markdown_report(markdown_file)
    
    def generate_markdown_report(self, filename: str, test_config: dict = None):
        """Generate detailed markdown report"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        total_hits = sum(r.hits for r in self.results if r.success)
        avg_runtime = sum(r.runtime for r in self.results) / total if total > 0 else 0
        
        # Sort results
        failures = [r for r in self.results if not r.success]
        successful_results = [r for r in self.results if r.success]
        top_performers = sorted([r for r in successful_results if r.hits > 0], 
                              key=lambda x: x.hits, reverse=True)
        
        # Generate markdown content
        markdown_content = f"""# BLAST Database CLI Test Report

**Generated:** {timestamp}

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total} |
| **Successful** | {successful} |
| **Failed** | {failed} |
| **Success Rate** | {(successful/total*100):.1f}% |
| **Total Hits** | {total_hits} |
| **Average Runtime** | {avg_runtime:.2f}s |

## 🎯 Test Configuration

"""
        
        if test_config:
            markdown_content += f"""| Parameter | Value |
|-----------|-------|
| **MOD** | {test_config.get('mod', 'N/A')} |
| **Environment** | {test_config.get('environment', 'All')} |
| **Molecule Type** | {test_config.get('molecule_type', 'N/A')} |
| **Max Databases** | {test_config.get('max_dbs', 'All')} |
| **Parallel Jobs** | {test_config.get('parallel_jobs', 'N/A')} |

"""
        
        # Test results section
        markdown_content += f"""## ✅ Test Results

### All Tests ({total} total)

| Database | BLAST Type | Status | Hits | Runtime (s) | Error |
|----------|------------|---------|------|-------------|-------|
"""
        
        # Add all results
        for result in self.results:
            status = "✅ Success" if result.success else "❌ Failed"
            error = result.error_message if result.error_message else ""
            if len(error) > 50:
                error = error[:50] + "..."
            
            markdown_content += f"| `{result.database_name}` | {result.blast_type} | {status} | {result.hits} | {result.runtime:.2f} | {error} |\n"
        
        # Failures section
        if failures:
            markdown_content += f"""
### ❌ Failed Tests ({len(failures)} total)

| Database | BLAST Type | Runtime (s) | Error Message |
|----------|------------|-------------|---------------|
"""
            for result in failures:
                error = result.error_message or "Unknown error"
                if len(error) > 100:
                    error = error[:100] + "..."
                markdown_content += f"| `{result.database_name}` | {result.blast_type} | {result.runtime:.2f} | {error} |\n"
        
        # Top performers section
        if top_performers:
            markdown_content += f"""
### 🏆 Top Performing Databases ({len(top_performers)} with hits)

| Rank | Database | BLAST Type | Hits | Runtime (s) |
|------|----------|------------|------|-------------|
"""
            for i, result in enumerate(top_performers[:10], 1):
                markdown_content += f"| {i} | `{result.database_name}` | {result.blast_type} | {result.hits} | {result.runtime:.2f} |\n"
        
        # Performance analysis
        if successful_results:
            fastest = min(successful_results, key=lambda x: x.runtime)
            slowest = max(successful_results, key=lambda x: x.runtime)
            
            markdown_content += f"""
## 📈 Performance Analysis

### Runtime Statistics
- **Fastest Search:** `{fastest.database_name}` ({fastest.runtime:.2f}s)
- **Slowest Search:** `{slowest.database_name}` ({slowest.runtime:.2f}s)
- **Runtime Range:** {fastest.runtime:.2f}s - {slowest.runtime:.2f}s
- **Standard Deviation:** {(sum((r.runtime - avg_runtime)**2 for r in successful_results) / len(successful_results))**0.5:.2f}s

### Database Types Tested
"""
            
            # Count database types
            blast_types = {}
            for result in self.results:
                blast_types[result.blast_type] = blast_types.get(result.blast_type, 0) + 1
            
            for blast_type, count in blast_types.items():
                success_count = sum(1 for r in self.results if r.blast_type == blast_type and r.success)
                success_rate = (success_count / count * 100) if count > 0 else 0
                markdown_content += f"- **{blast_type}:** {count} databases tested, {success_count} successful ({success_rate:.1f}%)\n"
        
        # Footer
        markdown_content += f"""
---

## 📋 Test Details

- **Test Framework:** AGR BLAST Database CLI Testing Framework
- **Report Generated:** {timestamp}
- **Test Sequence Length:** {len(self.get_test_sequence('FB', 'nucl'))} bp (nucleotide), {len(self.get_test_sequence('FB', 'prot'))} aa (protein)
- **Timeout Setting:** 60 seconds per search
- **Output Format:** BLAST tabular format (outfmt 6)
- **E-value Threshold:** 1e-3

### Environment Information
- **Test Environment:** Local development
- **BLAST+ Version:** System default
- **Parallel Processing:** Enabled (ThreadPoolExecutor)

*This report was automatically generated by the AGR BLAST Database CLI Testing Framework.*
"""
        
        # Write to file
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(markdown_content)
        
        self.console.print(f"\n[green]📄 Markdown report saved to: {output_path}[/green]")


@click.command()
@click.option("-m", "--mod", required=True, type=click.Choice(['FB', 'WB', 'SGD', 'ZFIN', 'RGD', 'XB']),
              help="Model organism database")
@click.option("-e", "--environment", help="Environment filter (e.g., FB_test, WB_test)")
@click.option("--max-dbs", type=int, help="Maximum databases to test")
@click.option("--molecule-type", type=click.Choice(['nucl', 'prot']), default='nucl',
              help="Molecule type to test")
@click.option("-j", "--parallel-jobs", type=int, default=4, help="Parallel jobs")
@click.option("-o", "--output-dir", default="test_output", help="Output directory")
@click.option("--markdown-report", help="Generate markdown report (specify filename)")
@click.option("--data-dir", default="data/blast", help="Custom data directory for databases")
def main(mod, environment, max_dbs, molecule_type, parallel_jobs, output_dir, markdown_report, data_dir):
    """
    Comprehensive CLI testing for BLAST databases.
    
    Examples:
      # Test all FB databases
      python test_cli_comprehensive.py -m FB
      
      # Test first 5 WB nucleotide databases
      python test_cli_comprehensive.py -m WB --max-dbs 5
      
      # Test FB protein databases in FB_test environment
      python test_cli_comprehensive.py -m FB -e FB_test --molecule-type prot
    """
    tester = CLITester(data_dir=data_dir)
    success = tester.run_tests(
        mod=mod,
        environment=environment,
        molecule_type=molecule_type,
        max_dbs=max_dbs,
        parallel_jobs=parallel_jobs,
        output_dir=output_dir,
        markdown_report=markdown_report
    )
    
    if success:
        tester.console.print("\n[green]🎉 Testing completed![/green]")
        sys.exit(0)
    else:
        tester.console.print("\n[red]💥 Testing failed![/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()