# Implementation Guide: Validation Visual Testing and Logging Enhancements

**Reference:** PRD v1.0 - Enhanced Visual Testing and Logging
**Audience:** Engineering team
**Last Updated:** January 2025

---

## Quick Start

This guide provides practical implementation instructions for the validation enhancement PRD. It translates functional requirements into actionable development tasks.

---

## Phase 1: Core Reporting (Weeks 1-2)

### Week 1: HTML Report Generation

#### Task 1.1: Create ValidationReporter Class

**File:** `src/validation_reporter.py` (new)

```python
#!/usr/bin/env python3
"""
Validation Reporter - Generate HTML and JSON reports from validation results.

Authors: [Team]
Date: January 2025
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json


class ValidationReporter:
    """Generate comprehensive reports from validation results."""

    def __init__(self,
                 output_dir: str = "../reports",
                 log_dir: str = "../logs/validation",
                 archive_dir: str = "../data/validation_archives"):
        """
        Initialize reporter with output directories.

        Args:
            output_dir: Directory for HTML reports
            log_dir: Directory for validation logs
            archive_dir: Directory for archived reports
        """
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.archive_dir = Path(archive_dir)

        # Create directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir.mkdir(exist_ok=True, parents=True)

    def generate_html_report(self,
                            validation_results: Dict[str, Dict],
                            mod: str,
                            release: str = "current",
                            output_file: Optional[str] = None) -> str:
        """
        Generate HTML report from validation results.

        Args:
            validation_results: Dict mapping MODs to validation stats
            mod: MOD identifier
            release: Release identifier
            output_file: Optional custom output filename

        Returns:
            Path to generated HTML report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_report_{mod}_{release}_{timestamp}.html"

        report_path = self.output_dir / output_file

        # Generate HTML content
        html_content = self._generate_html_content(validation_results, mod, release)

        # Write to file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(report_path)

    def _generate_html_content(self,
                               results: Dict[str, Dict],
                               mod: str,
                               release: str) -> str:
        """Generate HTML content for validation report."""

        # Extract statistics
        mod_stats = results.get(mod, {})
        total_passed = mod_stats.get('passed', 0)
        total_failed = mod_stats.get('failed', 0)
        total_dbs = total_passed + total_failed
        success_rate = (total_passed / max(1, total_dbs)) * 100
        total_hits = mod_stats.get('total_hits', 0)
        duration = mod_stats.get('duration', None)

        # Get individual database results
        db_results = mod_stats.get('results', [])
        passed_dbs = [r for r in db_results if r.success]
        failed_dbs = [r for r in db_results if not r.success]

        # Generate timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Validation Report - {mod} {release}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .stat-card.success {{ border-left-color: #28a745; }}
        .stat-card.warning {{ border-left-color: #ffc107; }}
        .stat-card.error {{ border-left-color: #dc3545; }}
        .stat-value {{
            font-size: 3em;
            font-weight: bold;
            color: #333;
            margin: 0;
        }}
        .stat-label {{
            color: #666;
            margin-top: 10px;
            font-size: 1.1em;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 8px;
            height: 30px;
            margin: 20px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #28a745, #20c997);
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .database-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .db-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ccc;
        }}
        .db-card.passed {{ border-left-color: #28a745; }}
        .db-card.failed {{ border-left-color: #dc3545; }}
        .db-name {{
            font-weight: bold;
            font-size: 1.2em;
            margin-bottom: 12px;
            color: #333;
        }}
        .db-stats {{
            font-size: 0.95em;
            color: #666;
            line-height: 1.6;
        }}
        .db-stats strong {{
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background-color: #f1f3f5;
            font-weight: 600;
            color: #495057;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .status-passed {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-failed {{
            color: #dc3545;
            font-weight: bold;
        }}
        .timestamp {{
            text-align: center;
            color: #888;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Database Validation Report</h1>
            <p><strong>{mod}</strong> - {release}</p>
            <p>Generated on {timestamp}</p>
        </div>

        <div class="summary">
            <div class="stat-card success">
                <div class="stat-value">{total_passed}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card error">
                <div class="stat-value">{total_failed}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_dbs}</div>
                <div class="stat-label">Total Databases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>

        <div class="section">
            <h2>Overview</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%;">
                    {success_rate:.1f}%
                </div>
            </div>
            <p><strong>Total Hits:</strong> {total_hits:,}</p>
"""

        if duration:
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            html += f"            <p><strong>Duration:</strong> {duration_str}</p>\n"

        html += "        </div>\n\n"

        # Failed databases section
        if failed_dbs:
            html += f"""        <div class="section">
            <h2>Failed Databases ({len(failed_dbs)})</h2>
            <div class="database-grid">
"""
            for result in failed_dbs:
                html += f"""                <div class="db-card failed">
                    <div class="db-name">{result.db_name}</div>
                    <div class="db-stats">
                        <strong>Total Hits:</strong> {result.total_hits}<br>
                        <strong>Tests Run:</strong> {result.test_count}<br>
                        <strong>Hit Rate:</strong> {result.get_hit_rate():.1f}%<br>
                        <strong>BLAST Type:</strong> {result.blast_type}
"""
                if result.error_message:
                    html += f"                        <br><strong>Error:</strong> {result.error_message}\n"
                html += "                    </div>\n                </div>\n"

            html += "            </div>\n        </div>\n\n"

        # Passed databases section
        if passed_dbs:
            html += f"""        <div class="section">
            <h2>Successful Databases ({len(passed_dbs)})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Database</th>
                        <th>Total Hits</th>
                        <th>Conserved Hits</th>
                        <th>Specific Hits</th>
                        <th>Hit Rate</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
            for result in passed_dbs:
                html += f"""                    <tr>
                        <td>{result.db_name}</td>
                        <td>{result.total_hits}</td>
                        <td>{result.conserved_hits}</td>
                        <td>{result.specific_hits}</td>
                        <td>{result.get_hit_rate():.1f}%</td>
                        <td class="status-passed">PASSED</td>
                    </tr>
"""
            html += """                </tbody>
            </table>
        </div>
"""

        # Footer
        html += f"""
        <div class="timestamp">
            <p><em>Report generated by AGR BLAST Database Manager</em></p>
        </div>
    </div>
</body>
</html>
"""

        return html
```

