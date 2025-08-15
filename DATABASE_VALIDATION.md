# Database Validation System

Comprehensive BLAST database testing and validation framework for AGR databases. Automatically validates database integrity, functionality, and searchability after creation.

## Features

### 🔍 **Comprehensive Validation**
- **File Integrity**: Checks all required database files (.nin, .nhr, .nsq)
- **Database Functionality**: Validates with `blastdbcmd -info`
- **Search Capability**: Tests with universal conserved sequences
- **Performance Metrics**: Tracks validation time and hit rates

### 📊 **Rich Reporting**
- **HTML Reports**: Beautiful, interactive validation reports
- **JSON Exports**: Structured data for integration
- **Dashboard View**: Multi-MOD status overview
- **Real-time Logging**: Detailed validation logs

### 🤖 **Automated Integration**
- **Post-Creation Validation**: Runs automatically after database creation
- **Slack Notifications**: Sends validation results to Slack
- **CI/CD Ready**: Standalone validation scripts
- **Production Safe**: Non-destructive testing only

## Quick Start

### Automatic Validation (Recommended)

Database validation runs automatically after successful database creation:

```bash
# Validation runs by default
uv run python src/create_blast_db.py --conf conf/global.yaml --mod FB --env FB2025_03

# Explicitly enable validation (default)
uv run python src/create_blast_db.py --conf conf/global.yaml --mod WB --env WS297 --validate-databases

# Skip validation (not recommended for production)
uv run python src/create_blast_db.py --conf conf/global.yaml --mod SGD --env main --skip-validation
```

### Manual Validation

Validate a specific release independently:

```bash
# Validate FB release
uv run python src/validate_release.py validate -m FB -r FB2025_03

# Validate with JSON report
uv run python src/validate_release.py validate -m SGD -r main --json-report

# List available releases
uv run python src/validate_release.py list
```

## Validation Process

### 1. File Integrity Check
Verifies all required BLAST database files exist and are readable:
- `.nin` - Nucleotide database index
- `.nhr` - Header file
- `.nsq` - Sequence file

### 2. Database Functionality Test  
Uses `blastdbcmd -info` to verify:
- Database is properly formatted
- Contains sequences (not empty)
- Metadata is accessible
- No corruption detected

### 3. Search Capability Test
Performs BLAST searches using universal conserved sequences:
- **18S/28S rRNA** - Universal ribosomal sequences
- **Cytochrome c oxidase (COI)** - Mitochondrial gene
- **Actin, GAPDH, Histone H3** - Housekeeping proteins
- **EF-1α, U6 snRNA** - Translation/splicing machinery

**BLAST Parameters:**
- E-value: ≤ 10 (very permissive)
- Word size: 7 (sensitive)
- Max targets: 5 (limited output)

## Reports and Logs

### Detailed Logs
Comprehensive validation logs stored in `../logs/`:
```
database_validation_20250815_143022.log    # Detailed validation log
validation_report_FB_FB2025_03_20250815_143022.json  # Structured results
```

### HTML Reports
Beautiful, interactive reports with:
- **Executive Summary**: Pass/fail statistics
- **Database Details**: Individual validation results  
- **Performance Metrics**: Timing and hit rate analysis
- **Technical Information**: Test parameters and methodology

### Dashboard View
Multi-MOD status dashboard showing:
- Real-time health status across all MODs
- Success rates and failure counts
- Recent validation timestamps
- Visual status indicators

## Configuration

### Environment Variables
```bash
# Optional: Custom paths
export LOG_DIR="../logs"
export REPORT_DIR="../reports"
export TEST_SEQUENCES_DIR="../tests/fixtures"
```

### CLI Options
```bash
# Main database creation
--validate-databases     # Enable validation (default: true)
--skip-validation       # Skip validation (not recommended)

# Standalone validation
-m, --mod               # MOD to validate (FB, SGD, WB, ZFIN, RGD)
-r, --release          # Release version  
-b, --base-path        # Base path to databases
--json-report          # Generate JSON report
```

## Integration Examples

### CI/CD Pipeline
```yaml
# .github/workflows/database-validation.yml
name: Database Validation
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate Databases
        run: |
          uv run python src/validate_release.py validate -m FB -r FB2025_03 --json-report
          uv run python src/validate_release.py validate -m SGD -r main --json-report
```

