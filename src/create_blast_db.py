"""
create_blast_db.py

This script is used to create BLAST databases from FASTA files. It includes functions to download files from an FTP site,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in YAML and JSON formats.

Author: Paulo Nuin, Adam Wright
Date: started July 2023
"""


import json
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
from subprocess import PIPE, Popen

import click
import wget
import yaml
from dotenv import dotenv_values
from rich.console import Console

from utils import (
    check_md5sum,
    check_output,
    edit_fasta,
    extendable_logger,
    get_mod_from_json,
    route53_check,
    s3_sync,
    slack_message,
    split_zfin_fasta,
)

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


    :param fasta_uri: The URI of the FASTA file that needs to be downloaded.
    :type fasta_uri: str
    :param md5sum: The MD5 checksum of the file.
    :type md5sum: str
    :param file_logger: The logger object used for logging the process of downloading the files.
    :type file_logger: logging.Logger
    :return: True if the file was successfully downloaded and the MD5 checksum matches, False otherwise.
    :rtype: bool

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

def create_db_structure(environment, mod, config_entry, file_logger) -> bool:
    """
    Function that creates the database and folder structure for storing the downloaded FASTA files.

    Parameters:
    environment (str): The current environment (like dev, prod, etc.).
    mod (str): The model organism.
    config_entry (dict): A dictionary containing the configuration details.
    file_logger (logging.Logger): The logger object used for logging the process of creating the database structure.

    Returns:
    bool: True if the directory was successfully created, False otherwise.

    :param environment: The current environment (like dev, prod, etc.).
    :type environment: str
    :param mod: The model organism.
    :type mod: str
    :param config_entry: A dictionary containing the configuration details.
    :type config_entry: dict
    :param file_logger: The logger object used for logging the process of creating the database structure.
    :type file_logger: logging.Logger
    :return: True if the directory was successfully created, False otherwise.
    :rtype: bool
    """

    # Log the start of the database structure creation process
    file_logger.info("Creating database structure")

    # Check if 'seqcol' is present in the configuration entry

    if "seqcol" in config_entry.keys():
        # If it is, log the fact and construct the directory path using 'seqcol'
        file_logger.info("seqcol found in config file")
        # Define the directory path if 'seqcol' is present
        p = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{config_entry['blast_title']}/"
    else:
        # If it's not, log the fact and construct the directory path using 'genus', 'species', and 'blast_title'
        file_logger.info("seqcol not found in config file")
        # Define the directory path if 'seqcol' is not present
        p = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{config_entry['blast_title'].replace(' ', '_')}/"
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
    Function that runs the makeblastdb command to create a BLAST database from a FASTA file.

    Parameters:
    config_entry (dict): A dictionary containing the configuration details.
    output_dir (str): The directory where the BLAST database will be stored.
    file_logger (logging.Logger): The logger object used for logging the process of running makeblastdb.

    Returns:
    bool: True if the makeblastdb command was successfully executed, False otherwise.


    :param config_entry: A dictionary containing the configuration details.
    :type config_entry: dict
    :param output_dir: The directory where the BLAST database will be stored.
    :type output_dir: str
    :param file_logger: The logger object used for logging the process of running makeblastdb.
    :type file_logger: logging.Logger
    """

    # Get the name of the FASTA file from the URI in the configuration entry
    fasta_file = Path(config_entry["uri"]).name

    # Log the start of the makeblastdb process
    console.log(f"Running makeblastdb for {fasta_file}")

    # If the FASTA file is not already unzipped, unzip it
    if not Path(f"../data/{fasta_file.replace('.gz', '')}").exists():
        # Log the start of the unzipping process
        file_logger.info(f"Unzipping {fasta_file}")

        # Construct the command to unzip the FASTA file
        unzip_command = f"gunzip -v ../data/{fasta_file}"

        # Run the unzip command
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()

        # Log the end of the unzipping process
        console.log("Unzip: done\nEditing FASATA file")
        file_logger.info(f"Unzipping {fasta_file}: done")

    # Check if the taxon ID is for ZFIN
    if config_entry["taxon_id"] == "NCBITaxon:7955":
        # Log the start of the ZFIN FASTA file editing process
        console.log("Editing ZFIN FASTA file")

        # Edit the ZFIN FASTA file
        split_zfin_fasta(f"../data/{fasta_file.replace('.gz', '')}")

    # Edit the FASTA file
    edit_fasta(f"../data/{fasta_file.replace('.gz', '')}", config_entry)

    try:
        # Define the makeblastdb command
        makeblast_command = (
            f"{env['MAKEBLASTDB_BIN']} -in ../data/{fasta_file.replace('.gz', '')} -dbtype {config_entry['seqtype']} "
            f"-title '{config_entry['blast_title']}' -parse_seqids "
            f"-out {output_dir}/{fasta_file.replace('fa.gz', 'db ')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
        )
        # Log the makeblastdb command
        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        # Execute the makeblastdb command
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        console.log("Makeblastdb: done")
        file_logger.info("Makeblastdb: done")
        # Remove the unzipped FASTA file
        Path(f"../data/{fasta_file.replace('.gz', '')}").unlink()
        file_logger.info(f"Removed {fasta_file.replace('.gz', '')}")
        console.log("Removed unzipped file")

    except Exception as e:
        # If an error occurs during the makeblastdb process, log the error and return False
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

def process_yaml(config_yaml) -> bool:
    """
    Function that processes a YAML file containing configuration details for multiple data providers.

    Parameters:
    config_yaml (str): The path to the YAML file that needs to be processed.

    Returns:
    bool: True if the YAML file was successfully processed, False otherwise.

    :param config_yaml: The path to the YAML file that needs to be processed.
    :type config_yaml: str
    :return: True if the YAML file was successfully processed, False otherwise.
    :rtype: bool
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
            process_json(json_file, environment, provider["name"])

