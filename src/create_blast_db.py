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
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
import subprocess
from typing import Dict, Tuple, List, Optional

import click
import wget
import yaml
from dotenv import load_dotenv
from rich.console import Console

from utils import (
    check_md5sum, check_output, edit_fasta,
    setup_logger, get_mod_from_json, s3_sync,
    send_slack_message
)

# Load environment variables
load_dotenv()

console = Console()

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
LOGGER = setup_logger("create_blast_db")

def store_fasta_files(fasta_file: Path) -> None:
    """
    Store the downloaded FASTA files in a specific directory.

    Args:
        fasta_file (Path): The path to the FASTA file that needs to be stored.
    """
    date_to_add = datetime.now().strftime("%Y_%b_%d")
    original_files_store = Path(f"../data/database_{date_to_add}")
    original_files_store.mkdir(parents=True, exist_ok=True)

    console.log(f"Storing {fasta_file} in {original_files_store}")
    copyfile(fasta_file, original_files_store / fasta_file.name)
    LOGGER.info(f"Stored {fasta_file} in {original_files_store}")

def get_files_ftp(fasta_uri: str, md5sum: str) -> bool:
    """
    Download files from an FTP site.

    Args:
        fasta_uri (str): The URI of the FASTA file that needs to be downloaded.
        md5sum (str): The MD5 checksum of the file.

    Returns:
        bool: True if the file was successfully downloaded and the MD5 checksum matches, False otherwise.
    """
    LOGGER.info(f"Downloading {fasta_uri}")
    console.log(f"Downloading {fasta_uri}")

    today_date = datetime.now().strftime("%Y_%b_%d")
    fasta_file = Path(f"../data/{Path(fasta_uri).name}")

    if (Path(f"../data/database_{today_date}") / fasta_file.name).exists():
        console.log(f"{fasta_file.name} already processed")
        LOGGER.info(f"{fasta_file} already processed")
        return False

    try:
        wget.download(fasta_uri, str(fasta_file))
        store_fasta_files(fasta_file)

        if check_md5sum(fasta_file, md5sum):
            return True
        else:
            LOGGER.error("MD5sums do not match")
            return False
    except Exception as e:
        console.log(f"Error downloading {fasta_uri}: {e}")
        LOGGER.error(f"Error downloading {fasta_uri}: {e}")
        return False

