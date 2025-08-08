#!/usr/bin/env python3
"""
test_blast_databases.py

This script validates BLAST databases created by the AGR BLAST database manager.
It performs searches against created databases using test sequences to ensure
proper database creation and functionality.

Authors: Paulo Nuin, Adam Wright
Date: July 2025
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Dict, List, Optional, Tuple

import click
import yaml

from terminal import (create_progress, log_error, log_success, log_warning,
                      print_header, print_status, show_summary)
from utils import setup_detailed_logger

# Test sequences for different MODs
DEFAULT_TEST_SEQUENCES = {
    "SGD": {
        "nucl": "ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCACGGTCCCAATTGCTCGAGAGATTTCTCTTTTACCTTTTTTTACTATTTTTCACTCTCCCATAACCTCCTATATTGACTGATCTGTAATAACCACGATATTATTGGAATAAATAGGGGCTTGAAATTTGGAAAAAAAAAAAAAACTGAAATATTTTCGTGATAAGTGATAGTGATATTCTTCTTTTATTTGCTACTGTTACTAAGTCTCATGTACTAACATCGATTGCTTCATTCTTTTTGTTGCTATATTATATGTTTAGAGGTTGCTGCTTTGGTTATTGATAACGGTTCTGGTATGTGTAAAGCCGGTTTTGCCGGTGACGACGCTCCTCGTGCTGTCTTCCCATCTATCGTCGGTAGACCAAGACACCAAGGTATCATGGTCGGTATGGGTCAAAAAGACTCCTACGTTGGTGATGAAGCTCAATCCAAGAGAGGTATCTTGACTTTACGTTACCCAATTGAACACGGTATTGTCACCAACTGGGACGATATGGAAAAGATCTGGCATCATACCTTCTACAACGAATTGAGAGTTGCCCCAGAAGAACACCCTGTTCTTTTGACTGAAGCTCCAATGAACCCTAAATCAAACAGAGAAAG",
        "prot": "MDSEVAALVIDNGSGMCKAGFAGDDAPRAVFPSIVGRPRHQGIMVGMGQKDSYVGDEAQSKRGILTLRYPIEHGIVTNWDDMEKIWHHTFYNELRVAPEEHPVLLTEAPMNPKSNREKMTQIMFETFNVPAFYVSIQAVLSLYSSGRTTGIVLDSGDGVTHVVPIYAGFSLPHAILRIDLAGRDLTDYLMKILSERGYSFSTTAEREIVRDIKEKLCYVALDFEQEMQTAAQSSSIEKSYELPDGQVITIGNERFRAPEALFHPSVLGLESAGIDQTTYNSIMKCDVDVRKELYGNIVMSGGTTMFPGIAERMQKEITALAPSSMKVKIIAPPERKYSVWIGGSILASLTTFQQMWISKQEYDESGPSIVHHKCF",
    },
    "FB": {
        "nucl": "AGTTTGGTTTCGTACTTGGCTCATTGCGCTCGTGCAGCTCGATATCCCAATCCCCGAGAGCTAGATGCTCCACTCTGCTGCTCGAAGGAAGCGACTCGGCTGATTGGATACATAATTCTCAGGAGTGTCAGATAGTTGCAAGCGACCATGCGCGCATGGCTTCTACTCCTCGCAGTGCTGGCGACTTTTCAAACGATTGTTCGAGTTGCTAGCACCGAGGATATATCCCAGAGATTCATCGCCGCCATAGCGCCCGTTGCCGCTCATATTCCGCTGGCATCAGCATCAGGATCAGGATCAGGACGATCTGGATCTAGATCGGTAGGAGCCTCGACCAGCACAGCATTAGCAAAAGCATTTAATCCATTCAGCGAGCCCGCCTCGTTCAGTGATAGTGATAAAAGCCATCGGAGTAAAACAAACAAAAAACCTAGCAAAAGTGACGCGAACCGACAGTTCAACGAAGTGCATAAGCCAAGAACAGACCAATTAGAAAATTCCAAAAATAAGTCTAAACAATTAGTTAATAAACCCAACCACAACAAAATGGCTGTCAAGGAGCAGAGGAGCCACCACAAGAAGAGCCACCACCATCGCAGCCACCAGCCAAAGCAGGCCAGTGCATCCACAGAATCTCATCAATCCTCGTCGATTGAATCAATCTTCGTGGAGGAGCCGACGCTGGTGCTCGACCGCGAGGTGGCCTCCATCAACGTGCCCGCCAACGCCAAGGCCATCATCGCCGAGCAGGGCCCGTCCACCTACAGCAAGGAGGCGCTCATCAAGGACAAGCTGAAGCCAGACCCCTCCACTCTAGTCGAGATCGAGAAGAGCCTGCTCTCGCTGTTCAACATGAAGCGGCCGCCCAAGATCGACCGCTCCAAGATCATCATCCCCGAGCCGATGAAGAAGCTCTACGCCGAGATCATGGGCCACGAGCTCGACTCGGTCAACATCCCCAAGCCGGGTCTGCTGACCAAGTCGGCCAACACAGTGCGAAGTTTTACACACAAAGATAGTAAAATCGACGATCGATTTCCGCACCACCACCGGTTTCGGCTGCACTTCGACGTGAAGAGCATTCCCGCCGACGAGAAGCTGAAGGCGGCGGAGCTGCAGCTGACCCGGGACGCACTCAGTCAACAGGTGGTGGCCAGCAGATCGTCGGCGAATCGGACGCGCTACCAGGTGCTTGTCTACGACATCACGCGCGTCGGGGTGCGTGGTCAGCGGGAGCCGAGCTATCTGCTGTTGGACACCAAGACGGTCCGGCTTAACAGCACGGACACGGTGAGCCTCGATGTCCAGCCGGCCGTGGACCGGTGGCTGGCGAGTCCGCAGCGCAACTACGGACTGCTGGTGGAGGTGCGGACGGTCCGCTCCCTGAAGCCGGCCCCACACCACCATGTACGCCTGCGCCGCAGCGCGGACGAGGCGCACGAGCGGTGGCAGCACAAGCAGCCGCTCCTGTTCACCTACACGGACGACGGGCGGCACAAGGCGCGCTCCATTCGGGACGTGTCTGGCGGAGAGGGCGGTGGCAAGGGCGGCCGGAACAAGCGGCAGCCGAGACGGCCTACGAGGCGCAAGAACCACGACGACACCTGCCGGCGGCACTCGCTGTACGTGGACTTCTCGGACGTGGGCTGGGACGACTGGATTGTGGCGCCTCTGGGCTACGATGCATATTACTGCCACGGGAAGTGCCCCTTCCCGCTGGCCGACCACTTTAACTCGACCAATCACGCCGTGGTGCAGACCCTGGTCAACAATATGAATCCCGGCAAGGTGCCGAAGGCGTGCTGCGTGCCCACGCAACTGGACAGCGTGGCCATGCTCTATCTCAACGACCAAAGTACGGTGGTGCTGAAGAACTACCAGGAGATGACCGTGGTGGGCTGTGGCTGTCGATAGATTCGCACCACCATCGCACCATACCACGCCATCCACTCAACCGAGTGAATGCGATGGGAAATCGCGAGCGAGAGAGCATCAAATGCTGTTTGGTTCCAAGCCGTCAATGCTTTAAACACAACGCAAACAAAATGGACTGAATATTTGAATTTTAAGTGTAAATCGTTAGACTTTAGCCGTATCGAGTAACGAGCAAACAGGCGGCAGCCACGCCCACATCCACGTCCCCACCAAAACCGCCCGCCTTGGAGCCTCTGTCGATTTCCCCAGCCAGGCTGGCGAAAAATCCCAGATCAGAGTGCAGATTTGAGAGCGCAGAGTCCACTGTATATAGCCGCCATGCCACGCCCCCAACACAGATAGTCCCCGCCCATCCGCCAGATACTTCAGATATTAGATACTTTCGTATCTGTGTGCGCTGCTGCTGCTGAAGGAGAAGTTAAGGGAGGAAAAGAGGAGTATGCTTAGGAGTAAGAGCGACCAATTGAACAAATTGTATAGAAATGCTAATATATATTAAAAAACCCTATCGATGCGAACTGGTATCTTTGTATACATTTGTACATGTATGTGGAAAGGAGACCTATTCTACTAGCCGTTTTTGTTAATAATTTTATAAAGCAATAGCAAACCACTTGTAAATTAACTAGCGAGAGCATAACCGAATAATGACTTGAAATTACTTAGGAACTATCATCCTAAACACATAGTTGTAGAAAGACCAGAAAAACAAACAGATATTGCATATGTAACTCTCTTGTATATGTACTAAACACCTATATACTTTATATGCGGTACACACTCACTCACCCCCATTAGCAAACACACAACCACACACACATATCGACGAAAGGGTATTCAAACTTCGTTGCGCATTCAACTAAACGTAACTGTATAAACAAAACGAATGCCCTATAAATATATGAATAACTATCTACATCGTTATGCGTTCTAAGCTAAGCTCGAATAAATCCGTAAACGTTAATTAATCTAGAATCGTAAGACCTAACGCGTAAGCTCAGCATGTTGGATAAATTAATAGAAACGAGAGAAAAGAGAAAAAACCCCACAAAAAGAAAACCCGATAAATGGAAAATATCGATTCGTGCCTGATGTTGCAGCGCACGTCTCGTATATGCAGTTTGTCATATAAACATTATTATTTTATTTATTTAAAACAACCCGTATTTTTGAGGACGACGACGATGATGCAGGAGCAAGGATGAAAAGAAAGATGAAAAATATAAAAGAAAACAATTTATT",
        "prot": "MAGIFRSTSLNHSSDVPGTPFKRYSLNSNNSTFCTSPGALQDVTMENSYASFDVPRPPGGGNSPLPSQGRSVRELEEQMSALRKENFNLKLRIYFLEEGQPGARADSSTESLSKQLIDAKIEIATLRKTVDVKMELLKDAARAISHHEELQRKADIDSQAIIDELQEQIHAYQMAESGGQPVENIAKTRKMLRLESEVQRLEEELVNIEARNVAARNELEFMLAERLESLTACEGKIQELAIKNSELVERLEKETASAESSNANRDLGAQLADKICELQEAQEKLKERERIHEQACRTIQKLMQKLSSQEKEIKKLNQENEQSANKENDCAKTVISPSSSGRSMSDNEASSQEMSTNLRVRYELKINEQEEKIKQLQTEVKKKTANLQNLVNKELWEKNREVERLTKLLANQQKTLPQISEESAGEADLQQSFTEAEYMRALERNKLLQRKVDVLFQRLADDQQNSAVIGQLRLELQQARTEVETADKWRLECVDVCSVLTNRLEELAGFLNSLLKHKDVLGVLAADRRNAMRKAVDRSLDLSKSLNMTLNITATSLADQSLAQLCNLSEILYTEGDASHKTFNSHEELHAATSMAPTVENLKAENKALKKELEKRRSSEGQRKERRSLPLPSQQFDNQSESEAWSEPDRKVSLARIGLDETSNSLAAPEQAISESESEGRTCATRQDRNRNSERIAQLEEQIAQKDERMLNVQCQMVELDNRYKQEQLRCLDITQQLEQLRAINEALTADLHAIGSHEEERMVELQRQLELKNQQIDQLKLAHSTLTADSQITEMELQALQQQMQEIEQLHADSVETLQSQLQKLKLDAVQQLEEHERLHREALERDWVALTTYQEQAQQLLELQRSLDYHQENEKELKQTLVENELATRALKKQLDESTLQASKAVMERTKAYNDKLQLEKRSEELRLQLEALKEEHQKLLQKRSNSSDVSQSGYTSEEVAVPMGPPSGQATTCKQAAAAVLGQRVNTSSPDLGIESDAGRISSVEVSNAQRAMLKTVEMKTEGSASPKAKSEESTSPDSKSNVATGAATVHDCAKVDLENAELRRKLIRTKRAFEDTYEKLRMANKAKAQVEKDIKNQILKTHNVLRNVRSNMENEL",
    },
    "WB": {
        "nucl": "ATGGCTGAAATCTTCAGGTCAACTTCACTAAATCATTCATCAGATGTGCCTGGTACACCATTTAAGCGATATTCATTGAATTCAAATAATTCAACATTTTGTACCAGTCCTGGTGCACTACAAGACGTGACAATGGAAAATTCATATGCTTCATTCGATGTTCCAAGACCACCAGGTGGTGGTAATTCACCATTACCATCACAAGGTAGATCAGTTAGAGAATTGGAAGAACAAATGTCTGCATTGAGAAAAGAAAATTTCAATTTAAAATTGAGAATATATTTTTTAGAAGAAGGGCAACCAGGTGCTAGAGCTGATTCATCAACAGAGTCTTTGTCTAAGCAATTGATTGATGCAAAAATTGAAATTGCAACATTAAGAAAAACTGTTGATGTTAAAATGGAATTGTTAAAAGAT",
        "prot": "MAEIFRSTSTNHSSDVPGTPFKRYSLNSNNSTFCTSPGALQDVTMENSYASFDVPRPPGGGNSPLPSQGRSVRELEEQMSALRKENFNLKLRIYFLEEGQPGARADSSTESLSKQLIDAKIEIATLRKTVDVKMELLKD",
    },
    "ZFIN": {
        "nucl": "ATGGCGGAGATCTTCAGATCGACGAGCTTGAACCACAGCAGCGACGTGCCCGGCACCCCGTTCAAGAGATACAGCCTGAACAGCAACAACTCGACCTTCTGCACGAGCCCGGGCGCGCTGCAGGACGTGACGATGGAGAACAGCTACGCGAGCTTCGACGTGCCGCGGCCGCCGGGCGGCGGCAACAGCCCGCTGCCGAGCCAGGGCAGAAGCGTGCGCGAGCTGGAGGAACAGATGAGCGCGCTGCGCAAGGAGAACTTCAACCTGAAACTGAGATCATACTTCCTCGAAGAAGGACAGCCGGGCGCCAGGGCGGACAGCAGCACCGAGAGCCTGTCGAAGCAGCTGATCGACGCCAAGATCGAGATCGCCACCCTGAGGAAAACCGTGGACGTGAAGATGGAGCTGCTGAAGGAC",
        "prot": "MAEIFRSTSTNHSSDVPGTPFKRYSLNSNNSTFCTSPGALQDVTMENSYASFDVPRPPGGGNSPLPSQGRSVRELEEQMSALRKENFNLKLRIYFLEEGQPGARADSSTESLSKQLIDAKIEIATLRKTVDVKMELLKD",
    },
    "RGD": {
        "nucl": "ATGGCGGAGATCTTCAGATCGACGAGCTTGAACCACAGCAGCGACGTGCCCGGCACCCCGTTCAAGAGATACAGCCTGAACAGCAACAACTCGACCTTCTGCACGAGCCCGGGCGCGCTGCAGGACGTGACGATGGAGAACAGCTACGCGAGCTTCGACGTGCCGCGGCCGCCGGGCGGCGGCAACAGCCCGCTGCCGAGCCAGGGCAGAAGCGTGCGCGAGCTGGAGGAACAGATGAGCGCGCTGCGCAAGGAGAACTTCAACCTGAAACTGAGATCATACTTCCTCGAAGAAGGACAGCCGGGCGCCAGGGCGGACAGCAGCACCGAGAGCCTGTCGAAGCAGCTGATCGACGCCAAGATCGAGATCGCCACCCTGAGGAAAACCGTGGACGTGAAGATGGAGCTGCTGAAGGAC",
        "prot": "MAEIFRSTSTNHSSDVPGTPFKRYSLNSNNSTFCTSPGALQDVTMENSYASFDVPRPPGGGNSPLPSQGRSVRELEEQMSALRKENFNLKLRIYFLEEGQPGARADSSTESLSKQLIDAKIEIATLRKTVDVKMELLKD",
    },
    "XB": {
        "nucl": "ATGGCGGAGATCTTCAGATCGACGAGCTTGAACCACAGCAGCGACGTGCCCGGCACCCCGTTCAAGAGATACAGCCTGAACAGCAACAACTCGACCTTCTGCACGAGCCCGGGCGCGCTGCAGGACGTGACGATGGAGAACAGCTACGCGAGCTTCGACGTGCCGCGGCCGCCGGGCGGCGGCAACAGCCCGCTGCCGAGCCAGGGCAGAAGCGTGCGCGAGCTGGAGGAACAGATGAGCGCGCTGCGCAAGGAGAACTTCAACCTGAAACTGAGATCATACTTCCTCGAAGAAGGACAGCCGGGCGCCAGGGCGGACAGCAGCACCGAGAGCCTGTCGAAGCAGCTGATCGACGCCAAGATCGAGATCGCCACCCTGAGGAAAACCGTGGACGTGAAGATGGAGCTGCTGAAGGAC",
        "prot": "MAEIFRSTSTNHSSDVPGTPFKRYSLNSNNSTFCTSPGALQDVTMENSYASFDVPRPPGGGNSPLPSQGRSVRELEEQMSALRKENFNLKLRIYFLEEGQPGARADSSTESLSKQLIDAKIEIATLRKTVDVKMELLKD",
    },
}

# Global variables
LOGGER = setup_detailed_logger("test_blast_databases", "blast_db_testing.log")
TEST_RESULTS = []


def load_test_config(config_file: str) -> Dict:
    """
    Load test configuration from JSON file.

    Args:
        config_file: Path to the test configuration JSON file

    Returns:
        Dictionary containing test configuration
    """
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        LOGGER.info(f"Loaded test configuration from {config_file}")
        return config
    except Exception as e:
        LOGGER.error(f"Failed to load test configuration: {str(e)}")
        return {}


def create_test_sequence_file(sequence: str, seq_type: str, temp_dir: Path) -> Path:
    """
    Create a temporary FASTA file with the test sequence.

    Args:
        sequence: The test sequence
        seq_type: Type of sequence (nucl or prot)
        temp_dir: Directory to create the file in

    Returns:
        Path to the created file
    """
    filename = (
        temp_dir / f"test_{seq_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fasta"
    )

    with open(filename, "w") as f:
        f.write(f">test_{seq_type}_sequence\n")
        f.write(f"{sequence}\n")

    LOGGER.info(f"Created test sequence file: {filename}")
    return filename


def run_blast_search(
    query_file: Path, database_path: Path, blast_program: str
) -> Tuple[bool, str, str]:
    """
    Run a BLAST search against a database.

    Args:
        query_file: Path to the query sequence file
        database_path: Path to the BLAST database
        blast_program: BLAST program to use (blastn, blastp, etc.)

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Construct BLAST command
        blast_cmd = [
            blast_program,
            "-query",
            str(query_file),
            "-db",
            str(database_path),
            "-outfmt",
            "6",
            "-max_target_seqs",
            "5",
            "-evalue",
            "1e-5",
        ]

        LOGGER.info(f"Running BLAST command: {' '.join(blast_cmd)}")

        # Execute BLAST search
        process = Popen(blast_cmd, stdout=PIPE, stderr=PIPE, text=True)
        stdout, stderr = process.communicate()

        success = process.returncode == 0

        if success:
            LOGGER.info("BLAST search completed successfully")
            if stdout.strip():
                LOGGER.info(
                    f"BLAST results: {len(stdout.strip().split(chr(10)))} hits found"
                )
            else:
                LOGGER.info("BLAST search completed but no hits found")
        else:
            LOGGER.error(f"BLAST search failed: {stderr}")

        return success, stdout, stderr

    except Exception as e:
        LOGGER.error(f"Error running BLAST search: {str(e)}")
        return False, "", str(e)