def process_json(json_file, environment, mod) -> bool:
    """
    Function that processes a JSON file containing configuration details for a specific data provider.

    Parameters:
    json_file (str): The path to the JSON file that needs to be processed.
    environment (str): The current environment (like dev, prod, etc.).
    mod (str): The model organism.

    Returns:
    bool: True if the JSON file was successfully processed, False otherwise.

    :param json_file: The path to the JSON file that needs to be processed.
    :type json_file: str
    :param environment: The current environment (like dev, prod, etc.).
    :type environment: str
    :param mod: The model organism.
    :type mod: str
    :return: True if the JSON file was successfully processed, False otherwise.
    :rtype: bool

    """

    # Get the current date in the format "YYYY_MMM_DD"

    date_to_add = datetime.now().strftime("%Y_%b_%d")
    console.log(f"Processing {json_file}")

    # If the model organism is not provided, get it from the JSON file
    if mod is None:
        mod_code = get_mod_from_json(json_file)
    else:
        mod_code = mod

    # If the model organism is found, process the JSON file
    if mod_code is not False:
        # Load the JSON file
        db_coordinates = json.load(open(json_file, "r"))

        # Iterate over each entry in the JSON file
        for entry in db_coordinates["data"]:
            # Create a logger for the current entry
            file_logger = extendable_logger(
                entry["blast_title"],
                f"../logs/{entry['genus']}_{entry['species']}"
                f"_{entry['seqtype']}_{date_to_add}.log",
            )

            # Log the model organism code
            file_logger.info(f"Mod found/provided: {mod_code}")
            # If the file is successfully downloaded, create the database structure and run makeblastdb
            if get_files_ftp(entry["uri"], entry["md5sum"], file_logger):
                # Create the database structure
                output_dir, config_dir = create_db_structure(
                    environment, mod_code, entry, file_logger
                )

                # Copy the JSON file to the configuration directory
                copyfile(json_file, f"{config_dir}/environment.json")

                # If the output directory exists, run makeblastdb
                if Path(output_dir).exists():
                    run_makeblastdb(entry, output_dir, file_logger)

@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option(
    "-r", "--check_route53", help="Check Route53", is_flag=True, default=False
)
@click.option(
    "-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False
)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
# @click.option("-d", "--dry_run", help="Don't download anything", is_flag=True, default=False)
def create_dbs(
    config_yaml,
    input_json,
    environment,
    mod,
    check_route53,
    skip_efs_sync,
    update_slack,
    sync_s3,
) -> None:
    """
    Main function that runs the pipeline for processing the configuration files and creating the BLAST databases.

    Parameters:
    config_yaml (str): The path to the YAML file that contains configuration details for multiple data providers.
    input_json (str): The path to the JSON file that contains configuration details for a specific data provider.
    environment (str): The current environment (like dev, prod, etc.).
    mod (str): The model organism.
    check_route53 (bool): A flag that indicates whether to check Route53.

    Returns:
    None

    :param config_yaml: The path to the YAML file that contains configuration details for multiple data providers.
    :type config_yaml: str
    :param input_json: The path to the JSON file that contains configuration details for a specific data provider.
    :type input_json: str
    :param environment: The current environment (like dev, prod, etc.).
    :type environment: str
    :param mod: The model organism.
    :type mod: str
    :param check_route53: A flag that indicates whether to check Route53.
    :type check_route53: bool
    """

    # If no arguments are provided, display the help message
    if len(sys.argv) == 1:
        click.main(["--help"])
    # If a YAML configuration file is provided, process the YAML file

    if config_yaml is not None:
        process_yaml(config_yaml)
    # If the check_route53 flag is set, check Route53

    elif check_route53:
        console.log("Checking Route53")
        route53_check()
    # Otherwise, process the JSON file
    else:
        process_json(input_json, environment, mod)

    # If the Slack update option is enabled, update Slack with the messages
    if update_slack:
        slack_message(slack_messages)

    # If the S3 sync option is enabled, sync the data to S3
    if sync_s3:
        s3_sync(Path("../data"), skip_efs_sync)


if __name__ == "__main__":
    create_dbs()
