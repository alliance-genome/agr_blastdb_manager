# Comprehensive UI Testing Framework

## Overview

The AGR BLAST UI Testing Framework provides a robust, two-phase approach to testing BLAST web interfaces across multiple Model Organism Databases (MODs). The framework automatically discovers URLs from AGR BLAST service configurations, finds and tests checkboxes, and validates search functionality.

## Key Features

- **Two-Phase Testing Approach**: Discovery → Systematic Testing
- **Automatic URL Discovery**: From AGR BLAST service configuration files
- **Checkbox Discovery & Testing**: Finds and tests individual checkboxes systematically  
- **Biological Test Sequences**: Uses conserved sequences (18S rRNA, HSP70, Actin, Histone H3)
- **Rich Progress Tracking**: Real-time progress bars and status updates
- **Comprehensive Reporting**: Markdown reports with screenshots and metrics
- **Cross-MOD Support**: FB, WB, SGD, ZFIN, RGD, XB

## Installation & Setup

### Prerequisites
```bash
# Install Python dependencies
uv sync

# Install browser automation dependencies (handled automatically by webdriver-manager)
# ChromeDriver is downloaded automatically
```

### Configuration
The framework automatically discovers test configurations from:
- `agr_blast_service_configuration/conf/` - AGR BLAST service configurations
- Auto-generated URLs: `https://blast.alliancegenome.org/blast/MOD/DB`

## Usage

### Phase 1: Discovery Mode
Discovers all checkboxes on BLAST interfaces and saves them to a temporary configuration file.

```bash
# Discover checkboxes for FB with visible browser (recommended for first run)
uv run python tests/ui/test_ui_comprehensive.py -m FB --discovery --no-headless

# Discover all MODs (runs headless by default)
uv run python tests/ui/test_ui_comprehensive.py --discovery

# Output: temp_checkbox_config.json containing all discovered checkboxes
```

**Discovery Features:**
- Runs Chrome visibly when using `--no-headless` (recommended for debugging)
- Discovers checkboxes with hierarchy and metadata
- Saves results to `temp_checkbox_config.json`
- Progress tracking for multiple URLs

### Phase 2: Systematic Testing Mode
Tests individual checkboxes systematically using the saved configuration.

```bash
# Test up to 10 checkboxes per URL from saved config
uv run python tests/ui/test_ui_comprehensive.py --systematic --max-checkboxes 10

# Test all discovered checkboxes (may take very long)
uv run python tests/ui/test_ui_comprehensive.py --systematic

# Generate markdown report
uv run python tests/ui/test_ui_comprehensive.py --systematic --markdown-report "reports/systematic_test.md"
```

**Systematic Testing Features:**
- Tests each checkbox individually for precise validation
- Uses saved checkbox configuration from discovery phase
- Detailed progress tracking per checkbox
- Comprehensive success/failure reporting

### Traditional Mode (Original Behavior)
Tests multiple checkboxes simultaneously on discovered URLs.

```bash
# Test specific MOD with protein sequences
uv run python tests/ui/test_ui_comprehensive.py -m FB --sequence-type prot

# Test with markdown report
uv run python tests/ui/test_ui_comprehensive.py -m WB --markdown-report "reports/wb_ui_test.md"

# Test all discovered MODs
uv run python tests/ui/test_ui_comprehensive.py
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-m, --mod` | Model organism database (FB, WB, SGD, ZFIN, RGD, XB) | All available |
| `--sequence-type` | Type of sequence to test (nucl, prot) | nucl |
| `--max-checkboxes` | Maximum checkboxes to test per URL | 3 |
| `--base-url` | Base URL for BLAST interface | https://blast.alliancegenome.org/blast |
| `--config-dir` | Path to AGR configuration directory | ../agr_blast_service_configuration/conf |
| `--markdown-report` | Generate markdown report (specify filename) | None |
| `--headless/--no-headless` | Run browser in headless mode | True |
| `--discovery` | **Discovery mode**: find and save checkboxes | False |
| `--systematic` | **Systematic mode**: test individual checkboxes | False |

## Framework Architecture

### Core Classes

#### `CheckboxDiscovery`
- **Purpose**: Discovers checkboxes and saves to temp config file
- **Key Methods**:
  - `discover_checkboxes()` - Finds all checkboxes on a page
  - `save_checkbox_config()` - Saves discovered data to JSON
  - `run_discovery()` - Orchestrates full discovery process