def test_database(database_path: Path, mod_code: str, test_sequences: Dict) -> Dict:
    """
    Test a single BLAST database.

    Args:
        database_path: Path to the BLAST database
        mod_code: MOD code
        test_sequences: Dictionary containing test sequences

    Returns:
        Dictionary containing test results
    """
    result = {
        "database": str(database_path),
        "mod": mod_code,
        "tests": {},
        "overall_success": True,
        "timestamp": datetime.now().isoformat(),
    }

    # Create temporary directory for test files
    temp_dir = Path("../temp_test_files")
    temp_dir.mkdir(exist_ok=True)

    try:
        # Determine database type from database files
        db_files = list(database_path.parent.glob(f"{database_path.name}.*"))

        # Check if it's a nucleotide or protein database
        is_protein = any(f.suffix in [".pin", ".phr", ".psq"] for f in db_files)
        is_nucleotide = any(f.suffix in [".nin", ".nhr", ".nsq"] for f in db_files)

        if not is_protein and not is_nucleotide:
            result["overall_success"] = False
            result["error"] = "Cannot determine database type"
            return result

        # Get test sequences for this MOD
        mod_sequences = test_sequences.get(
            mod_code, DEFAULT_TEST_SEQUENCES.get(mod_code, {})
        )

        # Test nucleotide database
        if is_nucleotide and "nucl" in mod_sequences:
            nucl_query = create_test_sequence_file(
                mod_sequences["nucl"], "nucl", temp_dir
            )
            success, stdout, stderr = run_blast_search(
                nucl_query, database_path, "blastn"
            )

            result["tests"]["nucleotide"] = {
                "success": success,
                "hits_found": len(stdout.strip().split("\n")) if stdout.strip() else 0,
                "error": stderr if not success else None,
            }

            if not success:
                result["overall_success"] = False

            # Clean up
            nucl_query.unlink()

        # Test protein database
        if is_protein and "prot" in mod_sequences:
            prot_query = create_test_sequence_file(
                mod_sequences["prot"], "prot", temp_dir
            )
            success, stdout, stderr = run_blast_search(
                prot_query, database_path, "blastp"
            )

            result["tests"]["protein"] = {
                "success": success,
                "hits_found": len(stdout.strip().split("\n")) if stdout.strip() else 0,
                "error": stderr if not success else None,
            }

            if not success:
                result["overall_success"] = False

            # Clean up
            prot_query.unlink()

    except Exception as e:
        LOGGER.error(f"Error testing database {database_path}: {str(e)}")
        result["overall_success"] = False
        result["error"] = str(e)

    finally:
        # Clean up temp directory if empty
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except:
            pass

    return result


