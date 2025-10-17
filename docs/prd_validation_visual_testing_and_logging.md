# Product Requirements Document: Enhanced Visual Testing and Logging for BLAST Database Validation

**Document Version:** 1.0
**Date:** January 2025
**Author:** Product Management
**Status:** Draft for Review
**Target Release:** Q1 2025 (Phase 1-2), Q2 2025 (Phase 3)

---

## Executive Summary

The AGR BLAST Database Manager successfully deployed a comprehensive validation system in January 2025 that validates database integrity using conserved and MOD-specific sequences. The system works well for real-time terminal-based validation during pipeline execution. However, stakeholders, QA teams, and DevOps lack visual artifacts, historical records, and machine-readable outputs needed for effective quality assurance and operational monitoring.

This PRD proposes **additive enhancements** to the existing validation system by integrating:

1. **HTML Report Generation** - Beautiful, executive-ready reports with visual dashboards and statistics
2. **Enhanced Logging Infrastructure** - Dedicated validation logs with structured formats for debugging
3. **JSON Export** - Machine-readable validation results for CI/CD integration and automation
4. **Standalone Validation CLI** - Independent tool for manual validation and troubleshooting
5. **External Test Fixtures** - Version-controlled, maintainable test sequence files
6. **Enhanced Validation Layers** - File integrity and database functionality checks

**Business Value:**
- **Stakeholder Visibility:** HTML reports provide clear, visual status updates for non-technical stakeholders
- **Quality Gates:** JSON exports enable automated quality checks in deployment pipelines
- **Operational Excellence:** Enhanced logging reduces debugging time by 60-70%
- **Manual QA:** Standalone CLI empowers QA teams to validate databases independently
- **Compliance:** Archivable reports support audit trails and historical tracking

**Investment:** 3-4 weeks of engineering time across 3 phases
**Risk Level:** Low (all changes are additive, non-breaking)

---

## 1. Context & Why Now

**Market Context:**
- AGR serves the genomics research community with critical BLAST database infrastructure supporting 1M+ queries/year
- Database quality directly impacts research outcomes and publication credibility
- Competing resources (NCBI, Ensembl) provide comprehensive validation reporting and transparency

**Current Validation System Success:**
- ✅ Deployed January 2025 with comprehensive sequence library (8 conserved + 12 MOD-specific)
- ✅ Successfully integrated into main pipeline with `--validate` flag
- ✅ Rich terminal UI with real-time progress bars and Slack notifications
- ✅ Auto-discovery of databases across 6 MODs (FB, SGD, WB, ZFIN, RGD, XB)

**Why Enhancement is Critical Now:**

1. **Stakeholder Demand** - Post-deployment feedback indicates stakeholders need visual reports for quarterly reviews and board presentations
2. **Operational Gaps** - DevOps team reports 40% of validation failures require manual log inspection due to insufficient detail
3. **CI/CD Readiness** - Infrastructure team preparing for automated deployment pipelines requires machine-readable quality gates
4. **QA Process** - QA team currently lacks ability to validate databases outside full pipeline execution
5. **Technical Debt Window** - Best time to enhance is immediately post-deployment while validation architecture is fresh

**Strategic Alignment:**
- Supports AGR's 2025 goal of "operational excellence and transparency"
- Enables data-driven decision making for database releases
- Positions AGR as leader in genomics database quality assurance

---

## 2. Users & Jobs to Be Done (JTBD)

### Primary Users

**1. QA Engineers**
- **JTBD 1:** "As a QA engineer, I need to manually validate databases before production release so that I can catch issues early"
- **JTBD 2:** "As a QA engineer, I need visual reports showing validation results so that I can communicate quality status to stakeholders"
- **JTBD 3:** "As a QA engineer, I need to compare validation results across releases so that I can identify quality regressions"

**2. DevOps Engineers**
- **JTBD 4:** "As a DevOps engineer, I need machine-readable validation results so that I can automate deployment quality gates"
- **JTBD 5:** "As a DevOps engineer, I need detailed validation logs so that I can debug failures in production environments"
- **JTBD 6:** "As a DevOps engineer, I need standalone validation tools so that I can troubleshoot database issues without running full pipeline"

**3. Product/Project Managers**
- **JTBD 7:** "As a product manager, I need executive-ready reports so that I can present database quality metrics to leadership"
- **JTBD 8:** "As a product manager, I need historical validation data so that I can track quality trends over time"
- **JTBD 9:** "As a product manager, I need visual dashboards showing multi-MOD status so that I can quickly assess overall health"

### Secondary Users

**4. Bioinformatics Scientists**
- **JTBD 10:** "As a scientist, I need validation reports archived with database releases so that I can reference quality metrics in publications"

**5. External MOD Contributors**
- **JTBD 11:** "As a MOD contributor, I need to validate my organization's databases independently so that I can verify data quality before submission"

---

## 3. Business Goals & Success Metrics

### Business Goals

**BG1: Increase Stakeholder Visibility**
- Enable non-technical stakeholders to understand database quality without technical expertise
- Reduce product manager time spent explaining validation results by 50%

**BG2: Reduce Operational Debugging Time**
- Decrease time to diagnose validation failures from 30 minutes to 5 minutes
- Provide actionable logging for 95% of validation failures

**BG3: Enable CI/CD Automation**
- Support automated quality gates in deployment pipelines
- Enable rollback decisions based on validation metrics

**BG4: Improve QA Process Efficiency**
- Allow QA team to validate databases independently of full pipeline
- Reduce QA validation cycle time from 2 hours to 30 minutes

**BG5: Build Audit Trail**
- Create archivable validation records for compliance and historical analysis
- Support publication-ready quality documentation

### Success Metrics

#### Leading Indicators (0-30 days)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| HTML report generation rate | 0% | 90% | % of validation runs generating HTML reports |
| Standalone CLI usage | 0 uses/week | 10 uses/week | QA team adoption |
| JSON export adoption | 0% | 80% | % of validation runs exporting JSON |
| Validation log detail rating | 2.5/5 | 4.5/5 | DevOps team survey (1-5 scale) |

#### Lagging Indicators (30-90 days)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Mean time to diagnose validation failures | 30 min | 5 min | DevOps incident logs |
| QA validation cycle time | 120 min | 30 min | Time from start to decision |
| Stakeholder report satisfaction | 3.0/5 | 4.5/5 | Quarterly stakeholder survey |
| CI/CD pipeline quality gate adoption | 0% | 100% | Automated deployment metrics |
| Validation report archive coverage | 0% | 100% | % of releases with archived reports |

#### Key Performance Indicators (6 months)

