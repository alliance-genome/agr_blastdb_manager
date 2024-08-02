"""
create_blast_db.py

This script creates BLAST databases from FASTA files. It includes functions to download files from an FTP site,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in YAML and JSON formats.

Authors: Paulo Nuin, Adam Wright
Date: Started July 2023, Refactored [Current Date]
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
from typing import Dict, List, Optional, Tuple

import click
import wget
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TaskID,
                           TextColumn)
from rich.style import Style
from rich.table import Table
import subprocess
from utils import (check_md5sum, check_output, edit_fasta, get_ftp_file_size,
                   get_mod_from_json, run_command, s3_sync,
                   setup_logger, slack_message)

# Load environment variables
load_dotenv()

console = Console()

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
LOGGER = setup_logger("create_blast_db", "blast_db_creation.log")


def store_fasta_files(fasta_file: Path) -> None:
    """
    Store the downloaded FASTA files in a specific directory.

    Args:
        fasta_file (Path): The path to the FASTA file that needs to be stored.
    """
    date_to_add = datetime.now().strftime("%Y_%b_%d")
    original_files_store = Path(f"../data/database_{date_to_add}")
    original_files_store.mkdir(parents=True, exist_ok=True)

    console.log(
        Panel(
            f"Storing [bold]{fasta_file}[/bold] in [cyan]{original_files_store}[/cyan]",
            title="File Storage",
            border_style="green",
        )
    )
    copyfile(fasta_file, original_files_store / fasta_file.name)
    LOGGER.info(f"Stored {fasta_file} in {original_files_store}")


def get_files_ftp(
    fasta_uri: str, md5sum: str, progress: Progress, task: TaskID
) -> bool:
    """
    Download files from an FTP site.

    Args:
        fasta_uri (str): The URI of the FASTA file that needs to be downloaded.
        md5sum (str): The MD5 checksum of the file.
        progress (Progress): Rich progress bar object.
        task (TaskID): Task ID for the progress bar.

    Returns:
        bool: True if the file was successfully downloaded and the MD5 checksum matches, False otherwise.
    """
    LOGGER.info(f"Downloading {fasta_uri}")
    progress.update(task, description=f"Downloading {Path(fasta_uri).name}")

    today_date = datetime.now().strftime("%Y_%b_%d")
    fasta_file = Path(f"../data/{Path(fasta_uri).name}")

    if (Path(f"../data/database_{today_date}") / fasta_file.name).exists():
        progress.update(
            task, description=f"{fasta_file.name} already processed", completed=100
        )
        LOGGER.info(f"{fasta_file} already processed")
        return False

    try:
        file_size = get_ftp_file_size(fasta_uri)
        if file_size == 0:
            progress.update(
                task,
                description=f"Failed to get file size for {fasta_uri}",
                completed=100,
            )
            LOGGER.error(f"Failed to get file size for {fasta_uri}")
            return False

        wget.download(fasta_uri, str(fasta_file))
        store_fasta_files(fasta_file)

        if check_md5sum(fasta_file, md5sum):
            progress.update(task, completed=100)
            return True
        else:
            progress.update(task, description="MD5sums do not match", completed=100)
            LOGGER.error("MD5sums do not match")
            return False
    except Exception as e:
        progress.update(
            task, description=f"Error downloading {fasta_uri}: {e}", completed=100
        )
        LOGGER.error(f"Error downloading {fasta_uri}: {e}")
        return False


def create_db_structure(
    environment: str, mod: str, config_entry: Dict[str, str]
) -> Tuple[Path, Path]:
    """
    Create the database and folder structure for storing the downloaded FASTA files.

    Args:
        environment (str): The current environment (like dev, prod, etc.).
        mod (str): The model organism.
        config_entry (Dict[str, str]): A dictionary containing the configuration details.

    Returns:
        Tuple[Path, Path]: Paths to the database and config directories.
    """
    LOGGER.info("Creating database structure")

    blast_title = config_entry["blast_title"]
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)

    if "seqcol" in config_entry:
        LOGGER.info("seqcol found in config file")
        db_path = Path(
            f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/"
        )
    else:
        LOGGER.info("seqcol not found in config file")
        db_path = Path(
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/{sanitized_blast_title}/"
        )

    config_path = Path(f"../data/config/{mod}/{environment}")

    db_path.mkdir(parents=True, exist_ok=True)
    config_path.mkdir(parents=True, exist_ok=True)

    console.log(
        Panel(
            f"Created directory: [cyan]{db_path}[/cyan]",
            title="Database Structure",
            border_style="blue",
        )
    )
    LOGGER.info(f"Directory {db_path} created")

    return db_path, config_path


from utils import needs_parse_id, run_command


def run_makeblastdb(
    config_entry: Dict[str, str], output_dir: Path, progress: Progress, task: TaskID
) -> bool:
    fasta_file = Path(config_entry["uri"]).name

    LOGGER.info(f"Running makeblastdb for {fasta_file}")
    progress.update(task, description=f"Running makeblastdb for {fasta_file}")

    SLACK_MESSAGES.append(
        {
            "title": "Running makeblastdb",
            "text": fasta_file,
            "color": "#36a64f",
        }
    )

    gzipped_fasta = Path(f"../data/{fasta_file}")
    unzipped_fasta = gzipped_fasta.with_suffix("")

    if not unzipped_fasta.exists():
        success, output = run_command(["gunzip", "-k", "-v", str(gzipped_fasta)])
        if not success:
            progress.update(
                task,
                description=f"Error unzipping {fasta_file}: {output}",
                completed=100,
            )
            LOGGER.error(f"Error unzipping {fasta_file}: {output}")
            return False
        LOGGER.info(f"Unzipping {fasta_file}: done")
        progress.update(task, advance=10)

    # Check if parse_id is needed (on the gzipped file)
    parse_id_needed = needs_parse_id(gzipped_fasta)

    sanitized_blast_title = re.sub(r"\W+", "_", config_entry["blast_title"])

    makeblast_command = [
        "makeblastdb",
        "-in",
        str(unzipped_fasta),
        "-dbtype",
        config_entry["seqtype"],
        "-title",
        sanitized_blast_title,
        "-out",
        str(output_dir / unzipped_fasta.name.replace(".fasta", ".db")),
        "-taxid",
        config_entry["taxon_id"].replace("NCBITaxon:", ""),
    ]

    if parse_id_needed:
        makeblast_command.extend(["-parse_seqids"])
        LOGGER.info("Added -parse_seqids option to makeblastdb command")

    LOGGER.info(f"Running makeblastdb: {' '.join(makeblast_command)}")
    progress.update(task, description=f"Running makeblastdb command", advance=10)

    success, output = run_command(makeblast_command)
    if success:
        progress.update(task, description="Makeblastdb: done", completed=100)
        SLACK_MESSAGES.append(
            {
                "title": "Makeblastdb completed",
                "text": fasta_file,
                "color": "#36a64f",
            }
        )
        LOGGER.info("Makeblastdb: done")

        unzipped_fasta.unlink()
        LOGGER.info(f"Removed {unzipped_fasta}")
        return True
    else:
        progress.update(
            task, description=f"Error running makeblastdb: {output}", completed=100
        )
        SLACK_MESSAGES.append(
            {
                "title": "Error running makeblastdb",
                "text": fasta_file,
                "color": "#8D2707",
            }
        )
        LOGGER.error(f"Error running makeblastdb: {output}")
        rmtree(output_dir)
        return False


def process_yaml(config_yaml: Path) -> bool:
    """
    Process a YAML file containing configuration details for multiple data providers.

    Args:
        config_yaml (Path): The path to the YAML file that needs to be processed.

    Returns:
        bool: True if the YAML file was successfully processed, False otherwise.
    """
    try:
        with open(config_yaml, "r") as file:
            config = yaml.safe_load(file)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            main_task = progress.add_task(
                "[green]Processing YAML config", total=len(config["data_providers"])
            )

            for provider in config["data_providers"]:
                provider_task = progress.add_task(
                    f"Processing {provider['name']}",
                    total=len(provider["environments"]),
                )

                for environment in provider["environments"]:
                    json_file = (
                        config_yaml.parent
                        / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
                    )
                    process_json(json_file, environment, provider["name"], progress)
                    progress.update(provider_task, advance=1)

                progress.update(main_task, advance=1)

        return True
    except Exception as e:
        LOGGER.error(f"Error processing YAML file: {e}")
        console.print(
            Panel(
                f"[bold red]Error processing YAML file:[/bold red] {e}",
                title="Error",
                border_style="red",
            )
        )
        return False


def process_json(
    json_file: Path,
    environment: str,
    mod: Optional[str] = None,
    parent_progress: Optional[Progress] = None,
) -> bool:
    """
    Process a JSON file containing configuration details for a specific data provider.

    Args:
        json_file (Path): The path to the JSON file that needs to be processed.
        environment (str): The current environment (like dev, prod, etc.).
        mod (Optional[str]): The model organism.
        parent_progress (Optional[Progress]): Parent progress bar for nested progress.

    Returns:
        bool: True if the JSON file was successfully processed, False otherwise.
    """
    console.print(
        Panel(
            f"Processing JSON file: [cyan]{json_file}[/cyan]",
            title="JSON Processing",
            border_style="yellow",
        )
    )

    if mod is None:
        mod = get_mod_from_json(json_file)

    if not mod:
        LOGGER.error("Unable to determine MOD")
        console.print(
            "[bold red]Error:[/bold red] Unable to determine MOD", style="red"
        )
        return False

    try:
        with open(json_file, "r") as file:
            db_coordinates = json.load(file)

        progress = parent_progress or Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

        with progress:
            main_task = progress.add_task(
                f"[green]Processing {mod} - {environment}",
                total=len(db_coordinates["data"]),
            )

            for entry in db_coordinates["data"]:
                task = progress.add_task(f"Processing {entry['uri']}", total=100)
                if get_files_ftp(entry["uri"], entry["md5sum"], progress, task):
                    output_dir, config_dir = create_db_structure(
                        environment, mod, entry
                    )
                    copyfile(json_file, config_dir / "environment.json")

                    if output_dir.exists():
                        if not run_makeblastdb(entry, output_dir, progress, task):
                            LOGGER.error(
                                f"Failed to create BLAST database for {entry['uri']}"
                            )
                            progress.update(
                                main_task,
                                description=f"[red]Failed: {entry['uri']}[/red]",
                                advance=1,
                            )
                            return False
                progress.update(main_task, advance=1)

        return True
    except Exception as e:
        LOGGER.error(f"Error processing JSON file: {e}")
        console.print(
            Panel(
                f"[bold red]Error processing JSON file:[/bold red] {e}",
                title="Error",
                border_style="red",
            )
        )
        return False


@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option(
    "-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False
)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
def create_dbs(
    config_yaml, input_json, environment, mod, skip_efs_sync, update_slack, sync_s3
):
    """
    Main function that runs the pipeline for processing the configuration files and creating the BLAST databases.
    """
    start_time = time.time()
    LOGGER.info("Starting create_dbs function")
    LOGGER.info(
        f"Arguments: config_yaml={config_yaml}, input_json={input_json}, environment={environment}, "
        f"mod={mod}, skip_efs_sync={skip_efs_sync}, update_slack={update_slack}, sync_s3={sync_s3}"
    )

    if len(sys.argv) == 1:
        LOGGER.info("No arguments provided. Displaying help message.")
        click.echo(create_dbs.get_help(ctx=None))
        return

    console.print(
        Panel(
            "BLAST Database Creation Tool", title="Welcome", border_style="bold magenta"
        )
    )

    try:
        if config_yaml:
            LOGGER.info(f"Processing YAML file: {config_yaml}")
            success = process_yaml(Path(config_yaml))
            LOGGER.info(f"YAML processing {'successful' if success else 'failed'}")
        elif input_json:
            LOGGER.info(f"Processing JSON file: {input_json}")
            success = process_json(Path(input_json), environment, mod)
            LOGGER.info(f"JSON processing {'successful' if success else 'failed'}")
        else:
            LOGGER.error("Neither config_yaml nor input_json provided")
            console.print(
                "[bold red]Error:[/bold red] Either config_yaml or input_json must be provided",
                style="red",
            )
            return

        if not success:
            LOGGER.error("Processing failed. Exiting.")
            return

        if update_slack:
            LOGGER.info("Updating Slack")
            with console.status("[bold green]Updating Slack...[/bold green]"):
                slack_success = slack_message(SLACK_MESSAGES)
            LOGGER.info(f"Slack update {'successful' if slack_success else 'failed'}")
            console.print(
                Panel(
                    "Slack updated successfully"
                    if slack_success
                    else "Slack update failed",
                    title="Slack Update",
                    border_style="green" if slack_success else "red",
                )
            )

        if sync_s3:
            LOGGER.info("Syncing to S3")
            with console.status("[bold blue]Syncing to S3...[/bold blue]"):
                s3_success = s3_sync(Path("../data"), skip_efs_sync)
            LOGGER.info(f"S3 sync {'successful' if s3_success else 'failed'}")
            console.print(
                Panel(
                    "S3 sync completed successfully"
                    if s3_success
                    else "S3 sync failed",
                    title="S3 Sync",
                    border_style="blue" if s3_success else "red",
                )
            )

        # Display summary
        table = Table(title="BLAST Database Creation Summary")
        table.add_column("Task", style="cyan")
        table.add_column("Status", style="magenta")

        table.add_row("Configuration Processing", "Completed")
        table.add_row("Slack Update", "Completed" if update_slack else "Skipped")
        table.add_row("S3 Sync", "Completed" if sync_s3 else "Skipped")

        console.print(table)

    except Exception as e:
        LOGGER.error(f"Unhandled exception in create_dbs: {str(e)}", exc_info=True)
        console.print(
            Panel(
                f"[bold red]Error in create_dbs:[/bold red] {str(e)}",
                title="Error",
                border_style="red",
            )
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        LOGGER.info(f"create_dbs function completed in {duration:.2f} seconds")
        console.print(f"Total execution time: {duration:.2f} seconds")


if __name__ == "__main__":
    create_dbs()