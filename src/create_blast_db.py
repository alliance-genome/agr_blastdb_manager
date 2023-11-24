# Paulo Nuin July 2023


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

    :param fasta_file:
    :param file_logger:
    """

    date_to_add = datetime.now().strftime("%Y_%b_%d")

    original_files_store = Path(f"../data/database_{date_to_add}")

    if not Path(original_files_store).exists():
        console.log(f"Creating {original_files_store}")
        Path(original_files_store).mkdir(parents=True, exist_ok=True)

    copyfile(fasta_file, original_files_store / Path(fasta_file).name)


def get_files_ftp(fasta_uri, md5sum, file_logger) -> bool:
    """
    Function that downloads the files from the FTP site
    :param fasta_uri:
    :param md5sum:
    :param dry_run:
    :return:
    """

    file_logger.info(f"Downloading {fasta_uri}")

    # size = get_ftp_file_size(fasta_uri, file_logger)

    try:
        console.log(f"Downloading {fasta_uri}")
        fasta_file = f"../data/{Path(fasta_uri).name}"
        console.log(f"Saving to {fasta_file}")
        file_logger.info(f"Saving to {fasta_file}")
        if not Path(fasta_file).exists():
            wget.download(fasta_uri, fasta_file)
            store_fasta_files(fasta_file, file_logger)
        else:
            console.log(f"{fasta_file} already exists")
            file_logger.info(f"{fasta_file} already exists")
        if check_md5sum(fasta_file, md5sum):
            return True
        else:
            file_logger.info("MD5sums do not match")
    except Exception as e:
        console.log(f"Error downloading {fasta_uri}: {e}")
        return False


def create_db_structure(environment, mod, config_entry, file_logger) -> bool:
    """
    Function that creates the database and folder structure
    :param environment:
    :param mod:
    :param config_entry:
    :param dry_run:
    """
    file_logger.info("Creating database structure")

    if "seqcol" in config_entry.keys():
        file_logger.info("seqcol found in config file")
        console.log(
            f"Directory '../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}"
            f"/{config_entry['blast_title']}/' will be created"
        )
        p = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{config_entry['blast_title']}/"
    else:
        file_logger.info("seqcol not found in config file")
        console.log(
            f"Directory '../data/blast/{mod}/{environment}/databases/{config_entry['genus']}"
            f"{config_entry['species']}"
            f"/{config_entry['blast_title']}/' will be created"
        )
        p = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{config_entry['blast_title'].replace(' ', '_')}/"
        )
    c = f"../data/config/{mod}/{environment}"

    Path(p).mkdir(parents=True, exist_ok=True)
    Path(c).mkdir(parents=True, exist_ok=True)

    console.log(f"Directory {p} created")
    file_logger.info(f"Directory {p} created")

    return p, c


def run_makeblastdb(config_entry, output_dir, file_logger):
    """
    This function runs the makeblastdb command to create a BLAST database.

    :param config_entry: A JSON element containing information about the database to be created.
    :param output_dir: The directory where the BLAST databases will be created.
    :param file_logger: An external file logger.
    """

    # Load environment variables
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Get the name of the FASTA file
    fasta_file = Path(config_entry["uri"]).name

    # Log the start of the makeblastdb process
    console.log(f"Running makeblastdb for {fasta_file}")

    # Add a message to the slack_messages list
    slack_messages.append(
        {"title": "Running makeblastdb", "text": fasta_file, "color": "#36a64f"},
    )

    # Check if the FASTA file exists in the data directory
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
        # Construct the command to run makeblastdb
        makeblast_command = (
            f"{env['MAKEBLASTDB_BIN']} -in ../data/{fasta_file.replace('.gz', '')} -dbtype {config_entry['seqtype']} "
            f"-title '{config_entry['blast_title']}' -parse_seqids "
            f"-out {output_dir}/{fasta_file.replace('fa.gz', 'db ')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
        )

        # Log the start of the makeblastdb process
        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        console.log(f"Running makeblastdb: {makeblast_command}")

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
            Path(f"../data/{fasta_file.replace('.gz', '')}").unlink()
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


def process_yaml(config_yaml) -> bool:
    """
    This function processes a YAML file, extracts necessary data, and performs operations based on the provided arguments.

    :param config_yaml: The YAML file to be processed.
    :return: Returns True if the process was successful, False otherwise.
    """

    # Load the YAML file
    config = yaml.load(open(config_yaml), Loader=yaml.FullLoader)

    # Iterate over each data provider in the YAML file
    for provider in config["data_providers"]:
        # Log the name of the data provider
        console.log(f"Processing {provider['name']}")
        # Add a message to the slack_messages list
        slack_messages.append(
            {
                "title": "YAML processing",
                "text": f"{provider['name']} from {Path(config_yaml).stem}",
                "color": "#36a64f",
            }
        )

        # Iterate over each environment in the data provider
        for environment in provider["environments"]:
            # Log the name of the environment
            console.log(f"Processing {environment}")

            # Construct the path to the JSON file
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
    This function processes a JSON file, extracts necessary data, and performs operations based on the provided arguments.

    :param json_file: The JSON file to be processed.
    :param environment: The environment in which the process is running.
    :param mod: The model organism for which the data is being processed.
    :return: Returns True if the process was successful, False otherwise.
    """

    # Get the current date and log it
    date_to_add = datetime.now().strftime("%Y_%b_%d")
    console.log(f"Processing {json_file}")

    # Add a message to the slack_messages list
    slack_messages.append(
        {"title": "JSON processing", "text": Path(json_file).stem, "color": "#36a64f"},
    )

    # If a model organism is not provided, get it from the JSON file
    if mod is None:
        mod_code = get_mod_from_json(json_file)
    else:
        mod_code = mod

    # If a model organism code is found, process the JSON file
    if mod_code is not False:
        # Load the JSON file
        db_coordinates = json.load(open(json_file, "r"))

        # Iterate over each entry in the JSON file
        for entry in db_coordinates["data"]:
            # Create a logger for each entry
            file_logger = extendable_logger(
                entry["blast_title"],
                f"../logs/{entry['genus']}_{entry['species']}"
                f"_{entry['seqtype']}_{date_to_add}.log",
            )

            # Log the model organism code
            file_logger.info(f"Mod found/provided: {mod_code}")

            # If files are found via FTP, get them
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
    Function that runs the pipeline

    :param config_yaml: YAML file with all MODs configuration
    :param input_json: JSON file input coordinates
    :param environment: Environment, defaults to 'dev'
    :param mod: Model organism
    :param check_route53: Check Route53, defaults to False
    :param skip_efs_sync: Skip EFS sync, defaults to False
    :param update_slack: Update Slack, defaults to False
    :param sync_s3: Sync to S3, defaults to False
    :return: None
    """

    # If no arguments are passed, display the help message
    if len(sys.argv) == 1:
        click.main(["--help"])

    # If a YAML configuration file is provided, process it
    if config_yaml is not None:
        process_yaml(config_yaml)

    # If the Route53 check option is enabled, perform the check
    elif check_route53:
        console.log("Checking Route53")
        route53_check()

    # If no YAML file is provided and Route53 check is not enabled, process the JSON input
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