**Testing:**
```python
# tests/unit/test_validation_reporter.py

def test_html_report_generation(mock_validation_results):
    """Test HTML report generation."""
    reporter = ValidationReporter(output_dir="test_reports")

    html_path = reporter.generate_html_report(
        mock_validation_results,
        "FB",
        "2025_01"
    )

    assert Path(html_path).exists()
    assert "validation_report_FB_2025_01" in html_path

    # Verify HTML structure
    with open(html_path) as f:
        html = f.read()
        assert "<!DOCTYPE html>" in html
        assert "Database Validation Report" in html
        assert "FB" in html
```

---

#### Task 1.2: Integrate Reporter with Validation

**File:** `src/validation.py` (modifications)

```python
# Add at top of file
try:
    from validation_reporter import ValidationReporter
    REPORTER_AVAILABLE = True
except ImportError:
    REPORTER_AVAILABLE = False
    log_warning("ValidationReporter not available - HTML/JSON reporting disabled")


# Modify DatabaseValidator.__init__()
class DatabaseValidator:
    def __init__(
        self,
        logger,
        evalue: str = "10",
        word_size: str = "7",
        timeout: int = 30,
        num_threads: int = 2,
        enable_html: bool = False,           # NEW
        enable_json: bool = False,           # NEW
        output_dir: str = "../reports"       # NEW
    ):
        """Initialize the validator with optional reporting."""
        self.logger = logger
        self.evalue = evalue
        self.word_size = word_size
        self.timeout = timeout
        self.num_threads = num_threads

        # NEW: Setup reporter if requested
        self.enable_html = enable_html
        self.enable_json = enable_json
        if (enable_html or enable_json) and REPORTER_AVAILABLE:
            self.reporter = ValidationReporter(output_dir=output_dir)
            self.logger.info("ValidationReporter enabled")
        else:
            self.reporter = None

        self.logger.info("DatabaseValidator initialized")


    # Modify validate_all() to generate reports
    def validate_all(
        self, base_path: str, mod_filter: Optional[str] = None
    ) -> Dict[str, Dict]:
        """Validate all databases with optional reporting."""

        # ... existing validation logic ...

        # NEW: Generate reports if enabled
        if self.reporter:
            try:
                if self.enable_html:
                    html_path = self.reporter.generate_html_report(
                        all_results,
                        mod_filter or "all",
                        "current"
                    )
                    log_success(f"HTML report: {html_path}")

                if self.enable_json:
                    json_path = self.reporter.generate_json_export(
                        all_results,
                        mod_filter or "all",
                        "current"
                    )
                    log_success(f"JSON export: {json_path}")
            except Exception as e:
                log_error(f"Report generation failed: {str(e)}")
                # Don't fail validation if reporting fails

        return all_results
```