def find_blast_databases(
    data_dir: Path, mod_code: str = None, environment: str = None
) -> List[Path]:
    """
    Find all BLAST databases in the data directory.

    Args:
        data_dir: Root data directory
        mod_code: Optional MOD code to filter databases
        environment: Optional environment to filter databases

    Returns:
        List of database paths
    """
    databases = []

    # Look for databases in the expected structure
    blast_dir = data_dir / "blast"

    if not blast_dir.exists():
        LOGGER.warning(f"BLAST directory not found: {blast_dir}")
        return databases

    # Search pattern: data/blast/{mod}/{env}/databases/...
    search_pattern = blast_dir

    if mod_code:
        search_pattern = search_pattern / mod_code
    else:
        search_pattern = search_pattern / "*"

    if environment:
        search_pattern = search_pattern / environment
    else:
        search_pattern = search_pattern / "*"

    search_pattern = search_pattern / "databases"

    # Find all .nin, .pin files (database index files)
    for db_file in search_pattern.glob("**/*.nin"):
        databases.append(db_file.with_suffix(""))

    for db_file in search_pattern.glob("**/*.pin"):
        databases.append(db_file.with_suffix(""))

    # Remove duplicates
    databases = list(set(databases))

    LOGGER.info(f"Found {len(databases)} BLAST databases")
    return databases


