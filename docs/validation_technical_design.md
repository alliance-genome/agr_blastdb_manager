# Database Validation Integration - Technical Design

**Version:** 1.0
**Date:** 2025-10-07
**Owner:** Engineering Team
**Related:** `prd_database_validation_integration.md`

---

## 1. Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     create_blast_db.py (Main CLI)               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. Parse CLI args (including --validate flag)           │   │
│  │  2. Create BLAST databases (existing logic)              │   │
│  │  3. If --validate: trigger DatabaseValidator             │   │
│  │  4. Display results via terminal.py                      │   │
│  │  5. Send to Slack if --update-slack                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              validation.py (New Module)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  DatabaseValidator (Main Orchestrator)                   │   │
│  │  ├─ discover_databases()                                 │   │
│  │  ├─ load_test_sequences()                                │   │
│  │  ├─ validate_database()                                  │   │
│  │  └─ aggregate_results()                                  │   │
│  │                                                          │   │
│  │  SequenceLibrary (Sequence Management)                   │   │
│  │  ├─ conserved_sequences                                  │   │
│  │  └─ mod_specific_sequences                               │   │
│  │                                                          │   │
│  │  BlastRunner (BLAST Execution)                           │   │
│  │  ├─ detect_db_type()                                     │   │
│  │  ├─ run_blast_query()                                    │   │
│  │  └─ parse_blast_output()                                 │   │
│  │                                                          │   │
│  │  ValidationReporter (Result Formatting)                  │   │
│  │  ├─ format_terminal_report()                             │   │
│  │  ├─ format_slack_message()                               │   │
│  │  └─ generate_diagnostics()                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│         Integration Points (Existing Modules)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  terminal.py: Rich-based formatting                      │   │
│  │  utils.py: Logging, Slack messaging                      │   │
│  │  BLAST+: blastn, blastp commands                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Input: --validate flag + created databases
    │
    ▼
1. Database Discovery
   ├─ Scan ../data/blast/{MOD}/{env}/databases/
   ├─ Find .nin files (nucleotide) and .pin files (protein)
   └─ Build DatabaseInfo objects
    │
    ▼
