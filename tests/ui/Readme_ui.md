# BLAST Web Interface UI Testing

This tool provides automated UI testing capabilities for the BLAST web interface using Playwright. It allows testing of different Model Organism Databases (MODs) and their various BLAST configurations.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Test Output](#test-output)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Prerequisites

- Python 3.10 or higher
- uv (dependency management)
- A Playwright browser (installed below), or an installed Google Chrome

## Installation

1. Install the project with its dev extra, which includes Playwright:
```bash
uv sync --extra dev
```

2. Download the browser Playwright drives (once per machine; it goes in the
   user cache, not system-wide):
```bash
uv run playwright install chromium
```

   To use an already installed Google Chrome instead, pass
   `--browser-channel chrome` to `test_ui.py` (or set `PLAYWRIGHT_CHANNEL=chrome`
   for `test_ui_flow.py` and `simple_test.py`). No ChromeDriver is needed.

## Configuration

### Configuration File (config.json)

Create a `config.json` file with your test configurations:

```json
{
  "SGD": {
    "fungal": {
      "items": [
        "database1_id",
        "database2_id"
      ],
      "nucl": "ATGCATGC...",
      "prot": "MKLTMKLT..."
    }
  },
  "WB": {
    "nematode": {
      "items": [
        "database3_id",
        "database4_id"
      ],
      "nucl": "ATGCATGC...",
      "prot": "MKLTMKLT..."
    }
  }
}
```

## Usage

### Basic Command Structure

```bash
uv run python tests/ui/test_ui.py [OPTIONS]
```

### Required Options

- `-m, --mod`: Model organism database to test (e.g., SGD, WB)
- `-t, --type`: Database type (e.g., fungal, nematode)

### Optional Parameters

- `-s, --single_item`: Number of items to test (default: 1)
- `-M, --molecule`: Molecule type to test ('nucl' or 'prot', default: 'nucl')
- `-n, --number_of_items`: Number of random items to test
- `-c, --config`: Path to configuration file (default: config.json)
- `-o, --output`: Output directory for screenshots (default: output)
- `--comprehensive`: Step-by-step screenshots and a pass/fail summary
- `--headless/--no-headless`: Show the browser window (default: headless)
- `--base-url`: BLAST interface to test (default: https://blast.alliancegenome.org/blast)
- `--browser-channel`: Use an installed browser such as `chrome` instead of Playwright's Chromium

### Example Commands

1. Test a single database:
```bash
uv run python tests/ui/test_ui.py --mod SGD --type fungal
```

2. Test multiple databases with protein sequences:
```bash
uv run python tests/ui/test_ui.py --mod SGD --type fungal --molecule prot --number_of_items 3
```

3. Test with custom configuration:
```bash
uv run python tests/ui/test_ui.py --mod WB --type nematode --config custom_config.json
```

### Entry point

Declare a script in `pyproject.toml`:

```toml
[project.scripts]
test-ui = "test_ui:run_blast_tests"
```

Then run tests using:
```bash
uv run test-ui --mod SGD --type fungal
```

## Test Output

### Screenshots

Screenshots are saved in the output directory with the following structure:
```
output/
└── <MOD>/
    ├── database1_id.png
    ├── database2_id.png
    └── ...
```

### Console Output

The tool provides rich console output including:
- Progress indicators
- Success/failure messages
- Error details
- Screenshot locations

## Troubleshooting

### Common Issues

1. Browser Not Installed
```
Error: Executable doesn't exist ... Looks like Playwright was just installed or updated.
Solution: Run `uv run playwright install chromium`, or pass --browser-channel chrome
```

2. Configuration Not Found
```
Error: Invalid JSON configuration file
Solution: Ensure config.json exists and is properly formatted
```

3. Browser Launch Failed
```
Error: playwright._impl._errors.Error
Solution: Reinstall the browser with `uv run playwright install chromium`
```

### Debug Tips

1. Disable Headless Mode:
   - Pass `--no-headless` to watch the browser

2. Increase Wait Times:
   - Pass `wait_timeout` / `result_timeout` (seconds) to `BlastUITester`
   - Defaults are 30 seconds for pages and elements, 600 seconds for results

3. Check Screenshots:
   - Screenshots are saved even if tests fail
   - Compare failed test screenshots with successful ones

## Development

### Adding New Features

1. Clone the repository
2. Create a new branch
3. Install development dependencies:
```bash
uv sync --extra dev
```

### Code Style

Follow these guidelines:
- Use type hints
- Add docstrings for new functions
- Follow PEP 8 conventions
- Add appropriate error handling

### Running Tests

The testing script has its own pytest check, which runs it against a local
stand-in for the search page (skipped when no Playwright browser is installed):
```bash
uv run pytest tests/ui/test_ui_flow.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add or modify tests
4. Submit a pull request

### Project Structure

```
.
├── test_ui.py
├── config.json
├── pyproject.toml
├── uv.lock
├── README.md
└── output/
    └── <MOD>/
        └── screenshots/
```

## License

[Add your license information here]

## Authors

[Add author information here]