def generate_test_report(results: List[Dict], output_file: Path = None) -> None:
    """
    Generate a test report from the results.

    Args:
        results: List of test results
        output_file: Optional output file path
    """
    report_lines = []

    # Header
    report_lines.append("# BLAST Database Test Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total databases tested: {len(results)}")
    report_lines.append("")

    # Summary
    successful = sum(1 for r in results if r["overall_success"])
    failed = len(results) - successful

    report_lines.append("## Summary")
    report_lines.append(f"- **Successful**: {successful}")
    report_lines.append(f"- **Failed**: {failed}")
    report_lines.append(f"- **Success Rate**: {(successful/len(results)*100):.1f}%")
    report_lines.append("")

    # Results by MOD
    mod_results = {}
    for result in results:
        mod = result["mod"]
        if mod not in mod_results:
            mod_results[mod] = {"success": 0, "failed": 0}

        if result["overall_success"]:
            mod_results[mod]["success"] += 1
        else:
            mod_results[mod]["failed"] += 1

    report_lines.append("## Results by MOD")
    for mod, counts in sorted(mod_results.items()):
        total = counts["success"] + counts["failed"]
        success_rate = (counts["success"] / total * 100) if total > 0 else 0
        report_lines.append(
            f"- **{mod}**: {counts['success']}/{total} ({success_rate:.1f}%)"
        )

    report_lines.append("")

    # Detailed results
    report_lines.append("## Detailed Results")

    for result in results:
        status = "✅ PASS" if result["overall_success"] else "❌ FAIL"
        report_lines.append(
            f"### {status} {result['mod']} - {Path(result['database']).name}"
        )
        report_lines.append(f"**Database**: `{result['database']}`")

        if "tests" in result:
            for test_type, test_result in result["tests"].items():
                test_status = "✅" if test_result["success"] else "❌"
                report_lines.append(
                    f"- **{test_type.title()}**: {test_status} ({test_result['hits_found']} hits)"
                )
                if test_result.get("error"):
                    report_lines.append(f"  - Error: {test_result['error']}")

        if "error" in result:
            report_lines.append(f"**Error**: {result['error']}")

        report_lines.append("")

    # Write report
    report_content = "\n".join(report_lines)

    if output_file:
        with open(output_file, "w") as f:
            f.write(report_content)
        print_status(f"Test report saved to {output_file}", "success")
    else:
        print(report_content)


