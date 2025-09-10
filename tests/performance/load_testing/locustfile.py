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
from locust.exception import StopUser
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
        self.successful_requests = 0
        self.failed_requests = 0
        self.user_id = id(self)

        self.mod = self.host.split('/')[-1] if self.host.endswith('/') else ''
        self.blast_test = None
        self.session_data = {}

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

    @task(3)
    def nucleotide_blast(self):
        """Simulate nucleotide BLAST search."""
        if not self.blast_test:
            return

        db_type = random.choice(list(self.blast_test.database_items.keys()))
        database = self.blast_test.get_random_database(db_type)
        sequence = self.blast_test.get_random_sequence(db_type, 'nucl')

        if database and sequence:
            self._perform_blast(db_type, database, sequence, 'nucleotide')

    @task(2)
    def protein_blast(self):
        """Simulate protein BLAST search."""
        if not self.blast_test:
            return

        db_type = random.choice(list(self.blast_test.database_items.keys()))
        database = self.blast_test.get_random_database(db_type)
        sequence = self.blast_test.get_random_sequence(db_type, 'prot')

        if database and sequence:
            self._perform_blast(db_type, database, sequence, 'protein')

    @task(1)
    def browse_homepage(self):
        """Simulate browsing the BLAST homepage."""
        try:
            with self.client.get(f"/blast/{self.mod}", catch_response=True, name="homepage") as response:
                if response.status_code == 200:
                    response.success()
                    self.successful_requests += 1
                else:
                    response.failure(f"Homepage load failed: {response.status_code}")
                    self.failed_requests += 1
        except Exception as e:
            self.failed_requests += 1
            events.request_failure.fire(
                request_type="GET",
                name="homepage",
                response_time=0,
                exception=e
            )

    @task(1)
    def check_database_availability(self):
        """Check if databases are available."""
        if not self.blast_test:
            return
            
        db_type = random.choice(list(self.blast_test.database_items.keys()))
        try:
            with self.client.get(f"/blast/{self.mod}/{db_type}", catch_response=True, 
                               name="database_availability") as response:
                if response.status_code == 200:
                    # Check if database list is present
                    if any(db in response.text for db in self.blast_test.database_items[db_type]):
                        response.success()
                        self.successful_requests += 1
                    else:
                        response.failure("Database list not found")
                        self.failed_requests += 1
                else:
                    response.failure(f"Database page load failed: {response.status_code}")
                    self.failed_requests += 1
        except Exception as e:
            self.failed_requests += 1
            events.request_failure.fire(
                request_type="GET",
                name="database_availability",
                response_time=0,
                exception=e
            )

    def _perform_blast(self, db_type: str, database: str, sequence: str, search_type: str):
        """
        Perform a BLAST search request.

        Args:
            db_type: Type of database to search
            database: Specific database identifier
            sequence: Query sequence
            search_type: Type of search (nucleotide/protein)
        """
        request_name = f"blast_search_{search_type}"
        start_time = time.time()
        
        try:
            # Submit BLAST search
            with self.client.post(
                    f"/blast/{self.mod}/{db_type}",
                    data={
                        "database": database,
                        "sequence": sequence,
                        "submit": "BLAST",
                        "program": "blastn" if search_type == "nucleotide" else "blastp"
                    },
                    catch_response=True,
                    name=request_name,
                    timeout=30
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    # Check if response contains expected elements
                    if "results" in response.text.lower() or "hits" in response.text.lower():
                        response.success()
                        self.successful_requests += 1
                        
                        # Store session data for follow-up requests
                        self.session_data[f"last_{search_type}_search"] = {
                            "database": database,
                            "sequence": sequence[:50] + "..." if len(sequence) > 50 else sequence,
                            "response_time": response_time
                        }
                    else:
                        response.failure("No search results found in response")
                        self.failed_requests += 1
                else:
                    response.failure(f"BLAST search failed: {response.status_code}")
                    self.failed_requests += 1

        except Exception as e:
            self.failed_requests += 1
            console.log(f"[red]Error performing BLAST search: {str(e)}[/red]")
            events.request_failure.fire(
                request_type="POST",
                name=request_name,
                response_time=(time.time() - start_time) * 1000,
                exception=e
            )

    def on_stop(self):
        """Called when user stops - log session summary."""
        total_requests = self.successful_requests + self.failed_requests
        if total_requests > 0:
            success_rate = (self.successful_requests / total_requests) * 100
            console.log(f"[blue]User {self.user_id} session summary:[/blue]")
            console.log(f"Total requests: {total_requests}")
            console.log(f"Success rate: {success_rate:.1f}%")
            console.log(f"Session data keys: {list(self.session_data.keys())}")


# Global test statistics
test_stats = {
    "start_time": None,
    "end_time": None,
    "total_users": 0,
    "peak_users": 0,
    "total_requests": 0,
    "total_failures": 0,
    "request_types": {},
    "response_times": []
}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test configuration at start."""
    global test_stats
    test_stats["start_time"] = time.time()
    
    console.log("[green]Starting BLAST load test[/green]")
    console.log(f"MOD: {os.getenv('LOCUST_MOD', 'Not specified')}")
    console.log(f"Environment: {os.getenv('LOCUST_ENV', 'prod')}")
    console.log(f"Host: {environment.host}")
    console.log(f"Users: {environment.parsed_options.num_users}")
    console.log(f"Spawn rate: {environment.parsed_options.spawn_rate}")
    
    if environment.parsed_options.run_time:
        console.log(f"Run time: {environment.parsed_options.run_time}")


@events.user_add.add_listener
def on_user_add(environment, **kwargs):
    """Track user additions."""
    global test_stats
    test_stats["total_users"] += 1
    test_stats["peak_users"] = max(test_stats["peak_users"], test_stats["total_users"])


@events.user_remove.add_listener
def on_user_remove(environment, **kwargs):
    """Track user removals."""
    global test_stats
    test_stats["total_users"] -= 1


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track individual requests."""
    global test_stats
    test_stats["total_requests"] += 1
    test_stats["response_times"].append(response_time)
    
    if name not in test_stats["request_types"]:
        test_stats["request_types"][name] = {"count": 0, "failures": 0, "total_time": 0}
    
    test_stats["request_types"][name]["count"] += 1
    test_stats["request_types"][name]["total_time"] += response_time
    
    if exception:
        test_stats["total_failures"] += 1
        test_stats["request_types"][name]["failures"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate comprehensive test completion report."""
    global test_stats
    test_stats["end_time"] = time.time()
    
    duration = test_stats["end_time"] - test_stats["start_time"]
    
    console.log("[green]BLAST load test completed[/green]")
    console.log(f"\n[bold]Test Summary Report:[/bold]")
    console.log(f"Duration: {duration:.1f} seconds")
    console.log(f"Peak concurrent users: {test_stats['peak_users']}")
    console.log(f"Total requests: {test_stats['total_requests']}")
    console.log(f"Total failures: {test_stats['total_failures']}")
    
    if test_stats["total_requests"] > 0:
        failure_rate = (test_stats["total_failures"] / test_stats["total_requests"]) * 100
        console.log(f"Failure rate: {failure_rate:.2f}%")
        
        # Request rate
        requests_per_second = test_stats["total_requests"] / duration
        console.log(f"Requests per second: {requests_per_second:.2f}")
        
        # Response time statistics
        if test_stats["response_times"]:
            response_times = sorted(test_stats["response_times"])
            count = len(response_times)
            
            avg_response_time = sum(response_times) / count
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Percentiles
            p50 = response_times[int(count * 0.5)]
            p95 = response_times[int(count * 0.95)]
            p99 = response_times[int(count * 0.99)]
            
            console.log(f"\n[bold]Response Time Statistics (ms):[/bold]")
            console.log(f"Average: {avg_response_time:.0f}")
            console.log(f"Minimum: {min_response_time:.0f}")
            console.log(f"Maximum: {max_response_time:.0f}")
            console.log(f"50th percentile: {p50:.0f}")
            console.log(f"95th percentile: {p95:.0f}")
            console.log(f"99th percentile: {p99:.0f}")
        
        # Request type breakdown
        console.log(f"\n[bold]Request Type Breakdown:[/bold]")
        for request_type, stats in test_stats["request_types"].items():
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            failure_rate = (stats["failures"] / stats["count"]) * 100 if stats["count"] > 0 else 0
            
            console.log(f"{request_type}:")
            console.log(f"  Count: {stats['count']}")
            console.log(f"  Failures: {stats['failures']} ({failure_rate:.1f}%)")
            console.log(f"  Avg response time: {avg_time:.0f}ms")
    
    # Save detailed report to file
    save_detailed_report()


def save_detailed_report():
    """Save detailed test report to JSON file."""
    import json
    from datetime import datetime
    
    report_data = {
        "test_info": {
            "mod": os.getenv('LOCUST_MOD', 'Not specified'),
            "environment": os.getenv('LOCUST_ENV', 'prod'),
            "start_time": datetime.fromtimestamp(test_stats["start_time"]).isoformat(),
            "end_time": datetime.fromtimestamp(test_stats["end_time"]).isoformat(),
            "duration_seconds": test_stats["end_time"] - test_stats["start_time"]
        },
        "statistics": test_stats,
        "performance_metrics": {
            "requests_per_second": test_stats["total_requests"] / (test_stats["end_time"] - test_stats["start_time"]) if test_stats["total_requests"] > 0 else 0,
            "failure_rate_percent": (test_stats["total_failures"] / test_stats["total_requests"]) * 100 if test_stats["total_requests"] > 0 else 0
        }
    }
    
    # Calculate response time percentiles if available
    if test_stats["response_times"]:
        sorted_times = sorted(test_stats["response_times"])
        count = len(sorted_times)
        
        report_data["response_times"] = {
            "average": sum(sorted_times) / count,
            "min": min(sorted_times),
            "max": max(sorted_times),
            "percentile_50": sorted_times[int(count * 0.5)],
            "percentile_95": sorted_times[int(count * 0.95)],
            "percentile_99": sorted_times[int(count * 0.99)]
        }
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"load_test_report_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        console.log(f"[green]Detailed report saved to: {filename}[/green]")
    except Exception as e:
        console.log(f"[red]Error saving report: {str(e)}[/red]")