### Monitoring Script
```bash
#!/bin/bash
# validate_all_latest.sh - Validate all latest releases

MODS=("FB" "SGD" "WB" "ZFIN" "RGD")
RELEASES=("FB2025_03" "main" "WS297" "prod" "production")

for i in "${!MODS[@]}"; do
    echo "Validating ${MODS[$i]} ${RELEASES[$i]}..."
    uv run python src/validate_release.py validate \
        -m "${MODS[$i]}" \
        -r "${RELEASES[$i]}" \
        --json-report
done

# Generate dashboard
uv run python -c "
from src.validation_reporter import ValidationReporter
reporter = ValidationReporter()
dashboard = reporter.generate_dashboard_report()
print(f'Dashboard generated: {dashboard}')
"
```

### Slack Integration
Validation results are automatically sent to Slack when configured:

```python
# Automatic Slack notifications include:
✅ "FB FB2025_03: All 156 databases validated successfully"
⚠️  "WB WS297: 3/89 databases failed validation"  
❌ "SGD main: Database validation failed - Connection timeout"
```

## Troubleshooting

### Common Issues

**"Missing required file"**
- Database creation incomplete or interrupted
- Check disk space and permissions
- Re-run database creation process

**"Database contains 0 sequences"** 
- FASTA file was empty during creation
- Download issue or corrupted source file
- Verify source data and re-create

**"BLAST search failed"**
- Test sequences missing from fixtures
- BLAST not installed or not in PATH
- Check universal_conserved.fasta exists

**"Validation timeout"**
- Large databases may need longer timeout
- Network issues with remote databases
- Consider running during off-peak hours

### Debug Mode
Enable detailed logging:
```bash
export PYTHONPATH=/path/to/src
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from database_validator import DatabaseValidator
validator = DatabaseValidator()
results = validator.validate_release('FB', 'FB2025_03')
"
```

### Manual Testing
Test individual components:
```bash
# Test file integrity
ls -la /var/sequenceserver-data/blast/FB/FB2025_03/databases/*/*.{nin,nhr,nsq}

# Test database functionality  
blastdbcmd -db /path/to/database -info

# Test search capability
blastn -query tests/fixtures/universal_conserved.fasta \
       -db /path/to/database \
       -evalue 10 -word_size 7 -max_target_seqs 5
```

## Architecture

### Core Components

**`DatabaseValidator`** (`src/database_validator.py`)
- Main validation engine
- Handles file, integrity, and functionality checks
- Generates structured results

**`validate_release.py`** (`src/validate_release.py`)  
- Standalone CLI tool for manual validation
- Supports single release or batch validation
- Integrates with CI/CD pipelines

**`ValidationReporter`** (`src/validation_reporter.py`)
- Generates HTML reports and dashboards
- Creates summary notifications
- Handles multi-MOD status views

### Data Flow
```
Database Creation → Validation → Logging → Reporting → Notification
       ↓                ↓           ↓          ↓           ↓
   makeblastdb → File Check → JSON Log → HTML Report → Slack
                      ↓           ↓          ↓
                 Integrity → Text Log → Dashboard
                      ↓           ↓
                BLAST Test → Metrics
```

### File Structure
```
src/
├── database_validator.py    # Core validation engine
├── validate_release.py      # Standalone validation CLI
├── validation_reporter.py   # Report generation
└── create_blast_db.py      # Main pipeline (integrated)

tests/fixtures/
└── universal_conserved.fasta  # Test sequences

logs/                        # Validation logs
├── database_validation_*.log
└── validation_report_*.json

reports/                     # Generated reports  
├── validation_report_*.html
└── validation_dashboard_*.html
```

## Best Practices

### For Production
- ✅ Always run validation after database creation
- ✅ Monitor validation reports regularly
- ✅ Set up automated Slack notifications
- ✅ Archive validation logs for compliance
- ✅ Use dashboard for daily health checks

### For Development
- ✅ Run validation before deployment
- ✅ Test with representative data samples
- ✅ Validate custom sequences work correctly
- ✅ Check validation performance on large databases
- ✅ Document any validation bypasses

### For CI/CD
- ✅ Include validation in deployment pipelines
- ✅ Fail builds on validation errors
- ✅ Generate artifacts for validation reports  
- ✅ Set up monitoring alerts
- ✅ Archive reports for historical analysis

## Contributing

To extend the validation system:

1. **Add new validation checks** in `DatabaseValidator` class
2. **Create custom test sequences** in `tests/fixtures/`
3. **Enhance reporting** in `ValidationReporter` class  
4. **Update documentation** for new features
5. **Add tests** for new validation logic

## Support

For issues or questions:
- Check logs in `../logs/database_validation_*.log`
- Review HTML reports for detailed analysis
- Validate test sequences are accessible
- Ensure BLAST tools are properly installed
- Contact AGR database team for MOD-specific issues