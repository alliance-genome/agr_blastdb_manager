"""
validation.py

BLAST database validation module for AGR BLAST Database Manager.
Provides post-creation validation using conserved and MOD-specific sequences.

Authors: Paulo Nuin, Adam Wright
Date: January 2025
"""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from terminal import (
    create_progress,
    log_error,
    log_success,
    log_warning,
    print_header,
    print_status,
    show_summary,
)


# Conserved sequences that should be found across all eukaryotic organisms
CONSERVED_SEQUENCES = {
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
GAGATACCAGCCTCGGCCCACTTACAGCTGAGTTCGAAGGCTGGTCCATC""",
}

# MOD-specific sequences for organism validation
MOD_SPECIFIC_SEQUENCES = {
    "FB": {
        "white_gene": """>Drosophila_white_gene_fragment
ATGGTCAATTACAAGGTGCGCAGCCTGGCCGAGGACTTCCTGGAGGAGGAGAAGAAGCC
GCTGATCTTCTCGGATCCGCCCAAATCCACCAAGCCCGAGTTCCAGTTCAGCGTGCTGG""",
        "rosy_gene": """>Drosophila_rosy_gene
ATGGCGGAAGAAGTGGCGATGTTGAAGGTGAAGGCCGGCAAGGGCAAGGTGGGCAAGCT
GGAGCGCTGGAACTACGCCAAGCACGTGGAGACCTACTCGCCCGAGATCGTGCACAAGG""",
    },
    "WB": {
        "unc_22": """>C_elegans_unc22_fragment
ATGAACACCAAAATCGTTGATACGATTGCAGATGAAACAACGTCCATTCCAGAAGAGAT
TCAAATCATGAAGACTTTAGGACCGGTCGATGGCGATCGCGACGCTCTGGAGACTCTCC""",
        "dpy_10": """>C_elegans_dpy10
ATGTCGTCAAAAAGAAGACTGAAAAAGCTATTAGCACTTGTATTAGCCGTTCTTCAAGC
AGTGTTCGCAAAACTCGTTGCTTCAGCCGGTGGAGCTGTACCAGGAGCCGTTATTGGCG""",
    },
    "SGD": {
        "GAL1": """>S_cerevisiae_GAL1_promoter
CGAGGCAAGCTAAACAGATCTCCAGAAGAAGGGTTGAATGATAGGAAACACATGAAATA
AAGCATTCTCAATATATTAAACTAAGTGAAAATCTTATAGGTGCCACTAAACCGTAACT""",
        "ACT1": """>S_cerevisiae_ACT1
ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCA
CGATGCATCATGGAAGATGCTGTTGTTCCCACATCCGTTTTCGCCGCAATAAGAAAAAC""",
    },
    "ZFIN": {
        "pax2a": """>zebrafish_pax2a_fragment
ATGGATAGCCCGAGGTTGCAGACAGATCTGCACGGAAGCCCAGTCATGTTCGCCTCGGT
CATCAACGGGACCAAGCTGGAGAAGAAAATCCGCCACACGAAGAGGATCTGCGCCAATG""",
        "sonic_hedgehog": """>zebrafish_shh
ATGCGGCTTTTGACGAGAATAGCCGGGCCGATCTTGCCATCTCCGTGATGAACCAGTGG
CCGCCCGTCCACAACAAAGACTCGAGCTGGGTGGATGTCCGAGGCCAAGGCAATCCTCG""",
    },
    "RGD": {
        "Alb": """>rat_albumin_fragment
ATGAAGTGGGTAACCTTTATTTCCCTTCTTTTTCTCTTTAGCTCGGCTTATTCCAGGGC
TGTGTGACTAGACTCACCAAATGCCATTGTCAATGGAAGCTGCACGCTGCCGTCCTGCA""",
        "Ins1": """>rat_insulin1
ATGGCCCTGTGGATGCGCCTCCTGCCCCTGCTGGCGCTGCTGGCCCTCTGGGGACCTGA
CCCAGCCGCAGCCTTTGTGAACCAACACCTGTGCGGCTCACACCTGGTGGAAGCTCTCT""",
    },
    "XB": {
        "sox2": """>xenopus_sox2_fragment
ATGTATAAGATGGCCACGGCAGCGCCCGGATGCACCGCTACGACGTGAGCGCCCTGCAG
TATAACTCCAACAACAACAGCAGCTACAGCATGATGCAGGACCAGCTGGGCTACCCGCA""",
        "bmp4": """>xenopus_bmp4
ATGATTCTTTACCGGCTCCAGTCTCTGGGCCTCTGCTTCCCGCAGCTGCTCGCCTCGAT
GCCCTCCCTGCTGACGGACTCCTTTTCTGGAATTCAGCCCTAAGCAAGATGCCGAGCCG""",
    },
}


class ValidationResult:
    """Container for validation results for a single database."""

    def __init__(
        self, db_name: str, db_path: str, mod: str, blast_type: str = "blastn"
    ):
        self.db_name = db_name
        self.db_path = db_path
        self.mod = mod
        self.blast_type = blast_type
        self.conserved_hits = 0
        self.specific_hits = 0
        self.total_hits = 0
        self.test_count = 0
        self.success = False
        self.error_message: Optional[str] = None
        self.hit_details: List[Dict] = []

    def add_hit(self, sequence_name: str, hit_count: int, identity: float):
        """Record a successful BLAST hit."""
        if hit_count > 0:
            self.hit_details.append(
                {"sequence": sequence_name, "hits": hit_count, "identity": identity}
            )
            self.total_hits += hit_count

    def get_hit_rate(self) -> float:
        """Calculate the percentage of tests that produced hits."""
        if self.test_count == 0:
            return 0.0
        tests_with_hits = len(self.hit_details)
        return (tests_with_hits / self.test_count) * 100


class DatabaseValidator:
    """Validates BLAST databases using conserved and MOD-specific sequences."""

    def __init__(
        self,
        logger,
        evalue: str = "10",
        word_size: str = "7",
        timeout: int = 30,
        num_threads: int = 2,
    ):
        """
        Initialize the validator.

        Args:
            logger: Logger instance for tracking operations
            evalue: E-value threshold for BLAST searches (default: 10 for validation)
            word_size: BLAST word size (default: 7 for sensitivity)
            timeout: Timeout in seconds for each BLAST search
            num_threads: Number of threads for BLAST
        """
        self.logger = logger
        self.evalue = evalue
        self.word_size = word_size
        self.timeout = timeout
        self.num_threads = num_threads
        self.logger.info("DatabaseValidator initialized")
        self.logger.info(
            f"Settings: evalue={evalue}, word_size={word_size}, timeout={timeout}s"
        )

    def discover_databases(self, base_path: str, mod: Optional[str] = None) -> Dict:
        """
        Discover all BLAST databases in the specified path.

        Args:
            base_path: Base directory to search for databases
            mod: Optional MOD filter (e.g., 'FB', 'WB')

        Returns:
            Dictionary mapping MODs to lists of (db_name, db_path) tuples
        """
        self.logger.info(f"Discovering databases in: {base_path}")
        base = Path(base_path)
        all_databases = {}

        if not base.exists():
            self.logger.error(f"Base path does not exist: {base_path}")
            return all_databases

        # Define MODs to search
        mods_to_search = [mod] if mod else ["FB", "SGD", "WB", "ZFIN", "RGD", "XB"]

        for mod_name in mods_to_search:
            mod_path = base / mod_name
            databases = []

            if mod_path.exists():
                # Find all .nin files (nucleotide databases)
                for nin_file in mod_path.rglob("*.nin"):
                    db_path = str(nin_file).replace(".nin", "")
                    db_name = nin_file.parent.name
                    databases.append((db_name, db_path))
                    self.logger.info(f"Found database: {mod_name}/{db_name}")

                # Find all .pin files (protein databases)
                for pin_file in mod_path.rglob("*.pin"):
                    db_path = str(pin_file).replace(".pin", "")
                    db_name = pin_file.parent.name
                    # Avoid duplicates
                    if not any(db[0] == db_name for db in databases):
                        databases.append((db_name, db_path))
                        self.logger.info(
                            f"Found protein database: {mod_name}/{db_name}"
                        )

            if databases:
                all_databases[mod_name] = databases
                self.logger.info(f"{mod_name}: Found {len(databases)} databases")

        total = sum(len(dbs) for dbs in all_databases.values())
        self.logger.info(f"Total databases discovered: {total}")

        return all_databases

    def run_blast_test(
        self, query_seq: str, db_path: str, blast_type: str = "blastn"
    ) -> Tuple[bool, int, float]:
        """
        Run a single BLAST test against a database.

        Args:
            query_seq: FASTA-formatted query sequence
            db_path: Path to BLAST database
            blast_type: Type of BLAST search (blastn, blastp, etc.)

        Returns:
            Tuple of (success, hit_count, best_identity)
        """
        try:
            # Write query to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".fasta", delete=False
            ) as tmp:
                tmp.write(query_seq)
                query_file = tmp.name

            # Run BLAST
            result = subprocess.run(
                [
                    blast_type,
                    "-query",
                    query_file,
                    "-db",
                    db_path,
                    "-outfmt",
                    "6 qseqid sseqid pident length evalue bitscore",
                    "-evalue",
                    self.evalue,
                    "-max_target_seqs",
                    "10",
                    "-word_size",
                    self.word_size,
                    "-num_threads",
                    str(self.num_threads),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Clean up temp file
            Path(query_file).unlink()

            # Parse results
            output_lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line and not line.startswith("Warning")
            ]

            if output_lines:
                # Get best identity from first hit
                parts = output_lines[0].split("\t")
                identity = float(parts[2]) if len(parts) > 2 else 0.0
                return True, len(output_lines), identity
            else:
                return False, 0, 0.0

        except subprocess.TimeoutExpired:
            self.logger.warning(f"BLAST timeout for {db_path}")
            if Path(query_file).exists():
                Path(query_file).unlink()
            return False, 0, 0.0
        except Exception as e:
            self.logger.error(f"BLAST error for {db_path}: {str(e)}")
            if "query_file" in locals() and Path(query_file).exists():
                Path(query_file).unlink()
            return False, 0, 0.0

    def validate_database(
        self, db_name: str, db_path: str, mod: str
    ) -> ValidationResult:
        """
        Validate a single database using conserved and MOD-specific sequences.

        Args:
            db_name: Name of the database
            db_path: Path to the database
            mod: MOD identifier (e.g., 'FB', 'WB')

        Returns:
            ValidationResult object with test results
        """
        # Determine BLAST type
        blast_type = "blastp" if ".pin" in db_path or "protein" in db_path.lower() else "blastn"

        result = ValidationResult(db_name, db_path, mod, blast_type)

        self.logger.info(f"Validating {mod}/{db_name} using {blast_type}")

        # Test with conserved sequences
        for seq_name, seq_content in CONSERVED_SEQUENCES.items():
            success, hits, identity = self.run_blast_test(
                seq_content, db_path, blast_type
            )
            result.test_count += 1
            if success:
                result.conserved_hits += hits
                result.add_hit(seq_name, hits, identity)
                self.logger.info(
                    f"  {seq_name}: {hits} hits (identity: {identity:.1f}%)"
                )

        # Test with MOD-specific sequences
        if mod in MOD_SPECIFIC_SEQUENCES:
            for seq_name, seq_content in MOD_SPECIFIC_SEQUENCES[mod].items():
                success, hits, identity = self.run_blast_test(
                    seq_content, db_path, blast_type
                )
                result.test_count += 1
                if success:
                    result.specific_hits += hits
                    result.add_hit(seq_name, hits, identity)
                    self.logger.info(
                        f"  {seq_name} (MOD-specific): {hits} hits (identity: {identity:.1f}%)"
                    )

        # Determine overall success
        result.success = result.total_hits > 0
        hit_rate = result.get_hit_rate()

        if result.success:
            self.logger.info(
                f"Validation PASSED for {db_name}: {result.total_hits} total hits, {hit_rate:.1f}% hit rate"
            )
        else:
            self.logger.warning(
                f"Validation FAILED for {db_name}: No hits found across {result.test_count} tests"
            )

        return result

    def validate_mod_databases(
        self, mod: str, databases: List[Tuple[str, str]]
    ) -> Dict:
        """
        Validate all databases for a specific MOD.

        Args:
            mod: MOD identifier
            databases: List of (db_name, db_path) tuples

        Returns:
            Dictionary with validation statistics
        """
        print_header(f"Validating {mod} Databases")
        start_time = datetime.now()

        stats = {
            "mod": mod,
            "total": len(databases),
            "passed": 0,
            "failed": 0,
            "total_hits": 0,
            "databases_with_conserved": 0,
            "databases_with_specific": 0,
            "results": [],
        }

        with create_progress() as progress:
            task = progress.add_task(
                f"Validating {mod} databases...", total=len(databases)
            )

            for db_name, db_path in databases:
                result = self.validate_database(db_name, db_path, mod)
                stats["results"].append(result)

                if result.success:
                    stats["passed"] += 1
                    stats["total_hits"] += result.total_hits

                    if result.conserved_hits > 0:
                        stats["databases_with_conserved"] += 1
                    if result.specific_hits > 0:
                        stats["databases_with_specific"] += 1
                else:
                    stats["failed"] += 1

                progress.advance(task)

        duration = datetime.now() - start_time

        # Show summary
        pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        conserved_rate = (
            (stats["databases_with_conserved"] / stats["total"] * 100)
            if stats["total"] > 0
            else 0
        )

        show_summary(
            f"{mod} Validation",
            {
                "Total Databases": stats["total"],
                "Passed": stats["passed"],
                "Failed": stats["failed"],
                "Pass Rate": f"{pass_rate:.1f}%",
                "Conserved Hits": stats["databases_with_conserved"],
                "Conserved Hit Rate": f"{conserved_rate:.1f}%",
                "Total Hits": stats["total_hits"],
            },
            duration,
        )

        stats["duration"] = duration
        return stats

    def validate_all(
        self, base_path: str, mod_filter: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Validate all databases in the specified path.

        Args:
            base_path: Base directory containing MOD databases
            mod_filter: Optional MOD filter to validate only one MOD

        Returns:
            Dictionary mapping MODs to their validation statistics
        """
        print_header("AGR BLAST Database Validation")
        print_status(
            f"E-value: {self.evalue}, Word size: {self.word_size}, Timeout: {self.timeout}s",
            "info",
        )

        # Discover databases
        all_databases = self.discover_databases(base_path, mod_filter)

        if not all_databases:
            log_error(f"No databases found in {base_path}")
            return {}

        # Show summary
        total_dbs = sum(len(dbs) for dbs in all_databases.values())
        print_status(f"Found {total_dbs} databases across {len(all_databases)} MODs", "info")

        # Validate each MOD
        all_results = {}
        overall_start = datetime.now()

        for mod in sorted(all_databases.keys()):
            databases = all_databases[mod]
            stats = self.validate_mod_databases(mod, databases)
            all_results[mod] = stats

        # Overall summary
        overall_duration = datetime.now() - overall_start
        total_passed = sum(r["passed"] for r in all_results.values())
        total_failed = sum(r["failed"] for r in all_results.values())
        overall_pass_rate = (
            (total_passed / total_dbs * 100) if total_dbs > 0 else 0
        )

        print_header("Overall Validation Summary")
        show_summary(
            "All MODs",
            {
                "Total Databases": total_dbs,
                "Total Passed": total_passed,
                "Total Failed": total_failed,
                "Overall Pass Rate": f"{overall_pass_rate:.1f}%",
            },
            overall_duration,
        )

        # Show warnings for low hit rates
        for mod, stats in all_results.items():
            pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            if pass_rate < 50:
                log_warning(
                    f"{mod} has low pass rate ({pass_rate:.1f}%) - may indicate specialized databases"
                )

        if overall_pass_rate < 50:
            log_warning(
                "Overall pass rate below 50% - databases may be specialized or require different BLAST programs"
            )
        else:
            log_success(f"Validation complete: {overall_pass_rate:.1f}% pass rate")

        return all_results
