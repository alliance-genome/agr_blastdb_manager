# BLAST Web Interface UI Testing

This tool provides automated UI testing capabilities for the BLAST web interface using Selenium WebDriver. It allows testing of different Model Organism Databases (MODs) and their various BLAST configurations.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Test Output](#test-output)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Prerequisites

- Python 3.8 or higher
- Poetry (dependency management)
- Chrome or Chromium browser
- ChromeDriver matching your Chrome version

## Installation

1. Ensure Poetry is installed on your system. If not, install it following the [official instructions](https://python-poetry.org/docs/#installation).

2. Clone this repository and navigate to the project directory:
```bash
git clone <repository-url>
cd <project-directory>
```

3. Install dependencies using Poetry:
```bash
poetry install
```

4. Add the required dependencies to your project:
```bash
poetry add selenium rich click
```

Your `pyproject.toml` should include these dependencies:
```toml
[tool.poetry.dependencies]
python = "^3.8"
selenium = "^4.9.0"
rich = "^13.3.5"
click = "^8.1.3"

[tool.poetry.dev-dependencies]
# Add any development dependencies here
```

## Configuration

### ChromeDriver Setup

1. Download ChromeDriver that matches your Chrome version from [ChromeDriver Downloads](https://sites.google.com/chromium.org/driver/)
2. Add ChromeDriver to your system PATH

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
poetry run python test_ui.py [OPTIONS]
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

### Example Commands

1. Test a single database:
```bash
poetry run python test_ui.py --mod SGD --type fungal
```

2. Test multiple databases with protein sequences:
```bash
poetry run python test_ui.py --mod SGD --type fungal --molecule prot --number_of_items 3
```

3. Test with custom configuration:
```bash
poetry run python test_ui.py --mod WB --type nematode --config custom_config.json
```

### Poetry Scripts

Add these convenient scripts to your `pyproject.toml`:

```toml
[tool.poetry.scripts]
test-ui = "test_ui:run_blast_tests"
```

Then run tests using:
```bash
poetry run test-ui --mod SGD --type fungal
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

1. ChromeDriver Version Mismatch
```
Error: SessionNotCreatedException
Solution: Update ChromeDriver to match your Chrome version
```

2. Configuration Not Found
```
Error: Invalid JSON configuration file
Solution: Ensure config.json exists and is properly formatted
```

3. Browser Launch Failed
```
Error: WebDriverException
Solution: Check Chrome installation and ChromeDriver path
```

### Debug Tips

1. Disable Headless Mode:
   - Edit `setup_browser()` in the code
   - Remove the `--headless` option to see browser automation in action

2. Increase Wait Times:
   - Adjust the `WebDriverWait` timeout values for slower connections
   - Default wait is 10 seconds for elements, 600 seconds for results

3. Check Screenshots:
   - Screenshots are saved even if tests fail
   - Compare failed test screenshots with successful ones

## Development

### Adding New Features

1. Clone the repository
2. Create a new branch
3. Install development dependencies:
```bash
poetry install --with dev
```

### Code Style

Follow these guidelines:
- Use type hints
- Add docstrings for new functions
- Follow PEP 8 conventions
- Add appropriate error handling

### Running Tests

If you add tests for the testing script itself:
```bash
poetry run pytest tests/
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
├── poetry.lock
├── README.md
└── output/
    └── <MOD>/
        └── screenshots/
```

## License

[Add your license information here]

## Authors

[Add author information here]