#### `SystematicTester`
- **Purpose**: Tests individual checkboxes from saved config
- **Key Methods**:
  - `load_checkbox_config()` - Loads saved checkbox data
  - `test_individual_checkbox()` - Tests a single checkbox
  - `run_systematic_tests()` - Tests all checkboxes systematically

#### `ConfigurationDiscovery`
- **Purpose**: Discovers URLs from AGR BLAST service configuration
- **Key Methods**:
  - `discover_configurations()` - Finds available MOD/environment combinations
  - Automatic URL generation based on MOD and environment

#### `UITester`
- **Purpose**: Core UI testing functionality (original comprehensive mode)
- **Key Methods**:
  - `run_blast_search()` - Executes BLAST searches with checkbox selection
  - `analyze_checkboxes()` - Discovers and categorizes checkboxes
  - `run_comprehensive_tests()` - Tests multiple URLs/checkboxes

### Test Sequences

The framework uses biologically conserved sequences to ensure cross-species compatibility:

```python
UNIVERSAL_SEQUENCES = {
    "nucl": {
        "FB": "18S rRNA partial sequence - highly conserved across eukaryotes",
        "WB": "18S rRNA partial sequence",
        "SGD": "18S rRNA partial sequence", 
        "ZFIN": "18S rRNA partial sequence",
        "RGD": "18S rRNA partial sequence",
        "XB": "18S rRNA partial sequence"
    },
    "prot": {
        "FB": "HSP70 protein sequence - highly conserved heat shock protein",
        # ... additional protein sequences
    }
}
```

## Output Files

### Temporary Configuration File
`temp_checkbox_config.json` - Created by discovery mode
```json
{
  "FB": {
    "FB2025_03": {
      "url": "https://blast.alliancegenome.org/blast/FB/FB2025_03",
      "checkboxes": [
        {
          "id": "databases[]",
          "text": "Acromyrmex echinatior",
          "value": "3b6d11eca2d07b10dc59723891a6c43d",
          "selected": false
        }
      ],
      "total_checkboxes": 195,
      "discovery_timestamp": "2025-09-10T14:30:00"
    }
  }
}
```

### Test Reports
Generated markdown reports include:
- Executive summary with success rates
- Detailed test results per URL/checkbox
- Screenshots for visual validation
- Performance metrics and runtime data
- Error details and debugging information

### Screenshots
- Saved to `test_output/ui_screenshots/`
- Captured at key test steps
- Named with timestamps and test identifiers
- Used for visual validation and debugging

## Best Practices

### Discovery Phase
1. **Use visible browser** (`--no-headless`) for first-time discovery to observe behavior
2. **Run discovery once** per test session - checkboxes don't change frequently
3. **Check temp config** before systematic testing to verify correct discovery

### Systematic Testing
1. **Limit checkboxes** (`--max-checkboxes`) for faster testing cycles
2. **Use headless mode** for faster execution in CI/CD
3. **Generate reports** for documentation and debugging

### Troubleshooting
1. **VPN Issues**: Disable VPN if experiencing DNS resolution errors
2. **Browser Issues**: Clear browser cache, update ChromeDriver
3. **Timeout Issues**: Increase timeout values for slow networks
4. **Checkbox Issues**: Re-run discovery if systematic testing fails

## Integration with CI/CD

```bash
# Quick validation (discovery + limited systematic testing)
uv run python tests/ui/test_ui_comprehensive.py -m FB --discovery --no-headless
uv run python tests/ui/test_ui_comprehensive.py --systematic --max-checkboxes 5

# Full regression testing
uv run python tests/ui/test_ui_comprehensive.py --discovery
uv run python tests/ui/test_ui_comprehensive.py --systematic --markdown-report "reports/full_ui_test.md"
```

## Performance Metrics

Recent test results:
- **764 checkboxes discovered** across FB environments
- **195 checkboxes per environment** (average)
- **13.65s average runtime** per BLAST search
- **100% success rate** in functional testing

## Comparison with Legacy Testing

| Feature | Legacy (`test_ui.py`) | New Framework (`test_ui_comprehensive.py`) |
|---------|----------------------|-------------------------------------------|
| Checkbox Discovery | Manual configuration | Automatic discovery + saved config |
| Testing Approach | Batch testing | Individual + batch options |
| URL Discovery | Manual | Automatic from AGR configs |
| Progress Tracking | Basic | Rich progress bars |
| Reporting | Basic | Comprehensive markdown |
| Configuration | Static JSON | Dynamic discovery |
| Browser Control | Limited | Full Chrome automation |

The new framework provides significant improvements in automation, reliability, and comprehensive testing coverage while maintaining backward compatibility through the traditional mode.