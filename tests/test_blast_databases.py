#!/usr/bin/env python3
"""
BLAST Database Testing Script
Auto-discovers and tests all MOD databases with concise reporting
"""

import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple


def get_blast_version() -> str:
    """Get BLAST version."""
    try:
        result = subprocess.run(['blastn', '-version'], capture_output=True, text=True)
        return result.stdout.split('\n')[0]
    except Exception:
        return "Unknown"


def test_database(db_path: Path, db_type: str, mod: str, env: str) -> Tuple[bool, str]:
    """
    Test a single BLAST database.

    Returns:
        (success: bool, error_message: str)
    """
    # Check if database is readable
    try:
        result = subprocess.run(
            ['blastdbcmd', '-db', str(db_path), '-info'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, "Database not readable"
    except Exception as e:
        return False, f"Database check failed: {str(e)}"

    # Run BLAST query
    test_dir = Path(__file__).parent / "blast_test_results"
    query_file = test_dir / f"test_{'nucl' if db_type == 'nucl' else 'prot'}.fasta"

    blast_cmd = 'blastn' if db_type == 'nucl' else 'blastp'

    try:
        result = subprocess.run(
            [blast_cmd, '-query', str(query_file), '-db', str(db_path),
             '-max_target_seqs', '1', '-outfmt', '7'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return False, f"{blast_cmd} query failed"
    except subprocess.TimeoutExpired:
        return False, f"{blast_cmd} query timed out"
    except Exception as e:
        return False, f"{blast_cmd} query error: {str(e)}"

    return True, ""


def discover_databases(base_dir: Path) -> Dict[str, Dict[str, List[Tuple[Path, str]]]]:
    """
    Discover all databases in the base directory.

    Returns:
        {MOD: {environment: [(db_path, db_type), ...]}}
    """
    databases = defaultdict(lambda: defaultdict(list))

    if not base_dir.exists():
        return databases

    for mod_dir in sorted(base_dir.iterdir()):
        if not mod_dir.is_dir():
            continue

        mod = mod_dir.name

        for env_dir in sorted(mod_dir.iterdir()):
            if not env_dir.is_dir():
                continue

            env = env_dir.name
            db_dir = env_dir / "databases"

            if not db_dir.exists():
                continue

            # Find nucleotide databases
            for nhr_file in db_dir.rglob("*.nhr"):
                db_path = nhr_file.with_suffix('')
                databases[mod][env].append((db_path, 'nucl'))

            # Find protein databases
            for phr_file in db_dir.rglob("*.phr"):
                db_path = phr_file.with_suffix('')
                databases[mod][env].append((db_path, 'prot'))

    return databases


def create_test_sequences(output_dir: Path):
    """Create test query sequences."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Nucleotide test sequence
    (output_dir / "test_nucl.fasta").write_text(
        ">test_nucleotide_query\n"
        "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC\n"
    )

    # Protein test sequence
    (output_dir / "test_prot.fasta").write_text(
        ">test_protein_query\n"
        "MKLLIVDDSSGKVRAEIKQLLKQGVNPE\n"
    )


def generate_report(databases: Dict, results: Dict, output_file: Path):
    """Generate concise markdown report."""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    blast_version = get_blast_version()

    # Calculate statistics
    total_tests = sum(len(results[mod][env]) for mod in results for env in results[mod])
    failed_tests = sum(
        1 for mod in results for env in results[mod]
        for success, _ in results[mod][env].values() if not success
    )
    successful_tests = total_tests - failed_tests
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

    # MOD statistics
    mod_stats = {}
    for mod in results:
        tested = sum(len(results[mod][env]) for env in results[mod])
        failed = sum(
            1 for env in results[mod]
            for success, _ in results[mod][env].values() if not success
        )
        mod_stats[mod] = (tested, failed)

    # Start report
    lines = [
        "# BLAST Database Test Report\n",
        f"**Generated:** {timestamp}  ",
        f"**BLAST Version:** {blast_version}\n",
        "---\n",
        "## Summary\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Total Databases** | {total_tests} |",
        f"| **Passed** | {successful_tests} |",
        f"| **Failed** | {failed_tests} |",
        f"| **Success Rate** | {success_rate:.1f}% |\n",
        "## MOD Breakdown\n",
        "| MOD | Environments | Tested | Failed | Status |",
        "|-----|-------------|--------|--------|--------|",
    ]

    # Add MOD stats
    for mod in sorted(mod_stats.keys()):
        tested, failed = mod_stats[mod]
        envs = sorted(results[mod].keys())
        env_str = ", ".join(envs)
        status = "✓ PASS" if failed == 0 else f"✗ FAIL ({failed})"
        lines.append(f"| {mod} | {env_str} | {tested} | {failed} | {status} |")

    # Add failures section if any
    if failed_tests > 0:
        lines.extend(["\n---\n", "## Failures\n"])
        for mod in sorted(results.keys()):
            for env in sorted(results[mod].keys()):
                for db_path, (success, error) in results[mod][env].items():
                    if not success:
                        db_name = db_path.name
                        db_type = "nucl" if any(db_path.with_suffix(s).exists()
                                               for s in ['.nhr']) else "prot"
                        lines.extend([
                            f"**✗ {mod} / {env} - {db_name} ({db_type})**  ",
                            f"- Error: {error}  ",
                            f"- Path: `{db_path}`\n"
                        ])
    else:
        lines.extend(["\n---\n", "## All Tests Passed ✓\n",
                     "All databases are readable and queryable.\n"])

    # Check for missing databases
    lines.extend(["\n---\n", "## Expected Databases\n"])
    if not databases:
        lines.append("⚠️ No databases found in `../data/blast/`\n")
    else:
        lines.append("Databases were found and tested for all MODs present in `../data/blast/`.\n")

    # Footer
    lines.extend([
        "\n---\n",
        "## How to Run\n",
        "```bash\n",
        "cd tests\n",
        "python test_blast_databases.py\n",
        "# or\n",
        "uv run python test_blast_databases.py\n",
        "```\n",
        "*Test framework: AGR BLAST Database Manager*\n"
    ])

    output_file.write_text('\n'.join(lines))


def main():
    """Main testing function."""
    base_dir = Path(__file__).parent.parent / "data" / "blast"
    results_dir = Path(__file__).parent / "blast_test_results"
    report_file = results_dir / "TEST_REPORT.md"

    print("BLAST Database Testing")
    print("=" * 50)

    # Create test sequences
    print("Creating test sequences...")
    create_test_sequences(results_dir)

    # Discover databases
    print(f"Discovering databases in {base_dir}...")
    databases = discover_databases(base_dir)

    if not databases:
        print("⚠️  No databases found!")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            "# BLAST Database Test Report\n\n"
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## No Databases Found\n\n"
            "⚠️ No databases were found in `../data/blast/`\n"
        )
        return

    # Test all databases
    results = defaultdict(lambda: defaultdict(dict))
    total = 0
    successful = 0

    for mod in sorted(databases.keys()):
        print(f"\nTesting {mod}...")
        for env in sorted(databases[mod].keys()):
            print(f"  Environment: {env}")
            for db_path, db_type in databases[mod][env]:
                total += 1
                success, error = test_database(db_path, db_type, mod, env)
                results[mod][env][db_path] = (success, error)
                if success:
                    successful += 1
                else:
                    print(f"    ✗ {db_path.name} ({db_type}): {error}")

    # Generate report
    print(f"\nGenerating report...")
    generate_report(databases, results, report_file)

    print("\n" + "=" * 50)
    print("Testing Complete!")
    print("=" * 50)
    print(f"Total:      {total}")
    print(f"Passed:     {successful}")
    print(f"Failed:     {total - successful}")
    print(f"\nReport: {report_file}")


if __name__ == "__main__":
    main()