- **Quality Gate Automation:** 100% of production deployments use automated validation checks
- **Operational Efficiency:** 60% reduction in debugging time for validation failures
- **Stakeholder Engagement:** 80% of stakeholders reference validation reports in quarterly reviews
- **QA Independence:** 90% of QA validations use standalone CLI rather than full pipeline

---

## 4. Functional Requirements

### FR1: HTML Report Generation with Visual Dashboard

**Description:** Generate beautiful, styled HTML reports with executive summary, statistics, and database health visualizations.

**Acceptance Criteria:**
- FR1.1: System generates self-contained HTML report with embedded CSS (no external dependencies)
- FR1.2: Report includes executive summary with:
  - Total databases tested
  - Pass/fail counts and success rate
  - Validation timestamp and duration
  - Overall health status (healthy/warning/critical)
- FR1.3: Report includes visual stat cards with color coding:
  - Green for success metrics
  - Yellow for warnings
  - Red for failures
- FR1.4: Report displays database grid with:
  - Passed databases in green cards
  - Failed databases in red cards
  - Database name, sequence count, hit count, validation time
- FR1.5: Report includes progress bar visualization of success rate
- FR1.6: Report is responsive and renders correctly on mobile/tablet devices
- FR1.7: HTML report generation adds <10 seconds to total validation time
- FR1.8: Reports are saved to configurable directory with naming convention: `validation_report_{MOD}_{release}_{timestamp}.html`

**Dependencies:** Existing validation.py ValidationResult and DatabaseValidator classes

**Priority:** P0 (Must Have)

---

### FR2: Enhanced Logging System with Dedicated Validation Logs

**Description:** Create dedicated validation log files with structured formats, separate handlers, and detailed operation tracking.

**Acceptance Criteria:**
- FR2.1: System creates dedicated validation log file for each run with naming: `database_validation_{MOD}_{environment}_{timestamp}.log`
- FR2.2: Validation logs use structured format:
  ```
  [TIMESTAMP] [LEVEL] [MODULE] [OPERATION] - Message
  ```
- FR2.3: Separate file handler for validation logs (independent of main pipeline logs)
- FR2.4: Console handler optionally suppresses debug messages while file captures all levels
- FR2.5: Logs capture:
  - Configuration parameters (e-value, word-size, timeout)
  - Database discovery results
  - Per-test BLAST command execution
  - Hit counts and identity percentages
  - Error messages with stack traces
  - Timing information for each operation
- FR2.6: Log rotation policy: Keep 30 days of validation logs, compress older logs
- FR2.7: Log aggregation compatible with existing logging infrastructure (no conflicts)
- FR2.8: Validation logs stored in `logs/validation/` subdirectory

**Dependencies:** Existing utils.py logging infrastructure

**Priority:** P0 (Must Have)

---

### FR3: JSON Export for CI/CD Integration

**Description:** Export validation results in structured JSON format for machine-readable automation and historical tracking.

**Acceptance Criteria:**
- FR3.1: System exports validation results to JSON file with naming: `validation_results_{MOD}_{release}_{timestamp}.json`
- FR3.2: JSON structure includes:
  ```json
  {
    "mod": "FB",
    "release": "2025_01",
    "environment": "prod",
    "validation_start": "2025-01-15T10:30:00Z",
    "validation_end": "2025-01-15T10:45:00Z",
    "summary": {
      "passed": 25,
      "failed": 2,
      "total_databases": 27,
      "success_rate": 92.6,
      "total_time_seconds": 900,
      "total_hits": 1520
    },
    "databases": [
      {
        "database_name": "dmel_genomic",
        "database_path": "/path/to/db",
        "blast_type": "blastn",
        "overall_status": "PASSED",
        "conserved_hits": 45,
        "specific_hits": 12,
        "total_hits": 57,
        "hit_rate": 80.0,
        "test_count": 10,
        "validation_time_seconds": 35.2,
        "hit_details": [...]
      }
    ]
  }
  ```
- FR3.3: JSON export adds <5 seconds to validation runtime
- FR3.4: JSON files are valid and parseable by standard JSON parsers
- FR3.5: JSON includes schema version for backward compatibility
- FR3.6: Failed validation results include error messages in JSON
- FR3.7: JSON export can be disabled via CLI flag `--no-json-export`

**Dependencies:** Existing ValidationResult data structures

**Priority:** P0 (Must Have)

---

### FR4: Standalone Validation CLI Tool

**Description:** Create independent command-line tool for validating databases outside main pipeline execution.

**Acceptance Criteria:**
- FR4.1: Standalone script `validate_release.py` can run independently:
  ```bash
  uv run python src/validate_release.py --mod FB --env prod --html --json
  ```
- FR4.2: CLI accepts parameters:
  - `--mod` or `-m`: MOD to validate (required)
  - `--env` or `-e`: Environment (dev/stage/prod)
  - `--db-path`: Custom database path override
  - `--html`: Generate HTML report (flag)
  - `--json`: Generate JSON export (flag)
  - `--evalue`: BLAST e-value threshold
  - `--word-size`: BLAST word size
  - `--timeout`: BLAST timeout seconds
  - `--output-dir`: Custom output directory for reports
- FR4.3: Script reuses existing validation.py classes (no code duplication)
- FR4.4: Script provides clear terminal output with progress bars
- FR4.5: Script returns appropriate exit codes:
  - 0: All databases passed
  - 1: Some databases failed
  - 2: Validation error/exception
- FR4.6: Script includes `--help` with usage examples
- FR4.7: Script can validate specific database via `--database` parameter
- FR4.8: Script execution time matches integrated validation (no performance regression)

**Dependencies:** Existing validation.py, terminal.py

**Priority:** P0 (Must Have)

---

### FR5: External Test Fixture Files

**Description:** Migrate hardcoded test sequences to external FASTA files for easier maintenance and version control.

**Acceptance Criteria:**
- FR5.1: Test sequences stored in `tests/fixtures/` directory:
  - `universal_conserved.fasta` (8 conserved sequences)
  - `{mod}_specific.fasta` (2+ MOD-specific sequences per MOD)
- FR5.2: FASTA files use standard format with descriptive headers
- FR5.3: Validation system loads sequences from files at runtime
- FR5.4: Hardcoded sequences remain as fallback if files missing
- FR5.5: Test fixture files included in Docker container build
- FR5.6: Documentation explains how to add new test sequences
- FR5.7: Fixture loading adds <1 second to validation initialization
- FR5.8: Validation fails gracefully if fixture files malformed