---

#### Task 1.3: Update Main Pipeline

**File:** `src/create_blast_db.py` (modifications)

```python
@click.option(
    "--validate",
    is_flag=True,
    default=False,
    help="Validate databases after creation using BLAST tests"
)
@click.option(
    "--html-report",                       # NEW
    is_flag=True,
    default=False,
    help="Generate HTML validation report (requires --validate)"
)
@click.option(
    "--json-export",                       # NEW
    is_flag=True,
    default=False,
    help="Export validation results to JSON (requires --validate)"
)
def main(
    config_yaml,
    input_json,
    environment,
    mod,
    skip_efs_sync,
    update_slack,
    sync_s3,
    skip_local_storage,
    copy_to_sequenceserver,
    validate,
    html_report,                           # NEW
    json_export                            # NEW
):
    """Main pipeline execution."""

    # ... existing code ...

    # Validation with reporting
    if validate and not check_parse_seqids:
        print_header("Post-Creation Database Validation")

        validator = DatabaseValidator(
            logger,
            enable_html=html_report,       # NEW
            enable_json=json_export        # NEW
        )

        # ... rest of validation code ...
```

---

### Week 2: JSON Export and Enhanced Logging

#### Task 2.1: Add JSON Export

**Add to ValidationReporter:**

```python
def generate_json_export(self,
                        validation_results: Dict[str, Dict],
                        mod: str,
                        release: str = "current") -> str:
    """
    Export validation results to JSON.

    Args:
        validation_results: Dict mapping MODs to validation stats
        mod: MOD identifier
        release: Release identifier

    Returns:
        Path to generated JSON file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"validation_results_{mod}_{release}_{timestamp}.json"
    json_path = self.output_dir / output_file

    # Build JSON structure
    mod_stats = validation_results.get(mod, {})

    json_data = {
        "schema_version": "1.0",
        "mod": mod,
        "release": release,
        "environment": "current",
        "validation_start": datetime.now().isoformat(),
        "summary": {
            "passed": mod_stats.get('passed', 0),
            "failed": mod_stats.get('failed', 0),
            "total_databases": mod_stats.get('total', 0),
            "success_rate": (mod_stats.get('passed', 0) / max(1, mod_stats.get('total', 1))) * 100,
            "total_hits": mod_stats.get('total_hits', 0),
            "databases_with_conserved": mod_stats.get('databases_with_conserved', 0),
            "databases_with_specific": mod_stats.get('databases_with_specific', 0)
        },
        "databases": []
    }

    # Add individual database results
    for result in mod_stats.get('results', []):
        db_data = {
            "database_name": result.db_name,
            "database_path": result.db_path,
            "blast_type": result.blast_type,
            "overall_status": "PASSED" if result.success else "FAILED",
            "conserved_hits": result.conserved_hits,
            "specific_hits": result.specific_hits,
            "total_hits": result.total_hits,
            "test_count": result.test_count,
            "hit_rate": result.get_hit_rate(),
            "hit_details": result.hit_details
        }

        if result.error_message:
            db_data["error_message"] = result.error_message

        json_data["databases"].append(db_data)

    # Write JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)

    return str(json_path)
```

