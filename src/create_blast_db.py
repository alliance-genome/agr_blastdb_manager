"""
create_blast_db.py

This script creates BLAST databases from FASTA files. It includes functions to download files from HTTPS or FTP sites,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in JSON format.

Authors: Paulo Nuin, Adam Wright, [Assistant]
Date: Started July 2023, Refactored [Current Date]
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TaskID,
                           TextColumn)
from rich.style import Style
from rich.table import Table
from ftplib import FTP

from utils import (check_md5sum, check_output, edit_fasta, get_ftp_file_size,
                   get_mod_from_json, needs_parse_id, run_command, s3_sync,
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

def get_files(fasta_uri: str, md5sum: str) -> bool:
    """
    Download files from HTTPS or FTP based on the URI.

    Args:
        fasta_uri (str): The URI of the FASTA file to download.
        md5sum (str): The expected MD5 checksum of the file.

    Returns:
        bool: True if download and verification succeed, False otherwise.
    """
    LOGGER.info(f"Downloading {fasta_uri}")

    today_date = datetime.now().strftime("%Y_%b_%d")
    fasta_file = Path(f"../data/{Path(fasta_uri).name}")

    if (Path(f"../data/database_{today_date}") / fasta_file.name).exists():
        LOGGER.info(f"{fasta_file} already processed")
        return False

    parsed_uri = urlparse(fasta_uri)
    
    try:
        if parsed_uri.scheme in ['http', 'https']:
            return get_files_https(fasta_uri, fasta_file, md5sum)
        elif parsed_uri.scheme == 'ftp':
            return get_files_ftp(fasta_uri, fasta_file, md5sum)
        else:
            LOGGER.error(f"Unsupported protocol: {parsed_uri.scheme}")
            return False
    except Exception as e:
        LOGGER.error(f"Error downloading {fasta_uri}: {str(e)}")
        return False

def get_files_https(fasta_uri: str, fasta_file: Path, md5sum: str) -> bool:
    """Download files from HTTPS."""
    try:
        with requests.get(fasta_uri, stream=True, timeout=300) as response:
            response.raise_for_status()
            with open(fasta_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        LOGGER.info(f"Downloaded {fasta_uri}")
        store_fasta_files(fasta_file)
        return verify_download(fasta_file, md5sum, fasta_uri)
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Error downloading {fasta_uri}: {str(e)}")
        return False

def get_files_ftp(fasta_uri: str, fasta_file: Path, md5sum: str) -> bool:
    """Download files from FTP."""
    parsed_uri = urlparse(fasta_uri)
    try:
        with FTP(parsed_uri.netloc) as ftp:
            ftp.login()
            with open(fasta_file, 'wb') as f:
                ftp.retrbinary(f'RETR {parsed_uri.path}', f.write)
        
        LOGGER.info(f"Downloaded {fasta_uri}")
        store_fasta_files(fasta_file)
        return verify_download(fasta_file, md5sum, fasta_uri)
    except Exception as e:
        LOGGER.error(f"Error downloading {fasta_uri}: {str(e)}")
        return False

def verify_download(fasta_file: Path, md5sum: str, fasta_uri: str) -> bool:
    """Verify the downloaded file."""
    if check_md5sum(fasta_file, md5sum):
        LOGGER.info(f"Successfully downloaded and verified {fasta_uri}")
        return True
    else:
        LOGGER.error("MD5sums do not match")
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

def process_json(
    json_file: Path,
    environment: str,
    mod: Optional[str] = None,
    db_info: Optional[dict] = None,
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
                if get_files(entry["uri"], entry["md5sum"]):
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
        LOGGER.error(f"Error processing JSON file: {str(e)}")
        return False

def derive_mod_from_input(input_file):
    """
    Derive the MOD (Model Organism) from the input file name.

    Args:
        input_file (str): The path to the input file.

    Returns:
        str: The MOD (Model Organism) extracted from the input file name. If the input file name does not have the expected format or the MOD cannot be extracted, returns 'Unknown'.
    """
    file_name = Path(input_file).name
    parts = file_name.split('.')
    if len(parts) >= 3 and parts[0] == 'databases':
        return parts[1]  # This should be the MOD
    return 'Unknown'

@click.command()
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option("-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
def create_dbs(input_json, environment, mod, skip_efs_sync, update_slack, sync_s3):
    """
    A command line interface function that creates BLAST databases based on the provided configuration.
    
    Parameters:
    - input_json (str): JSON file input coordinates.
    - environment (str): Environment. Default is "dev".
    - mod (str): Model organism.
    - skip_efs_sync (bool): Skip EFS sync. Default is False.
    - update_slack (bool): Update Slack. Default is False.
    - sync_s3 (bool): Sync to S3. Default is False.
    
    Returns:
    None
    """
    start_time = time.time()
    LOGGER.info("Starting create_dbs function")

    try:
        # If mod is not provided, try to derive it from the input file
        if mod is None:
            mod = derive_mod_from_input(input_json)

        db_info = {
            "mod": mod,
            "environment": environment,
            "databases_created": []
        }

        if input_json:
            success = process_json(Path(input_json), environment, db_info['mod'], db_info)
        else:
            LOGGER.error("Input JSON file not provided")
            return

        if not success:
            LOGGER.error("Processing failed. Exiting.")
            return

        if update_slack:
            message = f"*MOD:* {db_info['mod']}\n"
            message += f"*Environment:* {db_info['environment']}\n"
            message += f"*Databases created:*\n"
            for db in db_info['databases_created']:
                message += f"• *{db['name']}* (Type: `{db['type']}`, Taxon ID: `{db['taxon_id']}`)\n"

            slack_success = slack_message([{"text": message}], subject="BLAST Database Update")
            LOGGER.info(f"Slack update {'successful' if slack_success else 'failed'}")

        if sync_s3:
            s3_success = s3_sync(Path("../data"), skip_efs_sync)
            LOGGER.info(f"S3 sync {'successful' if s3_success else 'failed'}")

    except Exception as e:
        LOGGER.error(f"Unhandled exception in create_dbs: {str(e)}", exc_info=True)
    finally:
        end_time = time.time()
        duration = end_time - start_time
        LOGGER.info(f"create_dbs function completed in {duration:.2f} seconds")

if __name__ == "__main__":
    create_dbs()