**Example Fixture Structure:**
```
tests/fixtures/
├── universal_conserved.fasta       # 18S rRNA, 28S rRNA, COI, actin, GAPDH, etc.
├── fb_specific.fasta                # white_gene, rosy_gene
├── wb_specific.fasta                # unc_22, dpy_10
├── sgd_specific.fasta               # GAL1, ACT1
├── zfin_specific.fasta              # pax2a, sonic_hedgehog
├── rgd_specific.fasta               # Alb, Ins1
└── xb_specific.fasta                # sox2, bmp4
```

**Dependencies:** Existing validation.py sequence dictionaries

**Priority:** P1 (Should Have)

---

### FR6: Enhanced Validation Layers

**Description:** Add file integrity checks and database functionality validation beyond BLAST testing.

**Acceptance Criteria:**
- FR6.1: File integrity check validates presence of:
  - `.nin`, `.nhr`, `.nsq` files for nucleotide databases
  - `.pin`, `.phr`, `.psq` files for protein databases
- FR6.2: Database functionality check runs `blastdbcmd -info` to verify:
  - Database is readable
  - Sequence count > 0
  - Format version is current
- FR6.3: Validation runs in layers:
  1. File check (fast, <1 second per database)
  2. Integrity check (medium, 2-5 seconds per database)
  3. BLAST functional test (slow, 30-60 seconds per database)