def create_db_structure(environment: str, mod: str, config_entry: Dict[str, str]) -> Tuple[Path, Path]:
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
        db_path = Path(f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/")
    else:
        LOGGER.info("seqcol not found in config file")
        db_path = Path(f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/{sanitized_blast_title}/")

    config_path = Path(f"../data/config/{mod}/{environment}")

    db_path.mkdir(parents=True, exist_ok=True)
    config_path.mkdir(parents=True, exist_ok=True)

    console.log(f"Directory {db_path} created")
    LOGGER.info(f"Directory {db_path} created")

    return db_path, config_path

def run_makeblastdb(config_entry: Dict[str, str], output_dir: Path) -> bool:
    """
    Run the makeblastdb command to create a BLAST database.

    Args:
        config_entry (Dict[str, str]): Configuration for the database.
        output_dir (Path): Directory to store the output files.

    Returns:
        bool: True if the database was created successfully, False otherwise.
    """
    fasta_file = Path(config_entry["uri"]).name

    LOGGER.info(f"Running makeblastdb for {fasta_file}")
    console.log(f"Running makeblastdb for {fasta_file}")

    SLACK_MESSAGES.append({
        "title": "Running makeblastdb",
        "text": fasta_file,
        "color": "#36a64f",
    })

    unzipped_fasta = Path(f"../data/{fasta_file.replace('.gz', '')}")
    if not unzipped_fasta.exists():
        try:
            LOGGER.info(f"Unzipping {fasta_file}")
            subprocess.run(["gunzip", "-v", f"../data/{fasta_file}"], check=True, capture_output=True, text=True)
            LOGGER.info(f"Unzipping {fasta_file}: done")
            console.log("Unzip: done\nEditing FASTA file")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"Error unzipping {fasta_file}: {e}")
            return False

    sanitized_blast_title = re.sub(r"\W+", "_", config_entry["blast_title"])
    extensions = "".join(Path(fasta_file).suffixes)

    makeblast_command = [
        "makeblastdb",
        "-in", str(unzipped_fasta),
        "-dbtype", config_entry["seqtype"],
        "-title", sanitized_blast_title,
        "-out", str(output_dir / fasta_file.replace(extensions, 'db')),
        "-taxid", config_entry["taxon_id"].replace("NCBITaxon:", ""),
    ]

    LOGGER.info(f"Running makeblastdb: {' '.join(makeblast_command)}")
    console.log(f"Running makeblastdb:\n {' '.join(makeblast_command)}")

    try:
        result = subprocess.run(makeblast_command, check=True, capture_output=True, text=True)
        console.log("Makeblastdb: done")
        SLACK_MESSAGES.append({
            "title": "Makeblastdb completed",
            "text": fasta_file,
            "color": "#36a64f",
        })
        LOGGER.info("Makeblastdb: done")

        unzipped_fasta.unlink()
        LOGGER.info(f"Removed {unzipped_fasta}")
        console.log("Removed unzipped file")
        return True
    except subprocess.CalledProcessError as e:
        console.log(f"Error running makeblastdb: {e}")
        SLACK_MESSAGES.append({
            "title": "Error running makeblastdb",
            "text": fasta_file,
            "color": "#8D2707",
        })
        LOGGER.error(f"Error running makeblastdb: {e}")
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
        with open(config_yaml, 'r') as file:
            config = yaml.safe_load(file)

        for provider in config["data_providers"]:
            console.log(f"Processing {provider['name']}")
            for environment in provider["environments"]:
                console.log(f"Processing {environment}")
                json_file = config_yaml.parent / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
                console.log(f"Processing {json_file}")
                process_json(json_file, environment, provider["name"])

        return True
    except Exception as e:
        LOGGER.error(f"Error processing YAML file: {e}")
        return False

def process_json(json_file: Path, environment: str, mod: Optional[str] = None) -> bool:
    """
    Process a JSON file containing configuration details for a specific data provider.

    Args:
        json_file (Path): The path to the JSON file that needs to be processed.
        environment (str): The current environment (like dev, prod, etc.).
        mod (Optional[str]): The model organism.

    Returns:
        bool: True if the JSON file was successfully processed, False otherwise.
    """
    console.log(f"Processing {json_file}")

    if mod is None:
        mod = get_mod_from_json(json_file)

    if not mod:
        LOGGER.error("Unable to determine MOD")
        return False

    try:
        with open(json_file, 'r') as file:
            db_coordinates = json.load(file)

        for entry in db_coordinates["data"]:
            if get_files_ftp(entry["uri"], entry["md5sum"]):
                output_dir, config_dir = create_db_structure(environment, mod, entry)
                copyfile(json_file, config_dir / "environment.json")

                if output_dir.exists():
                    run_makeblastdb(entry, output_dir)

        return True
    except Exception as e:
        LOGGER.error(f"Error processing JSON file: {e}")
        return False

@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option("-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
def create_dbs(config_yaml, input_json, environment, mod, skip_efs_sync, update_slack, sync_s3):
    """
    Main function that runs the pipeline for processing the configuration files and creating the BLAST databases.
    """
    if len(sys.argv) == 1:
        click.echo(create_dbs.get_help(ctx=None))
        return

    try:
        if config_yaml:
            process_yaml(Path(config_yaml))
        else:
            process_json(Path(input_json), environment, mod)

        if update_slack:
            send_slack_message(SLACK_MESSAGES)

        if sync_s3:
            s3_sync(Path("../data"), skip_efs_sync)

    except Exception as e:
        LOGGER.error(f"Error in create_dbs: {e}")
        console.log(f"Error in create_dbs: {e}")

if __name__ == "__main__":
    create_dbs()