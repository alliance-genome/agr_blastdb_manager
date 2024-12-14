# NEEDS editing, and changing to poetry, etc


# BLAST Web Interface Load Testing

This document provides comprehensive instructions for running load tests against the BLAST web interface using Locust.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Test Scenarios](#test-scenarios)
- [Monitoring and Analysis](#monitoring-and-analysis)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Access to the BLAST web interface
- Basic understanding of BLAST searches and MOD databases

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install locust rich
```

3. Clone this repository or copy the locustfile.py to your working directory.

## Configuration

### Environment Variables

The following environment variables can be set:

- `BLAST_CONFIG`: Path to the configuration file (default: config.json)
- `LOCUST_MOD`: Model organism database to test
- `LOCUST_ENV`: Target environment (prod, dev, stage)

### Configuration File (config.json)

The configuration file should follow this structure:

```json
{
  "SGD": {
    "fungal": {
      "items": ["database1", "database2"],
      "nucl": "ATGC...",
      "prot": "MKLT..."
    }
  },
  "WB": {
    "nematode": {
      "items": ["database3", "database4"],
      "nucl": "ATGC...",
      "prot": "MKLT..."
    }
  }
}
```

## Running Tests

### Basic Usage

```bash
locust -f locustfile.py --host=https://blast.alliancegenome.org --mod=SGD --env=prod
```

### Common Options

- `-t RUNTIME`: Test duration (e.g., 1h, 30m)
- `-u NUM_USERS`: Number of concurrent users
- `-r SPAWN_RATE`: User spawn rate per second
- `--headless`: Run without web interface
- `--mod MOD`: Model organism database to test
- `--env ENV`: Target environment

### Example Commands

1. Run a 1-hour test with 10 users:
```bash
locust -f locustfile.py --host=https://blast.alliancegenome.org -t 1h -u 10 -r 1 --mod=SGD --env=prod --headless
```

2. Run with web interface for manual control:
```bash
locust -f locustfile.py --host=https://blast.alliancegenome.org --mod=SGD --env=prod
```

3. Distributed load testing (multiple workers):
```bash
# Master
locust -f locustfile.py --master --expect-workers=2

# Workers
locust -f locustfile.py --worker --master-host=localhost
```

## Test Scenarios

The load test implements two main scenarios:

1. Nucleotide BLAST Search (`@task(1)`)
   - Randomly selects a database type
   - Uses nucleotide sequences from config
   - Simulates form submission

2. Protein BLAST Search (`@task(1)`)
   - Randomly selects a database type
   - Uses protein sequences from config
   - Simulates form submission

Each test:
- Waits 1-5 seconds between requests
- Randomly selects databases
- Validates responses
- Reports errors and successes

## Monitoring and Analysis

### Web Interface

Access the web interface at http://localhost:8089 when running without --headless:

- Real-time statistics
- RPS (Requests Per Second)
- Response time distribution
- Error rates

### Console Output

The script provides rich console output:

- Test start/stop events
- Configuration details
- Error reporting
- Progress updates

### Generating Reports

Generate HTML reports after test completion:

```bash
locust -f locustfile.py --host=https://blast.alliancegenome.org --mod=SGD --env=prod --headless --html=report.html
```

## Troubleshooting

### Common Issues

1. Configuration Not Found
```
Error: No module named 'config.json'
Solution: Ensure config.json is in the same directory as locustfile.py
```

2. MOD Not Specified
```
Error: MOD must be specified via --mod or LOCUST_MOD
Solution: Add --mod parameter or set LOCUST_MOD environment variable
```

3. Connection Errors
```
Error: Connection refused
Solution: Verify host URL and network connectivity
```

### Debug Mode

Enable debug logging:

```bash
locust -f locustfile.py --host=https://blast.alliancegenome.org --mod=SGD --env=prod --loglevel=DEBUG
```

### Support

For issues or questions:
1. Check the error message in the console output
2. Verify configuration file format
3. Ensure all prerequisites are installed
4. Check network connectivity to the target host

## Contributing

To contribute:
1. Fork the repository
2. Create a feature branch
3. Add or modify tests
4. Submit a pull request

Please ensure all new code includes appropriate tests and documentation.