- FR6.4: Early exit if file check fails (don't run BLAST on broken database)
- FR6.5: Validation report shows results for each layer independently
- FR6.6: File check failures include specific missing file names
- FR6.7: Enhanced validation adds <10% to total validation runtime

**Dependencies:** NCBI BLAST+ tools (blastdbcmd)

**Priority:** P1 (Should Have)

---

### FR7: Multi-MOD Dashboard Report

**Description:** Generate consolidated dashboard showing validation status across all MODs.

**Acceptance Criteria:**
- FR7.1: Dashboard HTML shows status cards for all MODs (FB, SGD, WB, ZFIN, RGD, XB)
- FR7.2: Each MOD card displays:
  - Pass/fail counts
  - Success rate
  - Health status (healthy/warning/critical)
  - Validation timestamp
- FR7.3: Color-coded status indicators:
  - Green: 0 failures
  - Yellow: <10% failure rate
  - Red: ≥10% failure rate
- FR7.4: Dashboard generated via:
  ```bash
  uv run python src/validate_release.py --dashboard --output dashboard.html
  ```
- FR7.5: Dashboard pulls latest validation results for each MOD
- FR7.6: Dashboard includes "last updated" timestamp
- FR7.7: Dashboard responsive for display on large screens/projectors

**Dependencies:** FR1 (HTML report generation), FR3 (JSON export)

**Priority:** P2 (Nice to Have)

---

### FR8: Report Archival and Historical Tracking

**Description:** Automatically archive validation reports with database releases for historical analysis.

**Acceptance Criteria:**
- FR8.1: Reports archived to: `../data/validation_archives/{MOD}/{release}/`
- FR8.2: Archive includes:
  - HTML report
  - JSON export
  - Validation log file
  - Metadata file (timestamp, environment, configuration)
- FR8.3: Archive creation optional via `--archive` flag
- FR8.4: Archives compressed if older than 90 days
- FR8.5: Archives automatically created for production releases
- FR8.6: Archival script can retrieve historical reports:
  ```bash
  uv run python src/get_validation_report.py --mod FB --release 2025_01
  ```
- FR8.7: Archives synced to S3 alongside database files (if `--sync-s3` enabled)

**Dependencies:** FR1, FR2, FR3, existing S3 sync infrastructure

**Priority:** P2 (Nice to Have)

---

## 5. Non-Functional Requirements

### Performance

**NFR1: Validation Runtime**
- HTML report generation: <10 seconds overhead per run
- JSON export: <5 seconds overhead per run
- Enhanced logging: <2 seconds overhead per run
- Total enhancement overhead: <15 seconds on 30-minute validation run (<1% increase)

**NFR2: Report Size**
- HTML reports: <2MB per report (self-contained CSS)
- JSON exports: <5MB per export (for large MODs with 50+ databases)
- Log files: <50MB per validation run (before compression)

**NFR3: Scalability**
- System scales to 100+ databases per MOD
- Dashboard supports up to 10 MODs simultaneously
- Report generation parallelizable for multi-MOD runs

### Reliability

**NFR4: Backward Compatibility**
- All enhancements are additive (no breaking changes)
- Existing `--validate` flag functionality unchanged
- Terminal output remains as-is unless new flags used
- Validation logic unmodified

**NFR5: Error Handling**
- Report generation failures do not break validation
- Missing fixture files fall back to hardcoded sequences
- Invalid JSON/HTML generation logged but validation continues
- Graceful degradation if file system permissions insufficient

**NFR6: Data Integrity**
- JSON exports machine-parseable with JSON Schema validation
- HTML reports render correctly in all major browsers (Chrome, Firefox, Safari, Edge)
- Log files follow standard syslog format for integration with log aggregation tools

### Security

**NFR7: File Permissions**
- Report files created with 0644 permissions (readable by group)
- Log files created with 0640 permissions (group read, no world access)
- Archived reports follow existing S3 bucket permissions

**NFR8: Data Privacy**
- Reports contain only database metadata (no sensitive sequence data)
- Logs sanitize file paths to avoid exposing system structure
- No credentials or secrets in reports/logs

### Usability

**NFR9: Documentation**
- All new CLI flags documented in `--help`
- README includes examples of HTML/JSON generation
- Architecture documentation explains reporter classes
- Test fixtures include README explaining format

**NFR10: Observability**
- Report generation logged with timing information
- Validation failures include actionable error messages
- Dashboard shows last-updated timestamp for staleness detection

---

## 6. Technical Architecture

### 6.1 System Overview

The enhancement adds a **reporter layer** on top of the existing validation engine without modifying core validation logic.

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Pipeline (create_blast_db.py)        │
│                            --validate flag                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Validation Engine (validation.py)               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  DatabaseValidator                                      │ │
│  │  - discover_databases()                                 │ │
│  │  - validate_database()                                  │ │
│  │  - run_blast_test()                                     │ │
│  │                                                          │ │
│  │  ValidationResult                                       │ │
│  │  - db_name, db_path, mod                               │ │
│  │  - conserved_hits, specific_hits                       │ │
│  │  - success, error_message, hit_details                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         NEW: Reporter Layer (validation_reporter.py)         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ValidationReporter                                     │ │
│  │  - generate_html_report()                              │ │
│  │  - generate_json_export()                              │ │
│  │  - generate_dashboard()                                │ │
│  │  - setup_validation_logger()                           │ │
│  │  - archive_reports()                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    HTML Report   JSON Export   Validation Log
```

**Key Principle:** The reporter consumes `ValidationResult` objects without modifying validation logic.

---

### 6.2 Component Design

#### ValidationReporter Class

**Location:** `src/validation_reporter.py` (new file)

```python
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

        # Create directories if needed
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir.mkdir(exist_ok=True, parents=True)

    def generate_html_report(self,
                            validation_results: Dict[str, Dict],
                            mod: str,
                            release: str,
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
        # Implementation from comprehensive-database-testing branch
        pass

    def generate_json_export(self,
                            validation_results: Dict[str, Dict],
                            mod: str,
                            release: str) -> str:
        """
        Export validation results to JSON.

        Args:
            validation_results: Dict mapping MODs to validation stats
            mod: MOD identifier
            release: Release identifier

        Returns:
            Path to generated JSON file
        """
        pass

    def generate_dashboard(self,
                          mods: List[str] = None) -> str:
        """
        Generate multi-MOD dashboard from latest validation results.

        Args:
            mods: List of MODs to include (default: all)

        Returns:
            Path to generated dashboard HTML
        """
        pass

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
        pass

    def archive_reports(self,
                       mod: str,
                       release: str,
                       html_path: str,
                       json_path: str,
                       log_path: str) -> str:
        """
        Archive validation reports for historical tracking.

        Args:
            mod: MOD identifier
            release: Release identifier
            html_path: Path to HTML report
            json_path: Path to JSON export
            log_path: Path to validation log

        Returns:
            Path to archive directory
        """
        pass
```

---

#### Integration with Existing validation.py

**Modification to validation.py:**

```python
# Add at top of file
try:
    from validation_reporter import ValidationReporter
    REPORTER_AVAILABLE = True
except ImportError:
    REPORTER_AVAILABLE = False

# Add to DatabaseValidator.__init__()
def __init__(self,
             logger,
             evalue: str = "10",
             word_size: str = "7",
             timeout: int = 30,
             num_threads: int = 2,
             enable_html: bool = False,     # NEW
             enable_json: bool = False,     # NEW
             output_dir: str = "../reports"): # NEW

    self.logger = logger
    self.evalue = evalue
    self.word_size = word_size
    self.timeout = timeout
    self.num_threads = num_threads

    # NEW: Optional reporter
    self.enable_html = enable_html
    self.enable_json = enable_json
    if (enable_html or enable_json) and REPORTER_AVAILABLE:
        self.reporter = ValidationReporter(output_dir=output_dir)
    else:
        self.reporter = None

# Add to validate_all() method after results collection
def validate_all(self, base_path: str, mod_filter: Optional[str] = None) -> Dict[str, Dict]:
    """Validate all databases..."""

    # ... existing validation logic ...

    # NEW: Generate reports if requested
    if self.reporter:
        if self.enable_html:
            html_path = self.reporter.generate_html_report(
                all_results,
                mod_filter or "all",
                "current"
            )
            log_success(f"HTML report generated: {html_path}")

        if self.enable_json:
            json_path = self.reporter.generate_json_export(
                all_results,
                mod_filter or "all",
                "current"
            )
            log_success(f"JSON export generated: {json_path}")

    return all_results
```

**Key Design Decisions:**
1. **Optional Dependency:** Reporter import wrapped in try/except so validation works without reporter
2. **Opt-In Flags:** HTML/JSON generation disabled by default (backward compatible)
3. **No Logic Changes:** Validation logic unchanged, reporter only consumes results
4. **Clean Separation:** Reporter has no knowledge of BLAST commands or database structure

---

#### Standalone CLI Tool (validate_release.py)

**Location:** `src/validate_release.py` (new file)

```python
#!/usr/bin/env python3
"""
Standalone database validation tool for AGR BLAST databases.

Can run independently of main pipeline for manual QA and troubleshooting.
"""

import click
from pathlib import Path
from validation import DatabaseValidator
from validation_reporter import ValidationReporter
from utils import setup_detailed_logger

@click.command()
@click.option('--mod', '-m', required=True, help='MOD to validate (FB, SGD, WB, etc.)')
@click.option('--env', '-e', default='prod', help='Environment (dev/stage/prod)')
@click.option('--db-path', help='Custom database path override')
@click.option('--html', is_flag=True, help='Generate HTML report')
@click.option('--json', is_flag=True, help='Generate JSON export')
@click.option('--dashboard', is_flag=True, help='Generate multi-MOD dashboard')
@click.option('--evalue', default='10', help='BLAST e-value threshold')
@click.option('--word-size', default='7', help='BLAST word size')
@click.option('--timeout', default=30, type=int, help='BLAST timeout (seconds)')
@click.option('--output-dir', default='../reports', help='Output directory for reports')
def validate(mod, env, db_path, html, json, dashboard, evalue, word_size, timeout, output_dir):
    """Validate BLAST databases for a specific MOD."""

    # Setup logging
    logger = setup_detailed_logger(f"validate_{mod}", f"validation_{mod}_{env}.log")

    # Determine database path
    if not db_path:
        db_path = f"../data/blast/{mod}/{env}/databases"

    logger.info(f"Starting validation for {mod} in {env} environment")
    logger.info(f"Database path: {db_path}")

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
    results = validator.validate_all(db_path, mod_filter=mod)

    # Exit code based on results
    if not results:
        logger.error("No databases found")
        return 2

    total_failed = sum(r['failed'] for r in results.values())
    if total_failed > 0:
        logger.warning(f"Validation complete with {total_failed} failures")
        return 1
    else:
        logger.info("All databases validated successfully")
        return 0

if __name__ == '__main__':
    import sys
    sys.exit(validate())
```

**Usage Examples:**

```bash
# Basic validation with terminal output
uv run python src/validate_release.py --mod FB --env prod

# Generate HTML report
uv run python src/validate_release.py --mod SGD --env prod --html

# Full validation with all outputs
uv run python src/validate_release.py --mod WB --env prod --html --json

# Custom database path
uv run python src/validate_release.py --mod ZFIN --db-path /custom/path --html

# Strict validation with tighter thresholds
uv run python src/validate_release.py --mod RGD --evalue 0.001 --word-size 11
```

---

#### Test Fixture Loader

**Location:** `src/validation.py` (enhancement to existing file)

```python
def load_test_fixtures(fixtures_dir: str = "tests/fixtures") -> Tuple[Dict, Dict]:
    """
    Load test sequences from external FASTA files.

    Args:
        fixtures_dir: Path to test fixtures directory

    Returns:
        Tuple of (conserved_sequences, mod_specific_sequences)
    """
    fixtures_path = Path(fixtures_dir)

    # Try to load conserved sequences from file
    conserved_file = fixtures_path / "universal_conserved.fasta"
    if conserved_file.exists():
        conserved_sequences = parse_fasta_file(conserved_file)
    else:
        # Fall back to hardcoded sequences
        conserved_sequences = CONSERVED_SEQUENCES.copy()

    # Try to load MOD-specific sequences
    mod_specific_sequences = {}
    for mod in ["FB", "WB", "SGD", "ZFIN", "RGD", "XB"]:
        mod_file = fixtures_path / f"{mod.lower()}_specific.fasta"
        if mod_file.exists():
            mod_specific_sequences[mod] = parse_fasta_file(mod_file)
        else:
            # Fall back to hardcoded sequences
            mod_specific_sequences[mod] = MOD_SPECIFIC_SEQUENCES.get(mod, {})

    return conserved_sequences, mod_specific_sequences

def parse_fasta_file(fasta_path: Path) -> Dict[str, str]:
    """
    Parse FASTA file into dictionary of sequences.

    Args:
        fasta_path: Path to FASTA file

    Returns:
        Dictionary mapping sequence names to FASTA content
    """
    sequences = {}
    current_name = None
    current_seq = []

    with open(fasta_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                # Save previous sequence
                if current_name:
                    sequences[current_name] = '>' + '\n'.join(current_seq)

                # Start new sequence
                current_name = line[1:].split()[0]  # First word after >
                current_seq = [line[1:]]  # Header line
            elif line:
                current_seq.append(line)

        # Save last sequence
        if current_name:
            sequences[current_name] = '>' + '\n'.join(current_seq)

    return sequences
```

**Fixture File Format Example:**

`tests/fixtures/universal_conserved.fasta`:
```fasta
>18S_rRNA Universal 18S ribosomal RNA conserved across eukaryotes
GTCAGAGGTGAAATTCTTGGATCGCCGCAAGACGAACCAAAGCGAAAGCATTTGCCAAG
AATGTTTTCATTAATCAAGAACGAAAGTTAGAGGTTCGAAGGCGATCAGATACCGCCCT
AGTTCTAACCATAAACGATGCCGACCAGGGATCAGCGAATGTTACGCT

>28S_rRNA Universal 28S ribosomal RNA conserved across eukaryotes
GCCGGATCCTTTGAAGACGGGTCGCTTGCGACCCGACGCCAAGGAACCAAGCTGACCGT
CGAGGCAACCCACTCGGACGGGGGCCCAAGTCCAACTACGAGCTTTTTAACTGCAGCAA
CCGAAGCGTACCGCATGGCCGTTGCGCTTCGGC

>actin Universal actin gene conserved across eukaryotes
ATGTGTGACGACGAGGAGACCACCGCCCTCGTCACCAGAGTCCATCACGATGCCAGTCC
TCAAGAACCCCTAAGGCCAACCGTGAAAAGATGACCCAGATCATGTTTGAGACCTTCAA
CACCCCCGCCATGTACGTTGCCATCCAGGCCGTGCTGTCCCT
```

---

### 6.3 Data Flow

**Validation with Reporting Enabled:**

```
1. User runs: create_blast_db.py --validate --html --json
   │
   ├──> Pipeline creates databases
   │
   ├──> Pipeline invokes DatabaseValidator with enable_html=True, enable_json=True
   │
   ├──> DatabaseValidator initializes ValidationReporter
   │
   ├──> DatabaseValidator.discover_databases() finds all databases
   │
   ├──> For each database:
   │    ├──> validate_database() runs BLAST tests
   │    ├──> Returns ValidationResult object
   │    └──> ValidationResult added to results collection
   │
   ├──> After all validations:
   │    ├──> Terminal output (existing functionality)
   │    ├──> Slack notification (existing functionality)
   │    │
   │    ├──> ValidationReporter.generate_html_report()
   │    │    ├──> Transforms ValidationResult to HTML
   │    │    ├──> Applies CSS styling
   │    │    └──> Writes to file
   │    │
   │    └──> ValidationReporter.generate_json_export()
   │         ├──> Transforms ValidationResult to JSON
   │         ├──> Validates JSON schema
   │         └──> Writes to file
   │
   └──> Pipeline continues with S3 sync, etc.
```

**Standalone Validation:**

```
1. User runs: validate_release.py --mod FB --html --json
   │
   ├──> Script sets up dedicated logger
   │
   ├──> Script creates DatabaseValidator with reporter enabled
   │
   ├──> DatabaseValidator runs validation (same as integrated mode)
   │
   ├──> Reports generated
   │
   └──> Script exits with appropriate exit code
```

---

### 6.4 File Organization

**New/Modified Files:**

```
src/
├── validation.py              # MODIFIED: Add reporter integration
├── validation_reporter.py     # NEW: HTML/JSON report generation
├── validate_release.py        # NEW: Standalone CLI tool
└── create_blast_db.py         # MODIFIED: Add --html/--json flags

tests/
├── fixtures/                  # NEW: External test sequences
│   ├── universal_conserved.fasta
│   ├── fb_specific.fasta
│   ├── wb_specific.fasta
│   ├── sgd_specific.fasta
│   ├── zfin_specific.fasta
│   ├── rgd_specific.fasta
│   ├── xb_specific.fasta
│   └── README.md              # NEW: Fixture documentation
└── unit/
    ├── test_validation.py     # EXISTING: May need minor updates
    └── test_validation_reporter.py  # NEW: Reporter unit tests

reports/                       # NEW: HTML/JSON output directory
├── validation_report_FB_2025_01_*.html
├── validation_results_FB_2025_01_*.json
└── validation_dashboard_*.html

logs/
└── validation/                # NEW: Dedicated validation logs
    └── database_validation_FB_prod_*.log

data/
└── validation_archives/       # NEW: Archived reports
    └── FB/
        └── 2025_01/
            ├── validation_report.html
            ├── validation_results.json
            ├── validation.log
            └── metadata.json
```

---

## 7. User Experience (UX) and Design

### 7.1 HTML Report Visual Design

**Report Header:**
```
╔═══════════════════════════════════════════════════════════════╗
║        Database Validation Report                              ║
║        FB Release 2025_01 - Generated 2025-01-15 10:45:23    ║
╚═══════════════════════════════════════════════════════════════╝
```

**Executive Summary Cards:**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  25          │  │  2           │  │  27          │  │  92.6%       │
│  Passed      │  │  Failed      │  │  Total       │  │  Success     │
│  [GREEN]     │  │  [RED]       │  │  [BLUE]      │  │  Rate        │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

**Progress Bar:**
```
Validation Success Rate:
[████████████████████████████████░░░░] 92.6%
```

**Database Grid (Failed Databases):**
```
╔════════════════════════════════════════════════════════════╗
║  Failed Databases (2)                                       ║
╠════════════════════════════════════════════════════════════╣
║  ┌────────────────────────────────────────────────┐       ║
║  │  dmel_protein_coding [FAILED]                  │       ║
║  │  File Check: ✗ Missing .pin file               │       ║
║  │  Integrity: ✗ Not checked (file check failed)  │       ║
║  │  Time: 2.3s                                     │       ║
║  └────────────────────────────────────────────────┘       ║
║                                                             ║
║  ┌────────────────────────────────────────────────┐       ║
║  │  dmel_ncrna [FAILED]                           │       ║
║  │  File Check: ✓ Passed                          │       ║
║  │  Integrity: ✓ Passed                           │       ║
║  │  BLAST Test: ✗ 0 hits across 10 tests         │       ║
║  │  Time: 45.2s                                    │       ║
║  └────────────────────────────────────────────────┘       ║
╚════════════════════════════════════════════════════════════╝
```

**Successful Databases Table:**
```
╔════════════════════════════════════════════════════════════════════╗
║  Successful Databases (25)                                          ║
╠════════════════════════════════════════════════════════════════════╣
║  Database              │ Sequences │ Hits │ Time  │ Status         ║
║────────────────────────┼───────────┼──────┼───────┼────────────────║
║  dmel_genomic          │ 14,256    │ 57   │ 35.2s │ ✓ PASSED      ║
║  dmel_transcript       │ 31,829    │ 64   │ 42.1s │ ✓ PASSED      ║
║  dmel_protein          │ 21,305    │ 48   │ 38.5s │ ✓ PASSED      ║
║  ...                   │ ...       │ ...  │ ...   │ ...           ║
╚════════════════════════════════════════════════════════════════════╝
```

**Color Scheme:**
- **Success Green:** #28a745 (Bootstrap success)
- **Warning Yellow:** #ffc107 (Bootstrap warning)
- **Error Red:** #dc3545 (Bootstrap danger)
- **Info Blue:** #007bff (Bootstrap primary)
- **Background:** #f8f9fa (Light gray)
- **Header Gradient:** Purple to indigo (#667eea → #764ba2)

---

### 7.2 Multi-MOD Dashboard Design

**Dashboard Layout:**
```
╔═══════════════════════════════════════════════════════════════════╗
║           AGR Database Validation Dashboard                        ║
║    Real-time status of BLAST database health across all MODs       ║
║         Last Updated: 2025-01-15 10:45:23                         ║
╚═══════════════════════════════════════════════════════════════════╝

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  FB (2025_01)  │  │  SGD (S288C)   │  │  WB (WS291)    │
│                │  │                │  │                │
│  ┌──────┬────┐ │  │  ┌──────┬────┐ │  │  ┌──────┬────┐ │
│  │ 25   │ 2  │ │  │  │ 15   │ 0  │ │  │  │ 12   │ 1  │ │
│  │Passed│Fail│ │  │  │Passed│Fail│ │  │  │Passed│Fail│ │
│  └──────┴────┘ │  │  └──────┴────┘ │  │  └──────┴────┘ │
│                │  │                │  │                │
│    92.6%       │  │    100%        │  │    92.3%       │
│  Success Rate  │  │  Success Rate  │  │  Success Rate  │
│                │  │                │  │                │
│  ⚠ WARNING     │  │  ✓ HEALTHY     │  │  ⚠ WARNING    │
└────────────────┘  └────────────────┘  └────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  ZFIN          │  │  RGD           │  │  XB            │
│  (GRCz11)      │  │  (mRatBN7.2)   │  │  (10.0)        │
│  ...           │  │  ...           │  │  ...           │
└────────────────┘  └────────────────┘  └────────────────┘
```

**Status Indicators:**
- ✓ HEALTHY (Green): 0 failures
- ⚠ WARNING (Yellow): 1-10% failures
- ✗ CRITICAL (Red): >10% failures

---

### 7.3 CLI Output Examples

**Standalone Validation with Reports:**

```bash
$ uv run python src/validate_release.py --mod FB --env prod --html --json

╔════════════════════════════════════════════════════════════════╗
║         AGR BLAST Database Validation                           ║
╚════════════════════════════════════════════════════════════════╝

MOD: FB
Environment: prod
Database Path: ../data/blast/FB/prod/databases
E-value: 10, Word size: 7, Timeout: 30s

[INFO] Discovering databases...
[INFO] Found 27 databases for FB

╔════════════════════════════════════════════════════════════════╗
║  Validating FB Databases                                        ║
╚════════════════════════════════════════════════════════════════╝

Validating FB databases... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 27/27 [02:15]

╔════════════════════════════════════════════════════════════════╗
║  FB Validation Summary                                          ║
╠════════════════════════════════════════════════════════════════╣
║  Total Databases:        27                                     ║
║  Passed:                 25                                     ║
║  Failed:                 2                                      ║
║  Pass Rate:              92.6%                                  ║
║  Conserved Hits:         20                                     ║
║  Total Hits:             1,520                                  ║
║  Duration:               2:15.3                                 ║
╚════════════════════════════════════════════════════════════════╝

[SUCCESS] HTML report generated: ../reports/validation_report_FB_2025_01_20250115_104523.html
[SUCCESS] JSON export generated: ../reports/validation_results_FB_2025_01_20250115_104523.json

[WARNING] 2 databases failed validation - see report for details

Exit code: 1 (failures detected)
```

**Integrated Validation (in main pipeline):**

```bash
$ uv run python src/create_blast_db.py -m FB -e prod --validate --html --json

# ... database creation output ...

╔════════════════════════════════════════════════════════════════╗
║  Post-Creation Database Validation                              ║
╚════════════════════════════════════════════════════════════════╝

[INFO] Starting validation for FB databases
[INFO] E-value: 10, Word size: 7, Timeout: 30s

Validating FB databases... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 27/27 [02:15]

[SUCCESS] Validation complete: 92.6% pass rate
[SUCCESS] HTML report: ../reports/validation_report_FB_prod_20250115_104523.html
[SUCCESS] JSON export: ../reports/validation_results_FB_prod_20250115_104523.json

# ... pipeline continues ...
```

---

## 8. Implementation Plan

### Phase 1: Core Reporting (Weeks 1-2)

**Week 1: HTML Report Generation**
- Create `validation_reporter.py` with `ValidationReporter` class
- Implement `generate_html_report()` with CSS styling
- Add unit tests for HTML generation
- Update `validation.py` to accept `enable_html` flag
- Test HTML reports with sample validation data
- Document HTML report structure

**Deliverables:**
- ✅ Working HTML report generation
- ✅ Unit tests passing
- ✅ Example reports for all MODs
- ✅ Documentation updated

**Week 2: JSON Export and Enhanced Logging**
- Implement `generate_json_export()` in reporter
- Create JSON schema for validation results
- Enhance logging infrastructure with dedicated handlers
- Add log rotation policy
- Create unit tests for JSON export and logging
- Integration tests with full validation flow

**Deliverables:**
- ✅ JSON export functionality working
- ✅ Enhanced logging system operational
- ✅ JSON schema documented
- ✅ Integration tests passing

---

### Phase 2: Standalone CLI and Fixtures (Week 3)

**Week 3: Standalone Tool and Test Fixtures**
- Create `validate_release.py` CLI tool
- Implement all CLI flags and help text
- Create test fixture files in `tests/fixtures/`
- Implement fixture loader in `validation.py`
- Add fallback logic for missing fixtures
- Create README for test fixtures
- End-to-end testing of standalone tool

**Deliverables:**
- ✅ Standalone CLI tool working
- ✅ Test fixtures created for all MODs
- ✅ Fixture loader with fallback implemented
- ✅ Documentation for CLI usage
- ✅ QA team can validate independently

---

### Phase 3: Advanced Features (Week 4)

**Week 4: Enhanced Validation and Dashboard**
- Implement file integrity checks (FR6)
- Add `blastdbcmd -info` validation layer
- Create multi-MOD dashboard generation
- Implement report archival system
- Add S3 sync for archived reports
- Performance testing and optimization
- Final documentation and examples

**Deliverables:**
- ✅ Enhanced validation layers working
- ✅ Multi-MOD dashboard operational
- ✅ Report archival system complete
- ✅ Performance benchmarks documented
- ✅ Full documentation suite

---

### Testing Strategy

**Unit Tests:**
- ValidationReporter methods (HTML, JSON, dashboard)
- Fixture loader with missing files
- Logging handler configuration
- JSON schema validation
- Exit code generation

**Integration Tests:**
- Full validation flow with reporting enabled
- Standalone CLI with all flag combinations
- Report generation with real validation data
- Archive creation and retrieval
- S3 sync integration

**Performance Tests:**
- Report generation overhead measurement
- Large database validation (100+ databases)
- Dashboard generation with 10 MODs
- Log file size monitoring

**User Acceptance Tests:**
- QA team validates databases using standalone CLI
- Product manager reviews HTML reports
- DevOps integrates JSON export into CI/CD
- Stakeholders review dashboard display

---

### Rollout Plan

**Stage 1: Internal Alpha (Week 2)**
- Deploy to development environment
- Engineering team validates HTML/JSON output
- Fix critical bugs and usability issues
- Performance tuning

**Stage 2: QA Beta (Week 3)**
- Deploy standalone CLI to QA team
- QA team runs parallel validations (terminal vs. reports)
- Gather feedback on HTML report clarity
- Iterate on UX based on QA feedback

**Stage 3: Limited Production (Week 4)**
- Enable HTML/JSON for single MOD (FB) in production
- Monitor report generation overhead
- Verify archival and S3 sync
- Stakeholder review of first production reports

**Stage 4: Full Rollout (Week 5+)**
- Enable reporting for all MODs
- Update documentation and training materials
- Announce to external MOD contributors
- Monitor adoption metrics

**Guardrails:**
- Report generation overhead must stay <15 seconds per run
- HTML reports must render correctly in all browsers
- JSON schema must validate successfully
- No increase in validation failure rate

**Kill-Switch Criteria:**
- Report generation overhead >30 seconds
- HTML reports cause browser crashes
- JSON exports corrupt or unparseable
- Logging fills disk space (>10GB/day)
- Validation failures increase >5%

---

## 9. Risks and Mitigations

### Technical Risks

**RISK 1: Report Generation Performance Impact**
- **Likelihood:** Medium
- **Impact:** High
- **Description:** HTML/JSON generation could slow validation significantly
- **Mitigation:**
  - Implement streaming HTML generation (don't build entire report in memory)
  - Lazy-load validation results during report generation
  - Profile code and optimize hotspots
  - Make reporting async/parallel
- **Contingency:** Add `--fast` flag that skips reporting

**RISK 2: Backward Compatibility Break**
- **Likelihood:** Low
- **Impact:** Critical
- **Description:** Reporter integration could break existing validation
- **Mitigation:**
  - All reporter features opt-in via flags
  - Extensive integration testing
  - Feature flags for gradual rollout
  - Fallback to existing behavior if reporter unavailable
- **Contingency:** Quick rollback via feature flag

**RISK 3: Disk Space Exhaustion**
- **Likelihood:** Medium
- **Impact:** Medium
- **Description:** Reports and logs could fill disk space
- **Mitigation:**
  - Implement log rotation (30-day retention)
  - Compress archived reports
  - Monitor disk usage with alerts
  - Document cleanup procedures
- **Contingency:** Emergency cleanup script

**RISK 4: HTML Report Browser Compatibility**
- **Likelihood:** Low
- **Impact:** Medium
- **Description:** Reports may not render correctly in all browsers
- **Mitigation:**
  - Use standard HTML5/CSS3
  - Test in Chrome, Firefox, Safari, Edge
  - Avoid JavaScript dependencies
  - Progressive enhancement approach
- **Contingency:** Provide text-only report fallback

---

### User Experience Risks

**RISK 5: Report Complexity Overwhelming Users**
- **Likelihood:** Medium
- **Impact:** Medium
- **Description:** Too much information could confuse stakeholders
- **Mitigation:**
  - Design executive summary at top
  - Use progressive disclosure (summary → details)
  - Provide report interpretation guide
  - Offer simplified "dashboard view"
- **Contingency:** Create simplified report template

**RISK 6: Low Adoption of Standalone CLI**
- **Likelihood:** Medium
- **Impact:** Low
- **Description:** QA team may not adopt new tool
- **Mitigation:**
  - Involve QA in design process
  - Provide training and documentation
  - Make CLI usage simpler than alternatives
  - Track adoption metrics
- **Contingency:** Provide guided tutorial or wizard mode

**RISK 7: JSON Schema Changes Break Automation**
- **Likelihood:** Low
- **Impact:** High
- **Description:** Future JSON changes could break CI/CD integrations
- **Mitigation:**
  - Version JSON schema explicitly
  - Maintain backward compatibility
  - Document schema in OpenAPI format
  - Provide migration guides
- **Contingency:** Support multiple schema versions

---

### Operational Risks

**RISK 8: Increased Support Burden**
- **Likelihood:** Medium
- **Impact:** Medium
- **Description:** More features = more support questions
- **Mitigation:**
  - Comprehensive documentation
  - FAQ for common issues
  - Self-service troubleshooting guide
  - Clear error messages
- **Contingency:** Office hours for Q&A

**RISK 9: Dependency on Comprehensive-Database-Testing Branch**
- **Likelihood:** Low
- **Impact:** Medium
- **Description:** Code from branch may have hidden issues
- **Mitigation:**
  - Thorough code review of imported code
  - Refactor to match main branch patterns
  - Comprehensive testing
  - Don't blindly copy—adapt and improve
- **Contingency:** Rewrite reporter from scratch if needed

**RISK 10: Archive Storage Costs**
- **Likelihood:** Low
- **Impact:** Low
- **Description:** S3 archival could increase AWS costs
- **Mitigation:**
  - Use S3 lifecycle policies (archive to Glacier)
  - Compress reports before upload
  - Retention policy (keep 1 year)
  - Monitor costs with alerts
- **Contingency:** Reduce retention period

---

## 10. Open Questions and Decisions Needed

### Product Decisions

**Q1: Report Retention Policy**
- How long should HTML/JSON reports be kept locally?
- How long should archived reports be kept in S3?
- **Recommendation:** 30 days local, 1 year S3, then Glacier

**Q2: Default Behavior for Reporting**
- Should HTML/JSON be opt-in or opt-out?
- Should production runs automatically generate reports?
- **Recommendation:** Opt-in for now, consider opt-out after Phase 3

**Q3: Dashboard Refresh Frequency**
- Should dashboard auto-refresh or require manual regeneration?
- How often should dashboard be updated?
- **Recommendation:** Manual generation, consider auto-refresh in future

**Q4: Report Distribution**
- Should reports be automatically emailed to stakeholders?
- Should reports be posted to Slack?
- **Recommendation:** Slack notification with report link, not full report

---

### Technical Decisions

**Q5: HTML Templating Engine**
- Use Python string formatting or templating library (Jinja2)?
- **Recommendation:** Start with string formatting (no dependency), consider Jinja2 if templates become complex

**Q6: JSON Schema Standard**
- Use JSON Schema standard or custom format?
- Include JSON-LD metadata?
- **Recommendation:** Use JSON Schema standard for validation, skip JSON-LD (not needed)

**Q7: Logging Framework**
- Integrate with existing logger or create new logger?
- Use structlog for structured logging?
- **Recommendation:** Extend existing logger, avoid new dependencies

**Q8: Test Fixture Format**
- Keep FASTA or use JSON/YAML?
- Include metadata in fixtures?
- **Recommendation:** FASTA for sequence data, separate metadata file if needed

---

### Integration Decisions

**Q9: CI/CD Integration**
- Should JSON export trigger automated actions?
- What thresholds should trigger pipeline failures?
- **Recommendation:** Leave to DevOps team, provide documentation on exit codes

**Q10: Slack Notification Enhancement**
- Include report summary in Slack message?
- Attach HTML report or just link?
- **Recommendation:** Include summary stats, link to full report (don't attach)

**Q11: S3 Bucket Structure**
- Where should archived reports be stored?
- Same bucket as databases or separate?
- **Recommendation:** Separate `agr-blast-validation-reports` bucket for clarity

**Q12: Multi-MOD Validation**
- Should standalone CLI support validating all MODs at once?
- Should dashboard be generated automatically?
- **Recommendation:** Yes to both, add `--all` flag to CLI

---

## 11. Success Criteria Summary

The enhancement will be considered successful if:

### Must-Have Criteria (Phase 1-2)

✅ **HTML reports generated for 90%+ of validation runs**
✅ **JSON export adopted by DevOps for CI/CD quality gates**
✅ **Enhanced logging reduces debugging time by 50%+**
✅ **Zero breaking changes to existing validation users**
✅ **Report generation overhead <15 seconds per run**

### Should-Have Criteria (Phase 3)

✅ **QA team uses standalone CLI for 80%+ of manual validations**
✅ **Stakeholder satisfaction with reports ≥4.5/5**
✅ **Multi-MOD dashboard displays correctly on all browsers**
✅ **Report archives successfully synced to S3**

### Nice-to-Have Criteria (Post-Phase 3)

✅ **External MOD contributors use standalone CLI**
✅ **Validation reports referenced in publications**
✅ **Automated quality gate prevents 1+ bad production deployment**

---

## 12. Appendix

### A. Related Documents

- **Technical Specification:** `docs/validation_technical_design.md` (comprehensive-database-testing branch)
- **User Guide:** `docs/validation_user_guide.md` (to be created)
- **API Reference:** `docs/api/validation_reporter.md` (to be created)
- **Architecture Decision Record:** `docs/adr/003-validation-reporting.md` (to be created)

### B. Glossary

- **MOD:** Model Organism Database (FB, SGD, WB, ZFIN, RGD, XB)
- **Conserved Sequence:** Genetic sequence found across all eukaryotic organisms (e.g., 18S rRNA)
- **Hit Rate:** Percentage of BLAST tests that produce matches
- **Validation Layer:** Separate testing phase (file check → integrity → BLAST)
- **Test Fixture:** Pre-defined test sequence used for validation

### C. References

- **Existing Validation System:** [Commit b94273c](https://github.com/alliance-genome/agr_blastdb_manager/commit/b94273c) - "Add post-creation BLAST database validation feature"
- **Comprehensive Testing Branch:** [comprehensive-database-testing](https://github.com/alliance-genome/agr_blastdb_manager/tree/comprehensive-database-testing)
- **NCBI BLAST+ Documentation:** https://www.ncbi.nlm.nih.gov/books/NBK279690/
- **JSON Schema Standard:** https://json-schema.org/

### D. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-15 | Product Management | Initial draft for review |

---

## Document Approval

**Stakeholders:**
- [ ] Product Management (Owner)
- [ ] Engineering Lead (Reviewer)
- [ ] QA Lead (Reviewer)
- [ ] DevOps Lead (Reviewer)
- [ ] AGR Project Manager (Approver)

**Next Steps:**
1. Review PRD with stakeholders (1 week)
2. Address feedback and finalize
3. Create engineering tickets from functional requirements
4. Kickoff Phase 1 implementation

---

**End of Document**