---

#### Task 2.2: Enhanced Logging

**Add to ValidationReporter:**

```python
import logging
from logging.handlers import RotatingFileHandler


def setup_validation_logger(self,
                           mod: str,
                           environment: str) -> logging.Logger:
    """
    Create dedicated validation logger with file and console handlers.

    Args:
        mod: MOD identifier
        environment: Environment name

    Returns:
        Configured logger instance
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = self.log_dir / f"database_validation_{mod}_{environment}_{timestamp}.log"

    # Create logger
    logger = logging.getLogger(f"validation_{mod}_{environment}")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    logger.handlers = []

    # File handler (DEBUG level, everything)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (INFO level, less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"Validation logging initialized for {mod}/{environment}")
    logger.info(f"Log file: {log_file}")

    return logger
```

---

## Phase 2: Standalone CLI (Week 3)

### Task 3.1: Create Standalone Validation Script

**File:** `src/validate_release.py` (new)

```python
#!/usr/bin/env python3
"""
Standalone database validation tool for AGR BLAST databases.

Usage:
    python validate_release.py --mod FB --env prod --html --json
"""

import sys
import click
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from validation import DatabaseValidator
from validation_reporter import ValidationReporter
from utils import setup_detailed_logger


@click.command()
@click.option('--mod', '-m', required=True,
              type=click.Choice(['FB', 'SGD', 'WB', 'ZFIN', 'RGD', 'XB']),
              help='MOD to validate')
@click.option('--env', '-e', default='prod',
              help='Environment (dev/stage/prod)')
@click.option('--db-path',
              help='Custom database path (overrides default)')
@click.option('--html', is_flag=True,
              help='Generate HTML report')
@click.option('--json', is_flag=True,
              help='Generate JSON export')
@click.option('--evalue', default='10',
              help='BLAST e-value threshold (default: 10)')
@click.option('--word-size', default='7',
              help='BLAST word size (default: 7)')
@click.option('--timeout', default=30, type=int,
              help='BLAST timeout in seconds (default: 30)')
@click.option('--output-dir', default='../reports',
              help='Output directory for reports')
def validate(mod, env, db_path, html, json, evalue, word_size, timeout, output_dir):
    """
    Validate BLAST databases for a specific MOD.

    Examples:
        python validate_release.py --mod FB --html
        python validate_release.py --mod SGD --env dev --json
        python validate_release.py --mod WB --html --json
    """

    # Setup logging
    logger_name = f"validate_{mod}_{env}"
    logger = setup_detailed_logger(logger_name, f"validation_{mod}_{env}.log")

    # Determine database path
    if not db_path:
        db_path = f"../data/blast/{mod}/{env}/databases"

    logger.info(f"Starting standalone validation for {mod}")
    logger.info(f"Environment: {env}")
    logger.info(f"Database path: {db_path}")
    logger.info(f"E-value: {evalue}, Word size: {word_size}, Timeout: {timeout}s")

    # Check if path exists
    if not Path(db_path).exists():
        logger.error(f"Database path does not exist: {db_path}")
        click.echo(f"ERROR: Database path not found: {db_path}", err=True)
        return 2

    # Create validator
    validator = DatabaseValidator(
        logger=logger,
        evalue=evalue,
        word_size=word_size,
        timeout=timeout,
        enable_html=html,
        enable_json=json,
        output_dir=output_dir
    )

    # Run validation
    click.echo(f"\nValidating {mod} databases in {env} environment...")
    results = validator.validate_all(db_path, mod_filter=mod)

    # Check results
    if not results:
        logger.error("No databases found for validation")
        click.echo("ERROR: No databases found", err=True)
        return 2

    # Calculate summary
    total_failed = sum(r['failed'] for r in results.values())
    total_passed = sum(r['passed'] for r in results.values())
    total_dbs = total_failed + total_passed

    # Exit code
    if total_failed > 0:
        logger.warning(f"Validation complete with {total_failed}/{total_dbs} failures")
        click.echo(f"\n⚠  WARNING: {total_failed} database(s) failed validation", err=True)
        return 1
    else:
        logger.info(f"All {total_passed} databases validated successfully")
        click.echo(f"\n✓ SUCCESS: All {total_passed} databases passed validation")
        return 0


if __name__ == '__main__':
    sys.exit(validate())
```

