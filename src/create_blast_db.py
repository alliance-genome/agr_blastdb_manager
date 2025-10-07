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
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import copyfile, copytree, rmtree
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

from utils import (check_md5sum, check_output, edit_fasta, get_ftp_file_size,
                   get_mod_from_json, needs_parse_id, run_command, s3_sync,
                   setup_logger, slack_message)

# Load environment variables
load_dotenv()

console = Console()

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
LOGGER = None  # Will be initialized in create_dbs()


def store_fasta_files(fasta_file: Path, skip_local_storage: bool = False) -> None:
    """
    Store the downloaded FASTA files in a specific directory.

    Args:
        fasta_file (Path): The path to the FASTA file that needs to be stored.
        skip_local_storage (bool): If True, skip storing the file locally.
    """
    if skip_local_storage:
        LOGGER.info(f"Skipping local storage for {fasta_file} (--skip-local-storage enabled)")
        return

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


def copy_to_sequenceserver(mod: str, environment: str) -> bool:
    """
    Copy BLAST databases and config files to /var/sequenceserver-data/.

    Args:
        mod (str): The model organism.
        environment (str): The environment name.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        source_blast = Path(f"../data/blast/{mod}/{environment}")
        source_config = Path(f"../data/config/{mod}/{environment}")

        dest_blast = Path(f"/var/sequenceserver-data/blast/{mod}/{environment}")
        dest_config = Path(f"/var/sequenceserver-data/config/{mod}/{environment}")

        # Check if source directories exist
        if not source_blast.exists():
            LOGGER.warning(f"Source BLAST directory does not exist: {source_blast}")
            return False

        if not source_config.exists():
            LOGGER.warning(f"Source config directory does not exist: {source_config}")
            return False

        # Remove existing destination directories if they exist
        if dest_blast.exists():
            LOGGER.info(f"Removing existing BLAST directory: {dest_blast}")
            rmtree(dest_blast)

        if dest_config.exists():
            LOGGER.info(f"Removing existing config directory: {dest_config}")
            rmtree(dest_config)

        # Copy directories
        LOGGER.info(f"Copying BLAST databases: {source_blast} -> {dest_blast}")
        copytree(source_blast, dest_blast)

        LOGGER.info(f"Copying config files: {source_config} -> {dest_config}")
        copytree(source_config, dest_config)

        console.log(
            Panel(
                f"Successfully copied to SequenceServer:\n"
                f"  BLAST: [cyan]{dest_blast}[/cyan]\n"
                f"  Config: [cyan]{dest_config}[/cyan]",
                title="SequenceServer Sync",
                border_style="green",
            )
        )

        LOGGER.info("Successfully copied files to /var/sequenceserver-data/")
        return True

    except Exception as e:
        LOGGER.error(f"Error copying to sequenceserver-data: {str(e)}", exc_info=True)
        console.print(
            Panel(
                f"[bold red]Error:[/bold red] Failed to copy to SequenceServer\n{str(e)}",
                title="Copy Error",
                border_style="red",
            )
        )
        return False


def bar_custom(current, total, width=80):
    if current % (total / 100) == 0:
        LOGGER.info(f"Downloading: {current/total*100:.1f}% complete")


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

    # Sanitize blast_title for use in directory paths
    blast_title = config_entry["blast_title"]
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)

    # SGD main (non-fungal) uses seqcol_type for top-level organization
    if "seqcol_type" in config_entry:
        LOGGER.info("seqcol_type found in config file (SGD main)")
        seqcol_type = config_entry['seqcol_type']
        sanitized_seqcol_type = re.sub(r"\W+", "_", seqcol_type)
        db_path = Path(
            f"../data/blast/{mod}/{environment}/databases/{sanitized_seqcol_type}/{sanitized_blast_title}/"
        )
    # Legacy seqcol field (used by some MODs)
    elif "seqcol" in config_entry:
        LOGGER.info("seqcol found in config file")
        db_path = Path(
            f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/"
        )
    # Default: use genus/species organization
    else:
        LOGGER.info("Using genus/species organization")
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


def get_files_ftp(fasta_uri: str, md5sum: str, skip_local_storage: bool = False) -> bool:
    LOGGER.info(f"Downloading {fasta_uri}")

    today_date = datetime.now().strftime("%Y_%b_%d")
    fasta_file = Path(f"../data/{Path(fasta_uri).name}")

    # Only check for already-processed files if we're storing locally
    if not skip_local_storage and (Path(f"../data/database_{today_date}") / fasta_file.name).exists():
        LOGGER.info(f"{fasta_file} already processed")
        return False

    try:
        file_size = get_ftp_file_size(fasta_uri)
        if file_size == 0:
            LOGGER.error(f"Failed to get file size for {fasta_uri}")

        # Use a custom progress bar (or no progress bar)
        wget.download(fasta_uri, str(fasta_file), bar=bar_custom)
        LOGGER.info(f"Downloaded {fasta_uri}")

        store_fasta_files(fasta_file, skip_local_storage)

        if check_md5sum(fasta_file, md5sum):
            LOGGER.info(f"Successfully downloaded and verified {fasta_uri}")
            return True
        elif fasta_uri.find("zfin") != -1:
            return True
        else:
            LOGGER.error("MD5sums do not match")
            return False
    except Exception as e:
        LOGGER.error(f"Error downloading {fasta_uri}: {str(e)}")
        return False


def run_makeblastdb(config_entry: Dict[str, str], output_dir: Path) -> bool:
    fasta_file = Path(config_entry["uri"]).name
    LOGGER.info(f"Running makeblastdb for {fasta_file}")

    SLACK_MESSAGES.append(
        {"title": "Running makeblastdb", "text": f"Processing {fasta_file}"}
    )

    gzipped_fasta = Path(f"../data/{fasta_file}")
    unzipped_fasta = gzipped_fasta.with_suffix("")

    if not unzipped_fasta.exists():
        success, output = run_command(["gunzip", "-k", "-v", str(gzipped_fasta)])
        if not success:
            LOGGER.error(f"Error unzipping {fasta_file}: {output}")
            return False
        LOGGER.info(f"Unzipping {fasta_file}: done")

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

    success, output = run_command(makeblast_command)
    if success:
        LOGGER.info("Makeblastdb: done")
        SLACK_MESSAGES.append(
            {
                "title": "Makeblastdb completed",
                "text": f"Successfully processed {fasta_file}",
            }
        )
        return True
    else:
        LOGGER.error(f"Error running makeblastdb: {output}")
        SLACK_MESSAGES.append(
            {"title": "Makeblastdb Error", "text": f"Failed to process {fasta_file}"}
        )
        return False


def process_yaml(config_yaml: Path, db_info: Optional[dict] = None, skip_local_storage: bool = False) -> bool:
    """
    Process a YAML file containing configuration details for multiple data providers.

    Args:
        config_yaml (Path): The path to the YAML file that needs to be processed.
        db_info (Optional[dict]): Dictionary to track database creation information.
        skip_local_storage (bool): If True, skip local storage of FASTA files.

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
                    process_json(json_file, environment, provider["name"], db_info, skip_local_storage)
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
    db_info: Optional[dict] = None,
    skip_local_storage: bool = False,
) -> bool:
    LOGGER.info(f"Processing JSON file: {json_file}")

    if mod is None:
        mod = get_mod_from_json(json_file)

    if not mod:
        LOGGER.error("Unable to determine MOD")
        return False

    try:
        with open(json_file, "r") as file:
            db_coordinates = json.load(file)

        total_entries = len(db_coordinates["data"])
        with Progress() as progress:
            main_task = progress.add_task(
                f"Processing {mod} - {environment}", total=total_entries
            )

            for entry in db_coordinates["data"]:
                LOGGER.info(f"Processing {entry['uri']}")
                if get_files_ftp(entry["uri"], entry["md5sum"], skip_local_storage):
                    output_dir, config_dir = create_db_structure(
                        environment, mod, entry
                    )
                    copyfile(json_file, config_dir / "environment.json")

                    if output_dir.exists():
                        if run_makeblastdb(entry, output_dir):
                            if db_info is not None:
                                db_info["databases_created"].append(
                                    {
                                        "name": entry["blast_title"],
                                        "type": entry["seqtype"],
                                        "taxon_id": entry["taxon_id"],
                                    }
                                )
                        else:
                            LOGGER.error(
                                f"Failed to create BLAST database for {entry['uri']}"
                            )
                            return False
                progress.update(main_task, advance=1)

        return True
    except Exception as e:
        LOGGER.error(f"Error processing JSON file: {str(e)}", exc_info=True)
        return False


