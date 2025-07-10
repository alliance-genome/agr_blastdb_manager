"""
locustfile.py

This module implements load testing for the BLAST web interface using Locust.
It supports testing different MODs and environments, using sequences from a
configuration file.

Usage:
    locust -f locustfile.py --host=https://blast.alliancegenome.org -t 1h -u 10 -r 1
    --mod=SGD --env=prod --headless

Environment variables:
    BLAST_CONFIG: Path to the configuration file (default: config.json)
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional

from locust import HttpUser, between, events, task
from rich.console import Console

console = Console()


class BlastLoadTest:
    """
    Handles configuration and data management for BLAST load testing.
    """

    def __init__(self, mod: str, environment: str = "prod"):
        self.mod = mod
        self.environment = environment
        self.config = self._load_config()
        self.sequences = self._prepare_sequences()
        self.database_items = self._prepare_database_items()

    def _load_config(self) -> Dict:
        """Load and validate the configuration file."""
        config_path = os.getenv("BLAST_CONFIG", "config.json")
        try:
            with open(config_path) as f:
                config = json.load(f)

            if self.mod not in config:
                raise ValueError(f"MOD '{self.mod}' not found in configuration")

            return config[self.mod]
        except Exception as e:
            console.log(f"[red]Error loading configuration: {str(e)}[/red]")
            raise

    def _prepare_sequences(self) -> Dict[str, str]:
        """Prepare test sequences for each database type."""
        sequences = {}
        for db_type, data in self.config.items():
            if isinstance(data, dict):
                sequences[db_type] = {
                    'nucl': data.get('nucl', ''),
                    'prot': data.get('prot', '')
                }
        return sequences

    def _prepare_database_items(self) -> Dict[str, List[str]]:
        """Prepare database items for each type."""
        items = {}
        for db_type, data in self.config.items():
            if isinstance(data, dict) and 'items' in data:
                items[db_type] = data['items']
        return items

    def get_random_sequence(self, db_type: str, molecule_type: str = 'nucl') -> str:
        """Get a random sequence for the specified database type."""
        if db_type in self.sequences:
            return self.sequences[db_type].get(molecule_type, '')
        return ''

    def get_random_database(self, db_type: str) -> Optional[str]:
        """Get a random database item for the specified type."""
        if db_type in self.database_items and self.database_items[db_type]:
            return random.choice(self.database_items[db_type])
        return None


class BlastUser(HttpUser):
    """
    Simulates user behavior for load testing the BLAST web interface.
    """

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mod = self.host.split('/')[-1] if self.host.endswith('/') else ''
        self.blast_test = None

    def on_start(self):
        """Initialize the test configuration when user starts."""
        try:
            # Get MOD from command line or environment
            self.mod = os.getenv("LOCUST_MOD", self.mod)
            if not self.mod:
                raise ValueError("MOD must be specified via --mod or LOCUST_MOD")

            self.environment = os.getenv("LOCUST_ENV", "prod")
            self.blast_test = BlastLoadTest(self.mod, self.environment)

        except Exception as e:
            console.log(f"[red]Error initializing test user: {str(e)}[/red]")
            raise

    @task(1)
    def nucleotide_blast(self):
        """Simulate nucleotide BLAST search."""
        if not self.blast_test:
            return

        db_type = random.choice(list(self.blast_test.database_items.keys()))
        database = self.blast_test.get_random_database(db_type)
        sequence = self.blast_test.get_random_sequence(db_type, 'nucl')

        if database and sequence:
            self._perform_blast(db_type, database, sequence)

    @task(1)
    def protein_blast(self):
        """Simulate protein BLAST search."""
        if not self.blast_test:
            return

        db_type = random.choice(list(self.blast_test.database_items.keys()))
        database = self.blast_test.get_random_database(db_type)
        sequence = self.blast_test.get_random_sequence(db_type, 'prot')

        if database and sequence:
            self._perform_blast(db_type, database, sequence)

    def _perform_blast(self, db_type: str, database: str, sequence: str):
        """
        Perform a BLAST search request.

        Args:
            db_type: Type of database to search
            database: Specific database identifier
            sequence: Query sequence
        """
        try:
            # Submit BLAST search
            with self.client.post(
                    f"/blast/{self.mod}/{db_type}",
                    data={
                        "database": database,
                        "sequence": sequence,
                        "submit": "BLAST"
                    },
                    catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"BLAST search failed: {response.status_code}")

        except Exception as e:
            console.log(f"[red]Error performing BLAST search: {str(e)}[/red]")
            events.request_failure.fire(
                request_type="POST",
                name="blast_search",
                response_time=0,
                exception=e
            )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test configuration at start."""
    console.log("[green]Starting BLAST load test[/green]")
    console.log(f"MOD: {os.getenv('LOCUST_MOD', 'Not specified')}")
    console.log(f"Environment: {os.getenv('LOCUST_ENV', 'prod')}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion."""
    console.log("[green]BLAST load test completed[/green]")