2. Sequence Loading
   ├─ Load 8 conserved sequences from SequenceLibrary
   ├─ Load MOD-specific sequences for current MOD
   └─ Write sequences to /tmp/*.fasta files
    │
    ▼
3. BLAST Validation (per database)
   ├─ Detect database type (blastn vs blastp)
   ├─ For each test sequence:
   │  ├─ Run BLAST query (e-value=10, word_size=7, timeout=30s)
   │  ├─ Parse output (hits, identity, bit score)
   │  └─ Collect results
   └─ Calculate database hit rate
    │
    ▼
4. Result Aggregation
   ├─ Combine results per MOD
   ├─ Calculate overall hit rate
   ├─ Identify top performers and failures
   └─ Generate diagnostics
    │
    ▼
5. Reporting
   ├─ Terminal: Rich-formatted tables and summaries
   ├─ Logs: Detailed validation events to {MOD}_{env}_{timestamp}.log
   ├─ Slack: Color-coded message with key metrics
   └─ Cleanup: Remove /tmp/*.fasta files
    │
    ▼
Output: Validation report + success/warning/failure status
```

---

## 2. Module Design

### 2.1 DatabaseValidator Class

**File:** `src/validation.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import subprocess
import time

@dataclass
class DatabaseInfo:
    """Information about a discovered database"""
    name: str
    path: str
    db_type: str  # 'nucleotide' or 'protein'
    mod: str
    environment: str

@dataclass
class BlastHit:
    """Single BLAST hit result"""
    query_id: str
    subject_id: str
    identity: float
    length: int
    evalue: float
    bit_score: float

@dataclass
class DatabaseResult:
    """Validation results for a single database"""
    db_info: DatabaseInfo
    conserved_hits: int
    mod_specific_hits: int
    total_hits: int
    best_identity: float
    test_time: float
    errors: List[str]

@dataclass
class ValidationSummary:
    """Aggregated validation results"""
    mod: str
    environment: str
    total_databases: int
    databases_with_conserved_hits: int
    databases_with_mod_hits: int
    database_results: List[DatabaseResult]
    total_time: float
    overall_hit_rate: float

class DatabaseValidator:
    """Main validation orchestrator"""

    def __init__(self, mod: str, environment: str, logger, config: Optional[Dict] = None):
        self.mod = mod
        self.environment = environment
        self.logger = logger
        self.config = config or self._default_config()
        self.sequence_lib = SequenceLibrary()
        self.blast_runner = BlastRunner(logger, self.config)

    def _default_config(self) -> Dict:
        return {
            'evalue': '10',
            'word_size': 7,
            'timeout': 30,
            'max_threads': 4,
            'min_hit_rate_warning': 0.5
        }

    def discover_databases(self) -> List[DatabaseInfo]:
        """Find all databases created in current run"""
        base_path = Path(f"../data/blast/{self.mod}/{self.environment}/databases")
        databases = []

        if not base_path.exists():
            self.logger.warning(f"Database path not found: {base_path}")
            return databases

        # Find nucleotide databases (.nin files)
        for nin_file in base_path.rglob("*.nin"):
            db_path = str(nin_file).replace('.nin', '')
            db_name = nin_file.parent.name
            databases.append(DatabaseInfo(
                name=db_name,
                path=db_path,
                db_type='nucleotide',
                mod=self.mod,
                environment=self.environment
            ))

        # Find protein databases (.pin files)
        for pin_file in base_path.rglob("*.pin"):
            db_path = str(pin_file).replace('.pin', '')
            db_name = pin_file.parent.name
            databases.append(DatabaseInfo(
                name=db_name,
                path=db_path,
                db_type='protein',
                mod=self.mod,
                environment=self.environment
            ))

        self.logger.info(f"Discovered {len(databases)} databases for validation")
        return databases

    def validate_database(self, db_info: DatabaseInfo) -> DatabaseResult:
        """Validate single database with all test sequences"""
        start_time = time.time()
        conserved_hits = 0
        mod_hits = 0
        best_identity = 0.0
        errors = []

        # Test with conserved sequences
        for seq_name, seq_content in self.sequence_lib.conserved_sequences.items():
            try:
                hits = self.blast_runner.run_blast(
                    sequence=seq_content,
                    db_path=db_info.path,
                    db_type=db_info.db_type,
                    sequence_name=seq_name
                )
                conserved_hits += len(hits)
                if hits:
                    best_identity = max(best_identity, max(h.identity for h in hits))
            except Exception as e:
                errors.append(f"Conserved {seq_name}: {str(e)}")

        # Test with MOD-specific sequences
        mod_seqs = self.sequence_lib.get_mod_sequences(self.mod)
        for seq_name, seq_content in mod_seqs.items():
            try:
                hits = self.blast_runner.run_blast(
                    sequence=seq_content,
                    db_path=db_info.path,
                    db_type=db_info.db_type,
                    sequence_name=seq_name
                )
                mod_hits += len(hits)
                if hits:
                    best_identity = max(best_identity, max(h.identity for h in hits))
            except Exception as e:
                errors.append(f"MOD {seq_name}: {str(e)}")

        return DatabaseResult(
            db_info=db_info,
            conserved_hits=conserved_hits,
            mod_specific_hits=mod_hits,
            total_hits=conserved_hits + mod_hits,
            best_identity=best_identity,
            test_time=time.time() - start_time,
            errors=errors
        )

    def validate_all(self) -> ValidationSummary:
        """Validate all discovered databases"""
        start_time = time.time()
        databases = self.discover_databases()

        if not databases:
            self.logger.error("No databases found to validate")
            return ValidationSummary(
                mod=self.mod,
                environment=self.environment,
                total_databases=0,
                databases_with_conserved_hits=0,
                databases_with_mod_hits=0,
                database_results=[],
                total_time=0.0,
                overall_hit_rate=0.0
            )

        self.logger.info(f"Starting validation of {len(databases)} databases")
        results = []

        for i, db_info in enumerate(databases, 1):
            self.logger.info(f"Validating [{i}/{len(databases)}]: {db_info.name}")
            result = self.validate_database(db_info)
            results.append(result)

            if result.errors:
                self.logger.warning(f"Errors in {db_info.name}: {result.errors}")

        # Aggregate results
        with_conserved = sum(1 for r in results if r.conserved_hits > 0)
        with_mod = sum(1 for r in results if r.mod_specific_hits > 0)
        total_hits = sum(r.total_hits for r in results)
        hit_rate = (with_conserved + with_mod) / (2 * len(results)) if results else 0.0

        return ValidationSummary(
            mod=self.mod,
            environment=self.environment,
            total_databases=len(databases),
            databases_with_conserved_hits=with_conserved,
            databases_with_mod_hits=with_mod,
            database_results=results,
            total_time=time.time() - start_time,
            overall_hit_rate=hit_rate
        )
```

### 2.2 SequenceLibrary Class

**File:** `src/validation.py`

```python
class SequenceLibrary:
    """Manages test sequences for validation"""

    def __init__(self):
        self.conserved_sequences = self._load_conserved_sequences()
        self.mod_sequences = self._load_mod_sequences()

    def _load_conserved_sequences(self) -> Dict[str, str]:
        """Load 8 highly conserved sequences"""
        return {
            "18S_rRNA": """>18S_ribosomal_RNA_conserved_region
GTCAGAGGTGAAATTCTTGGATCGCCGCAAGACGAACCAAAGCGAAAGCATTTGCCAAG
AATGTTTTCATTAATCAAGAACGAAAGTTAGAGGTTCGAAGGCGATCAGATACCGCCCT
AGTTCTAACCATAAACGATGCCGACCAGGGATCAGCGAATGTTACGCT""",

            "28S_rRNA": """>28S_ribosomal_RNA_conserved_region
GCCGGATCCTTTGAAGACGGGTCGCTTGCGACCCGACGCCAAGGAACCAAGCTGACCGT
CGAGGCAACCCACTCGGACGGGGGCCCAAGTCCAACTACGAGCTTTTTAACTGCAGCAA
CCGAAGCGTACCGCATGGCCGTTGCGCTTCGGC""",

            "COI_mt": """>COI_mitochondrial_conserved
CTGGATCAGGAACAGGTTGAACAGTTTACCCTCCTTTATCAGCAGGAATTGCTCATGCA
GGAGCATCAGTTGATTTAGCTATTTTTTCTTTACATTTAGCAGGAATTTCATCAATTTT
AGGAGCAGTAAATTTTATTACAACAGTAATTAATATACGATCAACA""",

            "actin": """>actin_conserved_region
ATGTGTGACGACGAGGAGACCACCGCCCTCGTCACCAGAGTCCATCACGATGCCAGTCC
TCAAGAACCCCTAAGGCCAACCGTGAAAAGATGACCCAGATCATGTTTGAGACCTTCAA
CACCCCCGCCATGTACGTTGCCATCCAGGCCGTGCTGTCCCT""",

            "gapdh": """>GAPDH_conserved_region
GTCGGAGTCAACGGATTTGGTCGTATTGGGCGCCTGGTCACCAGGGCTGCTTTTAACTC
TGGTAAAGTGGATATTGTTGCCATCAATGACCCCTTCATTGACCTCAACTACATGGTTT
ACATGTTCCAATATGATTCCACCCATGGCAAATTCCATGGCACCG""",

            "U6_snRNA": """>U6_snRNA_conserved
GTGCTCGCTTCGGCAGCACATATACTAAAATTGGAACGATACAGAGAAGATTAGCATGG
CCCCTGCGCAAGGATGACACGCAAATTCGTGAAGCGTTCCATATTT""",

            "histone_H3": """>histone_H3_conserved
GCGACCAACTTGTTGGGGACAACATTCGAAGTCTGGTCGGTCTCCTAAGCAGACCGGTG
GAAAAAGCAAACGACGGAAGGGCAAGGGAAGAAGACCCGCAGAGCGTCATGACCACCAC
AAGCAGACTGCGAGGAAGCAGCTGGCTACCAAGGCCGCTCGCAAGAGTGCGCCACGTGC""",

            "EF1a": """>EF1_alpha_conserved
GGTATTGGACAAACTGAAGGCTGAGCGTGAACGTGGTATCACCATTGATATCACACTTC
TCGGGTGCATCTCAACAGACTTCACATCAACATCGTCGTAATCGGACACGTCGATCTTG
GAGATACCAGCCTCGGCCCACTTACAGCTGAGTTCGAAGGCTGGTCCATC"""
        }

    def _load_mod_sequences(self) -> Dict[str, Dict[str, str]]:
        """Load MOD-specific test sequences"""
        return {
            "FB": {
                "white_gene": """>Drosophila_white_gene_fragment
ATGGTCAATTACAAGGTGCGCAGCCTGGCCGAGGACTTCCTGGAGGAGGAGAAGAAGCC
GCTGATCTTCTCGGATCCGCCCAAATCCACCAAGCCCGAGTTCCAGTTCAGCGTGCTGG""",
                "rosy_gene": """>Drosophila_rosy_gene
ATGGCGGAAGAAGTGGCGATGTTGAAGGTGAAGGCCGGCAAGGGCAAGGTGGGCAAGCT
GGAGCGCTGGAACTACGCCAAGCACGTGGAGACCTACTCGCCCGAGATCGTGCACAAGG"""
            },
            "WB": {
                "unc-22": """>C_elegans_unc22_fragment
ATGAACACCAAAATCGTTGATACGATTGCAGATGAAACAACGTCCATTCCAGAAGAGAT
TCAAATCATGAAGACTTTAGGACCGGTCGATGGCGATCGCGACGCTCTGGAGACTCTCC""",
                "dpy-10": """>C_elegans_dpy10
ATGTCGTCAAAAAGAAGACTGAAAAAGCTATTAGCACTTGTATTAGCCGTTCTTCAAGC
AGTGTTCGCAAAACTCGTTGCTTCAGCCGGTGGAGCTGTACCAGGAGCCGTTATTGGCG"""
            },
            "SGD": {
                "GAL1": """>S_cerevisiae_GAL1_promoter
CGAGGCAAGCTAAACAGATCTCCAGAAGAAGGGTTGAATGATAGGAAACACATGAAATA
AAGCATTCTCAATATATTAAACTAAGTGAAAATCTTATAGGTGCCACTAAACCGTAACT""",
                "ACT1": """>S_cerevisiae_ACT1
ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCA
CGATGCATCATGGAAGATGCTGTTGTTCCCACATCCGTTTTCGCCGCAATAAGAAAAAC"""
            },
            "ZFIN": {
                "pax2a": """>zebrafish_pax2a_fragment
ATGGATAGCCCGAGGTTGCAGACAGATCTGCACGGAAGCCCAGTCATGTTCGCCTCGGT
CATCAACGGGACCAAGCTGGAGAAGAAAATCCGCCACACGAAGAGGATCTGCGCCAATG""",
                "sonic_hedgehog": """>zebrafish_shh
ATGCGGCTTTTGACGAGAATAGCCGGGCCGATCTTGCCATCTCCGTGATGAACCAGTGG
CCGCCCGTCCACAACAAAGACTCGAGCTGGGTGGATGTCCGAGGCCAAGGCAATCCTCG"""
            },
            "RGD": {
                "Alb": """>rat_albumin_fragment
ATGAAGTGGGTAACCTTTATTTCCCTTCTTTTTCTCTTTAGCTCGGCTTATTCCAGGGC
TGTGTGACTAGACTCACCAAATGCCATTGTCAATGGAAGCTGCACGCTGCCGTCCTGCA""",
                "Ins1": """>rat_insulin1
ATGGCCCTGTGGATGCGCCTCCTGCCCCTGCTGGCGCTGCTGGCCCTCTGGGGACCTGA
CCCAGCCGCAGCCTTTGTGAACCAACACCTGTGCGGCTCACACCTGGTGGAAGCTCTCT"""
            },
            "XB": {
                "sox2": """>xenopus_sox2_fragment
ATGTATAAGATGGCCACGGCAGCGCCCGGATGCACCGCTACGACGTGAGCGCCCTGCAG
TATAACTCCAACAACAACAGCAGCTACAGCATGATGCAGGACCAGCTGGGCTACCCGCA""",
                "bmp4": """>xenopus_bmp4
ATGATTCTTTACCGGCTCCAGTCTCTGGGCCTCTGCTTCCCGCAGCTGCTCGCCTCGAT
GCCCTCCCTGCTGACGGACTCCTTTTCTGGAATTCAGCCCTAAGCAAGATGCCGAGCCG"""
            }
        }

    def get_mod_sequences(self, mod: str) -> Dict[str, str]:
        """Get MOD-specific sequences for given MOD"""
        return self.mod_sequences.get(mod, {})
```

### 2.3 BlastRunner Class

**File:** `src/validation.py`

```python
class BlastRunner:
    """Handles BLAST execution and output parsing"""

    def __init__(self, logger, config: Dict):
        self.logger = logger
        self.config = config

    def run_blast(self, sequence: str, db_path: str, db_type: str, sequence_name: str) -> List[BlastHit]:
        """Run BLAST query and return parsed hits"""
        # Write sequence to temp file
        query_file = Path(f"/tmp/validation_{sequence_name}_{int(time.time())}.fasta")
        query_file.write_text(sequence)

        try:
            # Determine BLAST program
            blast_program = "blastp" if db_type == "protein" else "blastn"

            # Build BLAST command
            cmd = [
                blast_program,
                '-query', str(query_file),
                '-db', db_path,
                '-outfmt', '6 qseqid sseqid pident length evalue bitscore',
                '-evalue', self.config['evalue'],
                '-word_size', str(self.config['word_size']),
                '-max_target_seqs', '10',
                '-num_threads', '2'
            ]

            self.logger.info(f"Running BLAST: {' '.join(cmd)}")

            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['timeout']
            )

            if result.returncode != 0:
                self.logger.error(f"BLAST failed: {result.stderr}")
                return []

            # Parse output
            hits = self._parse_blast_output(result.stdout)
            self.logger.info(f"Found {len(hits)} hits for {sequence_name}")
            return hits

        except subprocess.TimeoutExpired:
            self.logger.error(f"BLAST timeout for {sequence_name}")
            return []
        except Exception as e:
            self.logger.error(f"BLAST error for {sequence_name}: {str(e)}")
            return []
        finally:
            # Cleanup temp file
            if query_file.exists():
                query_file.unlink()

    def _parse_blast_output(self, output: str) -> List[BlastHit]:
        """Parse BLAST tabular output into BlastHit objects"""
        hits = []
        for line in output.strip().split('\n'):
            if not line or line.startswith('Warning'):
                continue

            parts = line.split('\t')
            if len(parts) >= 6:
                hits.append(BlastHit(
                    query_id=parts[0],
                    subject_id=parts[1],
                    identity=float(parts[2]),
                    length=int(parts[3]),
                    evalue=float(parts[4]),
                    bit_score=float(parts[5])
                ))
        return hits
```

### 2.4 ValidationReporter Class

**File:** `src/validation.py`

```python
from terminal import show_summary, print_status, print_header
from rich.table import Table
from rich import box

class ValidationReporter:
    """Formats validation results for different outputs"""

    @staticmethod
    def format_terminal_report(summary: ValidationSummary) -> None:
        """Display validation results in terminal using Rich"""
        from terminal import console

        # Header
        print_header(f"Database Validation Report - {summary.mod} {summary.environment}")

        # Summary table
        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="green")

        table.add_row("Total Databases", str(summary.total_databases))
        table.add_row(
            "With Conserved Hits",
            f"{summary.databases_with_conserved_hits}/{summary.total_databases} "
            f"({summary.databases_with_conserved_hits/summary.total_databases*100:.1f}%)"
        )
        table.add_row(
            "With MOD-Specific Hits",
            f"{summary.databases_with_mod_hits}/{summary.total_databases} "
            f"({summary.databases_with_mod_hits/summary.total_databases*100:.1f}%)"
        )
        table.add_row("Overall Hit Rate", f"{summary.overall_hit_rate*100:.1f}%")
        table.add_row("Validation Time", f"{summary.total_time:.1f}s")

        console.print(table)

        # Top performers
        top_performers = sorted(
            summary.database_results,
            key=lambda r: r.total_hits,
            reverse=True
        )[:5]

        if top_performers:
            console.print("\n[bold green]Top Performing Databases:[/bold green]")
            for i, result in enumerate(top_performers, 1):
                console.print(
                    f"  {i}. {result.db_info.name}: {result.total_hits} hits "
                    f"(conserved: {result.conserved_hits}, MOD: {result.mod_specific_hits})"
                )

        # Low hit databases
        low_performers = [r for r in summary.database_results if r.total_hits < 3]
        if low_performers:
            console.print("\n[bold yellow]⚠️  Databases with Low Hits:[/bold yellow]")
            for result in low_performers[:5]:
                console.print(f"  • {result.db_info.name}: {result.total_hits} hits")

        # Warnings
        if summary.overall_hit_rate < 0.5:
            console.print(
                "\n[bold red]⚠️  WARNING: Low overall hit rate detected![/bold red]"
            )
            console.print("   Possible reasons:")
            console.print("   • Specialized databases (protein-only, ncRNA, etc.)")
            console.print("   • Database indexing issues")
            console.print("   • Need for different BLAST programs (tblastx, blastx)")

    @staticmethod
    def format_slack_message(summary: ValidationSummary) -> Dict:
        """Format validation results for Slack"""
        # Determine color based on hit rate
        if summary.overall_hit_rate >= 0.8:
            color = "#36a64f"  # Green
            status = "PASSED"
            emoji = "🟢"
        elif summary.overall_hit_rate >= 0.5:
            color = "#ff9900"  # Orange
            status = "WARNING"
            emoji = "🟡"
        else:
            color = "#8D2707"  # Red
            status = "FAILED"
            emoji = "🔴"

        # Build message text
        text = f"{emoji} *Database Validation: {summary.mod} {summary.environment} - {status}*\n\n"
        text += f"*Overall Results:*\n"
        text += f"• Total Databases: {summary.total_databases}\n"
        text += f"• Conserved Hit Rate: {summary.databases_with_conserved_hits/summary.total_databases*100:.1f}% "
        text += f"({summary.databases_with_conserved_hits}/{summary.total_databases})\n"
        text += f"• MOD-Specific Hit Rate: {summary.databases_with_mod_hits/summary.total_databases*100:.1f}% "
        text += f"({summary.databases_with_mod_hits}/{summary.total_databases})\n"
        text += f"• Validation Time: {summary.total_time:.1f}s\n"

        # Top performers
        top = sorted(summary.database_results, key=lambda r: r.total_hits, reverse=True)[:3]
        if top:
            text += f"\n*📊 Top Performers:*\n"
            for r in top:
                text += f"• {r.db_info.name}: {r.total_hits} hits\n"

        # Low performers
        low = [r for r in summary.database_results if r.total_hits == 0]
        if low and len(low) <= 5:
            text += f"\n*❌ Databases with No Hits:*\n"
            for r in low[:5]:
                text += f"• {r.db_info.name}\n"

        return {
            "color": color,
            "title": f"Validation Report: {summary.mod} {summary.environment}",
            "text": text,
            "mrkdwn_in": ["text"]
        }
```

---

## 3. CLI Integration

### Updated create_blast_db.py

```python
@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
# ... existing options ...
@click.option(
    "--validate",
    help="Validate databases after creation",
    is_flag=True,
    default=False
)
@click.option(
    "--validation-evalue",
    help="E-value threshold for validation BLAST queries",
    default="10"
)
@click.option(
    "--validation-timeout",
    help="Timeout in seconds for each BLAST query",
    type=int,
    default=30
)
@click.option(
    "--skip-conserved-validation",
    help="Skip conserved sequence validation",
    is_flag=True,
    default=False
)
@click.option(
    "--skip-mod-validation",
    help="Skip MOD-specific sequence validation",
    is_flag=True,
    default=False
)
def create_dbs(
    # ... existing params ...
    validate: bool,
    validation_evalue: str,
    validation_timeout: int,
    skip_conserved_validation: bool,
    skip_mod_validation: bool,
) -> None:
    """Main function that runs the pipeline"""

    # ... existing database creation logic ...

    # NEW: Validation logic
    if validate and not check_parse_seqids:
        LOGGER.info("Starting database validation")

        from validation import DatabaseValidator, ValidationReporter

        # Build validation config
        val_config = {
            'evalue': validation_evalue,
            'timeout': validation_timeout,
            'skip_conserved': skip_conserved_validation,
            'skip_mod_specific': skip_mod_validation
        }

        # Run validation
        validator = DatabaseValidator(mod_code, environment, LOGGER, val_config)
        summary = validator.validate_all()

        # Report to terminal
        ValidationReporter.format_terminal_report(summary)

        # Add to Slack messages if requested
        if update_slack:
            slack_msg = ValidationReporter.format_slack_message(summary)
            SLACK_MESSAGES.append(slack_msg)

        LOGGER.info(f"Validation complete: {summary.overall_hit_rate*100:.1f}% hit rate")

    # ... rest of existing logic ...
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

**File:** `tests/unit/test_validation.py`

```python
import pytest
from src.validation import (
    DatabaseValidator,
    SequenceLibrary,
    BlastRunner,
    ValidationReporter
)

class TestSequenceLibrary:
    def test_conserved_sequences_loaded(self):
        lib = SequenceLibrary()
        assert len(lib.conserved_sequences) == 8
        assert "18S_rRNA" in lib.conserved_sequences
        assert "actin" in lib.conserved_sequences

    def test_mod_sequences_loaded(self):
        lib = SequenceLibrary()
        fb_seqs = lib.get_mod_sequences("FB")
        assert "white_gene" in fb_seqs
        assert "rosy_gene" in fb_seqs

        sgd_seqs = lib.get_mod_sequences("SGD")
        assert "GAL1" in sgd_seqs
        assert "ACT1" in sgd_seqs

class TestBlastRunner:
    def test_blast_command_construction(self, mocker):
        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = mocker.Mock(returncode=0, stdout="")

        runner = BlastRunner(logger=mocker.Mock(), config={'evalue': '10', 'word_size': 7, 'timeout': 30})
        runner.run_blast(
            sequence=">test\nACGT",
            db_path="/path/to/db",
            db_type="nucleotide",
            sequence_name="test"
        )

        # Verify blastn was called with correct params
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "blastn"
        assert "-evalue" in call_args
        assert "10" in call_args

    def test_blast_output_parsing(self):
        runner = BlastRunner(logger=mocker.Mock(), config={})
        output = "query1\tsubject1\t95.5\t100\t1e-50\t200.0\n"
        hits = runner._parse_blast_output(output)

        assert len(hits) == 1
        assert hits[0].identity == 95.5
        assert hits[0].evalue == 1e-50

class TestDatabaseValidator:
    def test_database_discovery(self, tmp_path):
        # Create mock database files
        db_dir = tmp_path / "data" / "blast" / "SGD" / "dev" / "databases" / "test_db"
        db_dir.mkdir(parents=True)
        (db_dir / "test.nin").touch()

        validator = DatabaseValidator("SGD", "dev", logger=mocker.Mock())
        databases = validator.discover_databases()

        assert len(databases) > 0
        assert databases[0].db_type == "nucleotide"
```

### 4.2 Integration Tests

```python
@pytest.mark.integration
class TestValidationIntegration:
    def test_full_validation_workflow(self, mock_blast_db):
        """Test complete validation workflow with mock database"""
        validator = DatabaseValidator("SGD", "dev", logger=logging.getLogger())
        summary = validator.validate_all()

        assert summary.total_databases > 0
        assert summary.overall_hit_rate >= 0
        assert summary.total_time > 0

    def test_cli_integration(self, cli_runner, mock_config):
        """Test --validate flag in CLI"""
        result = cli_runner.invoke(
            create_dbs,
            ['-j', mock_config, '-e', 'dev', '--validate']
        )

        assert result.exit_code == 0
        assert "Validation" in result.output
```

---

## 5. Performance Considerations

### Optimization Strategies

1. **Parallel Database Validation**
   - Use ThreadPoolExecutor to validate multiple databases concurrently
   - Configurable worker count (default: 4)
   - BLAST itself uses 2 threads per query

2. **Query File Reuse**
   - Write conserved sequences once, reuse across databases
   - Clean up only at end of validation

3. **Early Termination**
   - Stop testing database after N hits (configurable threshold)
   - Reduces time for high-quality databases

4. **Timeout Management**
   - Default 30s timeout per BLAST query
   - Prevents hanging on problematic databases

### Expected Performance

| Databases | Sequential Time | Parallel Time (4 workers) |
|-----------|----------------|---------------------------|
| 10        | ~4 min         | ~2 min                    |
| 20        | ~8 min         | ~4 min                    |
| 50        | ~20 min        | ~8 min                    |
| 100       | ~40 min        | ~15 min                   |

---

## 6. Configuration Management

### Validation Config Schema

```python
{
    # BLAST parameters
    'evalue': '10',              # Relaxed for validation
    'word_size': 7,              # Smaller for sensitivity
    'timeout': 30,               # Per-query timeout in seconds
    'max_threads': 4,            # Parallel validation workers

    # Thresholds
    'min_hit_rate_warning': 0.5, # Warn if hit rate < 50%
    'min_hits_per_db': 1,        # Flag if database has <1 hit

    # Feature flags
    'skip_conserved': False,     # Skip conserved sequence tests
    'skip_mod_specific': False,  # Skip MOD-specific tests

    # Advanced
    'early_termination_hits': None,  # Stop after N hits (None = no limit)
    'save_blast_output': False,      # Save raw BLAST output for debugging
}
```

### CLI to Config Mapping

```
--validate                        → Enable validation
--validation-evalue 1e-5         → config['evalue'] = '1e-5'
--validation-timeout 60          → config['timeout'] = 60
--skip-conserved-validation      → config['skip_conserved'] = True
--skip-mod-validation            → config['skip_mod_specific'] = True
```

---

## 7. Error Handling

### Error Scenarios

1. **BLAST Not Found**
   - Check: `which blastn` and `which blastp`
   - Error: "BLAST+ tools not found in PATH"
   - Recovery: Install BLAST+ or add to PATH

2. **Database Not Found**
   - Check: Database files exist and are readable
   - Error: "Database path invalid: {path}"
   - Recovery: Verify database creation completed

3. **BLAST Timeout**
   - After 30s (configurable), kill BLAST process
   - Log: "BLAST query timeout for {sequence} on {database}"
   - Recovery: Continue with next sequence/database

4. **BLAST Command Failure**
   - Capture stderr from BLAST
   - Log full command and error output
   - Recovery: Mark database as error, continue validation

5. **Sequence Library Load Failure**
   - Embedded sequences should never fail to load
   - If error: Fall back to subset of sequences
   - Alert: "Sequence library incomplete"

### Logging Strategy

```python
# Info: Normal operation
logger.info("Starting validation of 15 databases")
logger.info("Found 8 hits for 18S_rRNA in S_cerevisiae_genome.db")

# Warning: Potential issues
logger.warning("Low hit rate (45%) for C_elegans_ncRNA.db")
logger.warning("BLAST timeout for histone_H3 query")

# Error: Validation failures
logger.error("BLAST command failed: makeblastdb not run")
logger.error("Database path not found: /path/to/missing/db")
```

---

## 8. Deployment Checklist

### Pre-Deployment

- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests passing on dev environment
- [ ] Performance tested with 100+ databases
- [ ] Documentation complete (user guide, API docs, troubleshooting)
- [ ] Code review approved
- [ ] Security review completed (command injection, path traversal)

### Phase 1: Dev Deployment

- [ ] Deploy to dev branch
- [ ] Monitor all pipeline runs for 1 week
- [ ] Collect validation metrics and false positive/negative data
- [ ] Team training session conducted
- [ ] Feedback incorporated

### Phase 2: Staging Deployment

- [ ] Deploy to staging branch
- [ ] Require `--validate` for all staging runs
- [ ] Validate hit rate thresholds are appropriate
- [ ] Runbook validated with actual issues
- [ ] Performance meets SLA (<5 min for 20 databases)

### Phase 3: Production Deployment

- [ ] Deploy to main branch
- [ ] Optional flag initially (`--validate`)
- [ ] Monitor adoption rate and value delivery
- [ ] Collect production metrics for 2 weeks
- [ ] Consider default-on for Phase 4

### Post-Deployment

- [ ] Track key metrics (production incidents, QA time, hit rates)
- [ ] Monthly review of false positives/negatives
- [ ] Quarterly sequence library review
- [ ] Continuous improvement based on feedback

---

## 9. Future Enhancements

### Phase 2 Candidates

1. **Historical Database Validation Tool**
   - Standalone script to validate all production databases
   - Scheduled validation runs (weekly/monthly)
   - Trend analysis and alerting

2. **Custom Sequence Management**
   - Allow users to add their own test sequences
   - Sequence versioning and management UI
   - Community-contributed test sequences

3. **Advanced Diagnostics**
   - Auto-detection of database specialization (protein-only, ncRNA)
   - Suggested fixes for common issues
   - Integration with makeblastdb logs for root cause analysis

4. **CI/CD Integration**
   - Automatic validation on PR creation
   - Block merge if validation fails
   - GitHub status checks integration

5. **Web Dashboard**
   - Visual validation history and trends
   - Drill-down to individual database results
   - Comparison across MODs and environments

---

## 10. References

- **BLAST+ Manual:** https://www.ncbi.nlm.nih.gov/books/NBK279690/
- **AGR BLAST Pipeline:** `src/create_blast_db.py`
- **Existing Validation Test:** `origin/improved-error-reporting:tests/unit/test_database_validation.py`
- **Conserved Sequences Source:** Universal ribosomal RNA, housekeeping genes (NCBI RefSeq)
- **Rich Library Docs:** https://rich.readthedocs.io/

---

*This technical design is a living document and will be updated as implementation progresses. Code examples are illustrative and may be adjusted during development.*