def derive_mod_from_input(input_file):
    """
    Derive the MOD (Model Organism) from the input file name.

    Args:
        input_file (str): The path to the input file.

    Returns:
        str: The MOD (Model Organism) extracted from the input file name. If the input file name does not have the expected format or the MOD cannot be extracted, returns None.
    """
    from utils import MODS

    file_name = Path(input_file).name
    parts = file_name.split('.')

    # Try standard pattern: databases.MOD.environment.json
    if len(parts) >= 3 and parts[0] == 'databases':
        mod_part = parts[1]

        # First, check exact match with known MODs
        if mod_part.upper() in [m.upper() for m in MODS]:
            return mod_part.upper()

        # Try prefix match against known MODs, handling cases like "SGD_test"
        for known_mod in MODS:
            if mod_part.upper().startswith(known_mod.upper()):
                return known_mod

        # If no match found, return the extracted value anyway
        # This allows flexibility for test/custom MODs
        return mod_part

    # If pattern doesn't match, return None to indicate MOD should be specified explicitly
    return None



@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option("-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
@click.option("--skip-local-storage", help="Skip local storage of FASTA files", is_flag=True, default=False)
@click.option("--copy-to-sequenceserver/--no-copy-to-sequenceserver", "enable_sequenceserver_copy", help="Copy databases and config to /var/sequenceserver-data/", default=True)
def create_dbs(config_yaml, input_json, environment, mod, skip_efs_sync, update_slack, sync_s3, skip_local_storage, enable_sequenceserver_copy):
    """
    A command line interface function that creates BLAST databases based on the provided configuration.

    Parameters:
    - config_yaml (str): YAML file with all MODs configuration.
    - input_json (str): JSON file input coordinates.
    - environment (str): Environment. Default is "dev".
    - mod (str): Model organism.
    - skip_efs_sync (bool): Skip EFS sync. Default is False.
    - update_slack (bool): Update Slack. Default is False.
    - sync_s3 (bool): Sync to S3. Default is False.
    - skip_local_storage (bool): Skip local storage of FASTA files. Default is False.
    - enable_sequenceserver_copy (bool): Copy to /var/sequenceserver-data/. Default is True.

    Returns:
    None
    """
    global LOGGER
    start_time = time.time()

    # Derive MOD first for log filename
    temp_mod = mod if mod else derive_mod_from_input(input_json or config_yaml)
    temp_mod = temp_mod if temp_mod else "unknown"

    # Create per-run log file with timestamp and config info
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_name = Path(input_json or config_yaml or "unknown").stem if (input_json or config_yaml) else "unknown"
    log_filename = f"blast_db_{temp_mod}_{environment}_{timestamp}.log"

    # Initialize logger for this run
    LOGGER = setup_logger("create_blast_db", log_filename)

    LOGGER.info(f"Starting BLAST database creation")
    LOGGER.info(f"Config file: {config_yaml or input_json}")
    LOGGER.info(f"MOD: {temp_mod}, Environment: {environment}")
    LOGGER.info(f"Skip local storage: {skip_local_storage}")
    LOGGER.info(f"Copy to SequenceServer: {enable_sequenceserver_copy}")

    try:
        # If mod is not provided, try to derive it from the input file
        if mod is None:
            mod = derive_mod_from_input(input_json or config_yaml)
            if mod is None:
                LOGGER.error("Could not derive MOD from filename. Please specify MOD explicitly using -m/--mod option.")
                console.print(
                    Panel(
                        "[bold red]Error:[/bold red] Could not determine MOD from filename.\n"
                        "Please specify the MOD explicitly using the -m/--mod option.\n"
                        "Example: python create_blast_db.py -j <file> -m SGD",
                        title="Missing MOD",
                        border_style="red",
                    )
                )
                return

        db_info = {
            "mod": mod,
            "environment": environment,
            "databases_created": []
        }

        if config_yaml:
            success = process_yaml(Path(config_yaml), db_info, skip_local_storage)
        elif input_json:
            success = process_json(Path(input_json), environment, db_info['mod'], db_info, skip_local_storage)
        else:
            LOGGER.error("Neither config_yaml nor input_json provided")
            return

        if not success:
            LOGGER.error("Processing failed. Exiting.")
            return

        if update_slack:
            message = f"*MOD:* {db_info['mod']}\n"
            message += f"*Environment:* {db_info['environment']}\n"
            message += f"*Databases created:* {len(db_info['databases_created'])}\n\n"
            for db in db_info['databases_created']:
                # Escape underscores in database names for Slack markdown
                db_name = db['name'].replace('_', r'\_')
                message += f"• {db_name}\n  - Type: `{db['type']}`\n  - Taxon ID: `{db['taxon_id']}`\n"

            slack_success = slack_message([{"text": message}], subject="BLAST Database Update")
            LOGGER.info(f"Slack update {'successful' if slack_success else 'failed'}")

        if sync_s3:
            s3_success = s3_sync(Path("../data"), skip_efs_sync)
            LOGGER.info(f"S3 sync {'successful' if s3_success else 'failed'}")

        if enable_sequenceserver_copy:
            copy_success = copy_to_sequenceserver(mod, environment)
            LOGGER.info(f"SequenceServer copy {'successful' if copy_success else 'failed'}")

    except Exception as e:
        LOGGER.error(f"Unhandled exception in create_dbs: {str(e)}", exc_info=True)
    finally:
        end_time = time.time()
        duration = end_time - start_time
        LOGGER.info(f"create_dbs function completed in {duration:.2f} seconds")



if __name__ == "__main__":
    create_dbs()