@click.command()
@click.option(
    "-d",
    "--data-dir",
    help="Data directory containing BLAST databases",
    default="../data",
)
@click.option("-m", "--mod", help="MOD code to test (e.g., SGD, FB, WB)")
@click.option(
    "-e", "--environment", help="Environment to test (e.g., dev, stage, prod)"
)
@click.option(
    "-c", "--config", help="Test configuration file", default="../tests/UI/config.json"
)
@click.option("-o", "--output", help="Output file for test report")
@click.option("-v", "--verbose", help="Verbose output", is_flag=True)
def test_databases(
    data_dir: str, mod: str, environment: str, config: str, output: str, verbose: bool
) -> None:
    """
    Test BLAST databases created by the AGR BLAST database manager.

    This script validates that BLAST databases are properly created and functional
    by running test searches against them using known sequences.
    """
    start_time = datetime.now()

    print_header("BLAST Database Testing")
    LOGGER.info("Starting BLAST database testing")

    # Load test configuration
    test_config = {}
    if Path(config).exists():
        test_config = load_test_config(config)
        print_status(f"Loaded test configuration from {config}", "success")
    else:
        print_status(f"Test config file not found: {config}, using defaults", "warning")

    # Find databases to test
    data_path = Path(data_dir)
    databases = find_blast_databases(data_path, mod, environment)

    if not databases:
        print_status("No BLAST databases found", "error")
        sys.exit(1)

    print_status(f"Found {len(databases)} databases to test", "info")

    # Test databases
    results = []

    with create_progress() as progress:
        task = progress.add_task("Testing databases...", total=len(databases))

        for db_path in databases:
            # Extract MOD code from path
            path_parts = db_path.parts
            mod_code = None

            # Look for MOD code in path (data/blast/MOD/env/...)
            for i, part in enumerate(path_parts):
                if part == "blast" and i + 1 < len(path_parts):
                    mod_code = path_parts[i + 1]
                    break

            if not mod_code:
                LOGGER.warning(f"Cannot determine MOD code for database: {db_path}")
                continue

            progress.update(task, description=f"Testing {mod_code} - {db_path.name}")

            # Get test sequences
            test_sequences = test_config.get(mod_code, {})

            # Test the database
            result = test_database(db_path, mod_code, test_sequences)
            results.append(result)

            # Update progress
            status = "✅" if result["overall_success"] else "❌"
            if verbose:
                print_status(
                    f"{status} {mod_code} - {db_path.name}",
                    "success" if result["overall_success"] else "error",
                )

            progress.advance(task)

    # Generate summary
    duration = datetime.now() - start_time
    successful = sum(1 for r in results if r["overall_success"])
    failed = len(results) - successful

    summary_data = {
        "Total Databases": len(results),
        "Successful": successful,
        "Failed": failed,
        "Success Rate": f"{(successful/len(results)*100):.1f}%" if results else "0%",
    }

    show_summary("Database Testing", summary_data, duration)

    # Generate detailed report
    if output:
        generate_test_report(results, Path(output))
    else:
        generate_test_report(results)

    # Log completion
    LOGGER.info(f"Database testing completed in {duration}")

    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    test_databases()