**Make executable:**
```bash
chmod +x src/validate_release.py
```

---

### Task 3.2: Create Test Fixtures

**Create directory structure:**
```bash
mkdir -p tests/fixtures
```

**File:** `tests/fixtures/universal_conserved.fasta`
```fasta
# Copy sequences from validation.py CONSERVED_SEQUENCES
```

**File:** `tests/fixtures/fb_specific.fasta`
```fasta
# Copy FB sequences from validation.py MOD_SPECIFIC_SEQUENCES
```

**File:** `tests/fixtures/README.md`
```markdown
# Test Fixtures for Database Validation

This directory contains test sequences used for BLAST database validation.

## File Organization

- `universal_conserved.fasta` - 8 conserved sequences found across all eukaryotes
- `{mod}_specific.fasta` - MOD-specific test sequences (2+ per MOD)

## Adding New Sequences

1. Create/edit appropriate FASTA file
2. Use standard FASTA format with descriptive headers
3. Ensure sequence length >100bp for reliable BLAST hits
4. Test with actual databases before committing

## Sequence Sources

- Conserved sequences from UniProt highly conserved regions
- MOD-specific sequences from authoritative genome annotations
```

---

## Testing Checklist

### Unit Tests
- [ ] ValidationReporter.generate_html_report()
- [ ] ValidationReporter.generate_json_export()
- [ ] ValidationReporter.setup_validation_logger()
- [ ] HTML report structure and CSS
- [ ] JSON schema validation
- [ ] Fixture loader with fallback

### Integration Tests
- [ ] Full validation with HTML report
- [ ] Full validation with JSON export
- [ ] Standalone CLI with all flags
- [ ] Pipeline integration (--validate --html --json)
- [ ] Report file permissions and locations

### Performance Tests
- [ ] HTML generation overhead (<10s)
- [ ] JSON generation overhead (<5s)
- [ ] Logging overhead (<2s)
- [ ] Report with 50+ databases

---

## Documentation Tasks

- [ ] Update README.md with new CLI flags
- [ ] Add validation reporting examples
- [ ] Document HTML report structure
- [ ] Document JSON schema
- [ ] Update CLAUDE.md with new features
- [ ] Create user guide for QA team

---

## Deployment Checklist

- [ ] Create `reports/` directory on servers
- [ ] Create `logs/validation/` directory
- [ ] Set up log rotation policy
- [ ] Configure S3 bucket for archives (if needed)
- [ ] Test with development environment
- [ ] Test with production environment (single MOD)
- [ ] Rollout to all MODs

---

## Example Commands

```bash
# Integrated validation with reports
uv run python src/create_blast_db.py -m FB -e prod \\
    --validate --html-report --json-export

# Standalone validation
uv run python src/validate_release.py --mod FB --html --json

# Standalone with custom parameters
uv run python src/validate_release.py --mod SGD \\
    --evalue 0.001 --word-size 11 --html

# Validation with custom database path
uv run python src/validate_release.py --mod WB \\
    --db-path /custom/path --html --json
```

---

## Success Criteria

✅ **Phase 1 Complete When:**
- HTML reports generated successfully
- JSON exports validated against schema
- Enhanced logging capturing all operations
- Integration tests passing
- Documentation updated

✅ **Phase 2 Complete When:**
- Standalone CLI tool working
- QA team can run validations independently
- Test fixtures loaded correctly
- All CLI flags functional

✅ **Phase 3 Complete When:**
- Enhanced validation layers operational
- Dashboard generation working
- Performance benchmarks met
- Full documentation complete

---

**Questions?** Contact engineering lead or refer to main PRD.
