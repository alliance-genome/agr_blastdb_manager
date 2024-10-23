"""
create_blast_db.py

This script is used to create BLAST databases from FASTA files. It includes functions to download files from an FTP site,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in YAML and JSON formats.

Authors: Paulo Nuin, Adam Wright
Date: started July 2023
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
from subprocess import PIPE, Popen

import click
import wget  # type: ignore
import yaml
from dotenv import dotenv_values
from rich.console import Console

from utils import (check_md5sum, check_output, extendable_logger,
                  get_mod_from_json, list_databases_from_config, s3_sync,
                  slack_message, needs_parse_seqids)

console = Console()

slack_messages = []


def store_fasta_files(fasta_file, file_logger) -> None:
    """
    Function to store the downloaded FASTA files in a specific directory.

    Parameters:
    fasta_file (str): The path to the FASTA file that needs to be stored.
    file_logger (logging.Logger): The logger object used for logging the process of storing the FASTA files.

    Returns:
    None


    :param fasta_file: The path to the FASTA file that needs to be stored.
    :type fasta_file: str
    :param file_logger: The logger object used for logging the process of storing the FASTA files.
    :type file_logger: logging.Logger

    :param fasta_file: The path to the fasta file to be stored.
    :param file_logger: The logger to log the function's actions and errors.
    """

    # Get the current date in the format "YYYY_MMM_DD"
    date_to_add = datetime.now().strftime("%Y_%b_%d")

    # Define the directory where the FASTA files will be stored
    original_files_store = Path(f"../data/database_{date_to_add}")

    # If the directory does not exist, create it
    if not Path(original_files_store).exists():
        console.log(f"Creating {original_files_store}")
        Path(original_files_store).mkdir(parents=True, exist_ok=True)

    # Copy the FASTA file to the directory
    copyfile(fasta_file, original_files_store / Path(fasta_file).name)


def get_files_ftp(fasta_uri, md5sum, file_logger) -> bool:
    """
    Function to download files from an FTP site.

    Parameters:
    fasta_uri (str): The URI of the FASTA file that needs to be downloaded.
    md5sum (str): The MD5 checksum of the file.
    file_logger (logging.Logger): The logger object used for logging the process of downloading the files.

    Returns:
    bool: True if the file was successfully downloaded and the MD5 checksum matches, False otherwise.
    """

    # Log the start of the download process
    file_logger.info(f"Downloading {fasta_uri}")

    # Get the current date in the format "YYYY_MMM_DD"
    today_date = datetime.now().strftime("%Y_%b_%d")
    try:
        # Log the download process
        console.log(f"Downloading {fasta_uri}")

        # Define the path where the downloaded file will be stored
        fasta_file = f"../data/{Path(fasta_uri).name}"
        fasta_name = f"{Path(fasta_uri).name}"

        # Log the path where the file will be stored
        console.log(f"Saving to {fasta_file}")
        file_logger.info(f"Saving to {fasta_file}")

        # If the file does not already exist, download it and store it
        if not Path(f"../data/database_{today_date}/{fasta_name}").exists():
            wget.download(fasta_uri, fasta_file)
            store_fasta_files(fasta_file, file_logger)
        else:
            # If the file already exists, log this information and return False
            console.log(f"{fasta_name} already processed")
            file_logger.info(f"{fasta_file} already processed")
            return False

        # Check the MD5 checksum of the downloaded file
        if check_md5sum(fasta_file, md5sum):
            # If the checksum is correct, return True
            return True
        else:
            # If the MD5 checksum does not match, log this information
            file_logger.info("MD5sums do not match")
    except Exception as e:
        # If an error occurs during the download process, log the error and return False
        console.log(f"Error downloading {fasta_uri}: {e}")
        return False

    return True


def create_db_structure(environment, mod, config_entry, file_logger) -> tuple[str, str]:
    """
    Function that creates the database and folder structure for storing the downloaded FASTA files.

    Parameters:
    environment (str): The current environment (like dev, prod, etc.).
    mod (str): The model organism.
    config_entry (dict): A dictionary containing the configuration details.
    file_logger (logging.Logger): The logger object used for logging the process of creating the database structure.

    Returns:
    tuple[str, str]: A tuple containing the paths to the created directories.
    """

    # Get the blast_title from the config_entry
    blast_title = config_entry["blast_title"]

    # Use a regular expression to replace non-alphanumeric characters with an underscore
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)

    # Log the start of the database structure creation process
    file_logger.info("Creating database structure")

    # Check if 'seqcol' is present in the configuration entry
    if "seqcol" in config_entry.keys():
        # If it is, log the fact and construct the directory path using 'seqcol'
        file_logger.info("seqcol found in config file")
        # Define the directory path if 'seqcol' is present
        p = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/"
    else:
        # If it's not, log the fact and construct the directory path using 'genus', 'species', and 'blast_title'
        file_logger.info("seqcol not found in config file")
        # Define the directory path if 'seqcol' is not present
        p = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{sanitized_blast_title.replace(' ', '_')}/"
        )
    c = f"../data/config/{mod}/{environment}"

    # Create the directory if it does not exist
    Path(p).mkdir(parents=True, exist_ok=True)
    Path(c).mkdir(parents=True, exist_ok=True)

    # Log the creation of the directory
    console.log(f"Directory {p} created")
    file_logger.info(f"Directory {p} created")

    # Return the paths of the created directories
    return p, c


def run_makeblastdb(config_entry, output_dir, file_logger):
    """
    This function runs the makeblastdb command to create a BLAST database.

    Parameters:
    config_entry (dict): A dictionary containing the configuration details.
    output_dir (str): The directory where the BLAST database will be created.
    file_logger (logging.Logger): The logger object used for logging the process.
    """
    # Load environment variables
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Get the name of the FASTA file
    fasta_file = Path(config_entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    # Log the start of the makeblastdb process
    console.log(f"Running makeblastdb for {fasta_file}")

    # Add a message to the slack_messages list
    slack_messages.append(
        {"title": "Running makeblastdb", "text": fasta_file, "color": "#36a64f"},
    )

    # Check if the FASTA file exists in the data directory
    if not Path(unzipped_fasta).exists():
        # Log the start of the unzipping process
        file_logger.info(f"Unzipping {fasta_file}")

        # Construct the command to unzip the FASTA file
        unzip_command = f"gunzip -v ../data/{fasta_file}"

        # Run the unzip command
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()

        # Log the end of the unzipping process
        console.log("Unzip: done\nEditing FASTA file")
        file_logger.info(f"Unzipping {fasta_file}: done")

    # Check if parse_seqids is needed using the utility function
    parse_ids_flag = ""
    if needs_parse_seqids(unzipped_fasta):
        parse_ids_flag = "-parse_seqids"
        file_logger.info("FASTA headers require -parse_seqids flag")
        console.log("FASTA headers require -parse_seqids flag")

    # Get the blast_title from the config_entry
    blast_title = config_entry["blast_title"]

    # Use a regular expression to replace non-alphanumeric characters with an underscore
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)

    extensions = "".join(Path(fasta_file).suffixes)

    try:
        # Construct the command to run makeblastdb
        makeblast_command = (
            f"makeblastdb -in {unzipped_fasta} -dbtype {config_entry['seqtype']} "
            f"-title '{sanitized_blast_title}' "
            f"-out {output_dir}/{fasta_file.replace(extensions, 'db')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
            f"{parse_ids_flag}"
        ).strip()  # strip() removes trailing space if parse_ids_flag is empty

        # Log the start of the makeblastdb process
        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        console.log(f"Running makeblastdb:\n {makeblast_command}")

        # Run the makeblastdb command
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        p.wait()

        # Check if the makeblastdb process was successful
        if check_output(stdout, stderr):
            # Log the end of the makeblastdb process
            console.log("Makeblastdb: done")
            slack_messages.append(
                {
                    "title": "Makeblastdb completed",
                    "text": fasta_file,
                    "color": "#36a64f",
                },
            )
            file_logger.info("Makeblastdb: done")

            # Remove the unzipped FASTA file
            Path(unzipped_fasta).unlink()
            file_logger.info(f"Removed {fasta_file.replace('.gz', '')}")
            console.log("Removed unzipped file")
        else:
            # Log an error message
            console.log("Error running makeblastdb")
            slack_messages.append(
                {
                    "title": "Error running makeblastdb",
                    "text": fasta_file,
                    "color": "#8D2707",
                },
            )
            file_logger.info("Error running makeblastdb")

            # Remove the folders
            console.log("Removing folders")
            rmtree(output_dir)

            return False
    except Exception as e:
        # Log an error message
        console.log(f"Error running makeblastdb: {e}")
        slack_messages.append(
            {
                "title": "Error running makeblastdb",
                "text": fasta_file,
                "color": "#8D2707",
            },
        )
        file_logger.info(f"Error running makeblastdb: {e}")

        return False

    return True


def process_yaml(config_yaml, db_list=None) -> bool:
    """
    Function that processes a YAML file containing configuration details for multiple data providers.

    Parameters:
    config_yaml (str): The path to the YAML file that needs to be processed.
    db_list (list): Optional list of database names to process.

    Returns:
    bool: True if the YAML file was successfully processed, False otherwise.
    """
    # Load the YAML file
    config = yaml.load(open(config_yaml), Loader=yaml.FullLoader)

    # Iterate over each data provider in the configuration
    for provider in config["data_providers"]:
        # Log the name of the data provider
        console.log(f"Processing {provider['name']}")

        # Iterate over each environment for the current data provider
        for environment in provider["environments"]:
            # Log the name of the environment
            console.log(f"Processing {environment}")

            # Define the path to the JSON file for the current data provider and environment
            json_file = (
                Path(config_yaml).parent
                / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
            )

            # Log the path to the JSON file
            console.log(f"Processing {json_file}")

            # Process the JSON file
            process_json(json_file, environment, provider["name"], db_list)

    return True


def process_json(json_file, environment, mod, db_list=None) -> bool:
    """
    Process a JSON file containing configuration details for a specific data provider.

    Parameters:
    json_file (str): The path to the JSON file that needs to be processed.
    environment (str): The current environment (like dev, prod, etc.).
    mod (str): The model organism.
    db_list (list): Optional list of database names to process.

    Returns:
    bool: True if all databases were processed successfully, False if any errors occurred.
    """
    try:
        date_to_add = datetime.now().strftime("%Y_%b_%d")
        console.log(f"Processing {json_file}")

        # Verify JSON file exists
        if not Path(json_file).exists():
            console.log(f"[red]Error: JSON file not found: {json_file}[/red]")
            return False

        # Get or verify mod code
        mod_code = mod if mod is not None else get_mod_from_json(json_file)
        if not mod_code:
            console.log("[red]Error: Invalid or missing MOD code[/red]")
            return False

        # Load and validate JSON file
        try:
            with open(json_file, "r") as f:
                db_coordinates = json.load(f)
        except json.JSONDecodeError as e:
            console.log(f"[red]Error: Invalid JSON file: {e}[/red]")
            return False

        if "data" not in db_coordinates:
            console.log(
                "[red]Error: Invalid JSON structure - 'data' key not found[/red]"
            )
            return False

        # Create logs directory if it doesn't exist
        Path("../logs").mkdir(parents=True, exist_ok=True)

        # Track overall success
        all_successful = True

        # Process each database entry
        for entry in db_coordinates["data"]:
            try:
                # Skip if not in requested database list
                if db_list and entry["blast_title"] not in db_list:
                    console.log(
                        f"Skipping {entry['blast_title']} - not in requested database list"
                    )
                    continue

                # Validate required fields
                required_fields = [
                    "blast_title",
                    "genus",
                    "species",
                    "seqtype",
                    "uri",
                    "md5sum",
                ]
                missing_fields = [
                    field for field in required_fields if field not in entry
                ]
                if missing_fields:
                    console.log(
                        f"[red]Error: Missing required fields for {entry.get('blast_title', 'Unknown')}: {missing_fields}[/red]"
                    )
                    all_successful = False
                    continue

                # Create logger for current entry
                log_path = f"../logs/{entry['genus']}_{entry['species']}_{entry['seqtype']}_{date_to_add}.log"
                file_logger = extendable_logger(entry["blast_title"], log_path)
                file_logger.info(f"Mod found/provided: {mod_code}")

                # Download and process the file
                if not get_files_ftp(entry["uri"], entry["md5sum"], file_logger):
                    console.log(
                        f"[red]Error: Failed to download or verify file for {entry['blast_title']}[/red]"
                    )
                    all_successful = False
                    continue

                # Create database structure
                try:
                    output_dir, config_dir = create_db_structure(
                        environment, mod_code, entry, file_logger
                    )
                except Exception as e:
                    console.log(
                        f"[red]Error creating database structure for {entry['blast_title']}: {e}[/red]"
                    )
                    file_logger.error(f"Error creating database structure: {e}")
                    all_successful = False
                    continue

                # Copy configuration file
                try:
                    copyfile(json_file, f"{config_dir}/environment.json")
                except Exception as e:
                    console.log(
                        f"[red]Error copying configuration file for {entry['blast_title']}: {e}[/red]"
                    )
                    file_logger.error(f"Error copying configuration file: {e}")
                    all_successful = False
                    continue

                # Run makeblastdb if output directory exists
                if Path(output_dir).exists():
                    if not run_makeblastdb(entry, output_dir, file_logger):
                        console.log(
                            f"[red]Error: makeblastdb failed for {entry['blast_title']}[/red]"
                        )
                        all_successful = False
                else:
                    console.log(
                        f"[red]Error: Output directory not found for {entry['blast_title']}[/red]"
                    )
                    all_successful = False

            except Exception as e:
                console.log(
                    f"[red]Error processing entry {entry.get('blast_title', 'Unknown')}: {e}[/red]"
                )
                all_successful = False

        return all_successful

    except Exception as e:
        console.log(f"[red]Fatal error processing JSON file: {e}[/red]")
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
@click.option(
    "-d",
    "--db_names",
    help="Comma-separated list of database names to create",
    default=None,
)
@click.option(
    "-l",
    "--list",
    "list_dbs",
    help="List available databases",
    is_flag=True,
    default=False,
)
def create_dbs(
    config_yaml,
    input_json,
    environment,
    mod,
    skip_efs_sync,
    update_slack,
    sync_s3,
    db_names,
    list_dbs,
) -> None:
    """
    Main function that runs the pipeline for processing the configuration files and creating the BLAST databases.
    Use -d/--db_names to specify which databases to create (comma-separated list matching blast_title in config).
    Use -l/--list to see available databases without creating them.
    """
    # If list option is specified, show available databases and exit
    if list_dbs:
        if config_yaml:
            list_databases_from_config(config_yaml)
        elif input_json:
            list_databases_from_config(input_json)
        else:
            click.echo(
                "Please provide either a YAML (-g) or JSON (-j) configuration file to list databases."
            )
        return

    # Convert db_names string to list if provided
    db_list = None
    if db_names:
        db_list = [name.strip() for name in db_names.split(",")]

    # If no arguments are provided, display the help message
    if len(sys.argv) == 1:
        click.echo(create_dbs.get_help(ctx=None))
    # If a YAML configuration file is provided, process the YAML file
    elif config_yaml is not None:
        process_yaml(config_yaml, db_list)
    # Otherwise, process the JSON file
    else:
        process_json(input_json, environment, mod, db_list)

    # If the Slack update option is enabled, update Slack with the messages
    if update_slack:
        slack_message(slack_messages)

    # If the S3 sync option is enabled, sync the data to S3
    if sync_s3:
        s3_sync(Path("../data"), skip_efs_sync)


if __name__ == "__main__":
    create_dbs()
