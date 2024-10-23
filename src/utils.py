"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wright
Date: started September 2023
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from ftplib import FTP
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any

import wget
from dotenv import dotenv_values
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.webhook import WebhookClient

console = Console()


# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]


from shutil import copyfile  # Add to imports if not present


def store_fasta_files(fasta_file, file_logger) -> None:
    """
    Function to store the downloaded FASTA files in a specific directory.

    Parameters:
    fasta_file (str): The path to the FASTA file that needs to be stored.
    file_logger (logging.Logger): The logger object used for logging the process.
    """
    date_to_add = datetime.now().strftime("%Y_%b_%d")
    original_files_store = Path(f"../data/database_{date_to_add}")

    if not Path(original_files_store).exists():
        console.log(f"Creating {original_files_store}")
        Path(original_files_store).mkdir(parents=True, exist_ok=True)

    copyfile(fasta_file, original_files_store / Path(fasta_file).name)


def extendable_logger(log_name, file_name, level=logging.INFO) -> Any:
    """
    Creates a logger that can be extended with additional handlers and configurations.

    This function sets up a logger with a specified name, log file, and logging level. The logger uses a file handler to write log messages to a file. The log messages are formatted to include the timestamp, log level, and the log message.

    :param log_name: The name of the logger.
    :type log_name: str
    :param file_name: The name of the file where the log messages will be written.
    :type file_name: str
    :param level: The logging level. By default, it's set to logging.INFO.
    :type level: int, optional
    :return: The configured logger.
    :rtype: logging.Logger
    """

    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
    handler = logging.FileHandler(file_name)
    handler.setFormatter(formatter)
    specified_logger = logging.getLogger(log_name)
    specified_logger.setLevel(level)
    specified_logger.addHandler(handler)

    return specified_logger


def check_md5sum(fasta_file, md5sum) -> bool:
    """
    Checks the MD5 checksum of a downloaded file.

    This function calculates the MD5 checksum of the downloaded file and compares it with the expected checksum. If the checksums match, the function returns True. Otherwise, it returns False.

    :param fasta_file: The path to the downloaded file.
    :type fasta_file: str
    :param md5sum: The expected MD5 checksum.
    :type md5sum: str
    :return: True if the checksums match, False otherwise.
    :rtype: bool
    """

    downloaded_md5sum = hashlib.md5(open(fasta_file, "rb").read()).hexdigest()
    if downloaded_md5sum != md5sum:
        console.log(f"MD5sums do not match: {md5sum} != {downloaded_md5sum}")
        return False

    console.log(f"MD5sums match: {md5sum} {downloaded_md5sum}")

    return True


def get_ftp_file_size(fasta_uri, file_logger) -> int:
    """
    Function to get the size of a file on an FTP server.

    This function connects to an FTP server, navigates to the directory containing the file, and retrieves the size of the file.

    :param fasta_uri: The URI of the FASTA file on the FTP server.
    :type fasta_uri: str
    :param file_logger: The logger object used for logging the process of getting the file size.
    :type file_logger: logging.Logger
    :return: The size of the file in bytes.
    :rtype: int
    """

    # Initialize the size to 0
    size = 0

    # Connect to the FTP server
    ftp = FTP(Path(fasta_uri).parts[1])
    ftp.login()

    # Navigate to the directory containing the file
    ftp.cwd("/".join(Path(fasta_uri).parts[2:-1]))

    # Get the name of the file
    filename = Path(fasta_uri).name

    if filename is not None:
        # Get the size of the file
        size = ftp.size(filename)
        if size is not None:
            # Log the size of the file
            console.log(f"File size is {size} bytes")
            file_logger.info(f"File size is {size} bytes")
        else:
            # Handle the case where size is None
            console.log("Error: File size is not available.")
            return 0
    else:
        console.log("Error: Filename is None.")
        return 0

    return size


def get_mod_from_json(input_json) -> str | bool:
    """
    Retrieves the model organism (mod) from the input JSON file.

    This function extracts the mod from the filename of the input JSON file. The mod is the second element when the filename is split by the "." character. If the mod is not found in the predefined list of mods, the function returns False. Otherwise, it returns the mod.

    :param input_json: The path to the input JSON file.
    :type input_json: str
    :return: The model organism (mod) if found, False otherwise.
    :rtype: str or bool
    """
    filename = Path(input_json).name
    mod = filename.split(".")[1]

    if mod not in MODS:
        console.log(f"Mod {mod} not found in {MODS}")
        return False

    console.log(f"Mod found: {mod}")

    return mod


# def route53_check() -> bool:
#     """
#     Function that checks if the route53 record exists
#     """
#
#     client53 = boto3.client("route53")
#     response = client53.list_resource_record_sets(
#         HostedZoneId="alliancegenome.org", StartRecordType="TXT"
#     )
#     print(response)
#
#     return True


def edit_fasta(fasta_file: str, config_entry: dict) -> bool:
    """
    Edits the FASTA file based on the configuration entry.

    This function opens the FASTA file, reads the lines, and modifies the header lines to include additional information from the configuration entry. The modified lines are then written back to the FASTA file.

    :param fasta_file: The path to the FASTA file to be edited.
    :type fasta_file: str
    :param config_entry: The configuration entry containing the additional information to be added to the FASTA file.
    :type config_entry: dict
    :return: True if the FASTA file was successfully edited, False otherwise.
    :rtype: bool
    """

    # Initialize a list to store the original file lines
    original_file = []

    # Open the FASTA file and read the lines
    with open(fasta_file, "r") as fh:
        lines = fh.readlines()

        # Iterate over the lines
        for line in lines:
            # Check if the line is a header line
            if line.startswith(">"):
                # Strip the newline character from the line
                line = line.strip()

                # Check if 'seqcol' is in the configuration entry
                if "seqcol" in config_entry.keys():
                    # If so, append the 'seqcol', 'genus', and 'species' values to the line
                    line += f" {config_entry['seqcol']} {config_entry['genus']} {config_entry['species']}\n"
                else:
                    # If not, append the 'genus', 'species', and 'version' values to the line
                    line += f" {config_entry['genus']} {config_entry['species']} {config_entry['version']}\n"

                # Add the modified line to the original file list
                original_file.append(line)
            else:
                # If the line is not a header line, add it to the original file list as is
                original_file.append(line)

    # Open the FASTA file in write mode
    edited_file = open(fasta_file, "w")

    # Write the lines from the original file list to the FASTA file
    edited_file.writelines(original_file)

    # Close the FASTA file
    edited_file.close()

    return True


def validate_fasta(filename: str) -> bool:
    """
    Validates if a file is in FASTA format without using Biopython.

    Parameters:
    filename (str): Path to the file to validate

    Returns:
    bool: True if the file is a valid FASTA file, False otherwise
    """
    try:
        with open(filename, "r") as f:
            # Check if file is empty
            first_line = f.readline().strip()
            if not first_line:
                return False

            # Check if first line starts with '>'
            if not first_line.startswith(">"):
                return False

            # Check for at least one sequence
            has_sequence = False
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if not has_sequence:
                        return False
                    has_sequence = False
                elif line:  # sequence line
                    has_sequence = True

            return has_sequence

    except Exception as e:
        console.log(f"[red]Error validating FASTA file: {e}[/red]")
        return False


def s3_sync(path_to_copy: Path, skip_efs_sync: bool) -> bool:
    """
    Syncs files from a local directory to an S3 bucket.

    This function uses the AWS CLI to sync files from a local directory to an S3 bucket. It excludes any temporary files during the sync process. If the `skip_efs_sync` flag is not set, it also syncs the files to an EFS volume.

    :param path_to_copy: The path to the local directory to be synced to the S3 bucket.
    :type path_to_copy: Path
    :param skip_efs_sync: A flag indicating whether to skip syncing to the EFS volume.
    :type skip_efs_sync: bool
    :return: True if the sync operation was successful, False otherwise.
    :rtype: bool
    """

    # Load environment variables from .env file
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Log the start of the S3 sync process
    console.log(f"Syncing {path_to_copy} to S3")

    # Construct the AWS CLI command to sync files to the S3 bucket
    proc = Popen(
        [
            "aws",
            "s3",
            "sync",
            str(path_to_copy),
            env["S3"],
            "--exclude",
            "*.tmp",
            "--verbose",
            "--progress",
        ],
        stdout=PIPE,
        stderr=PIPE,
    )

    # Process the output of the AWS CLI command
    while True:
        output = proc.stderr.readline().strip()
        if output == b"":
            break
        else:
            console.log(output.decode("utf-8"))

    # Wait for the AWS CLI command to complete
    proc.wait()

    # Log the completion of the S3 sync process
    console.log(f"Syncing {path_to_copy} to S3: done")

    # If the skip_efs_sync flag is not set, sync the files to the EFS volume
    if not skip_efs_sync:
        sync_to_efs()

    return True


def sync_to_efs() -> bool:
    """
    Syncs files from an S3 bucket to an EFS volume.

    This function uses the AWS CLI to sync files from an S3 bucket to an EFS volume. It excludes any temporary files during the sync process.

    :return: True if the sync operation was successful, False otherwise.
    :rtype: bool
    """

    # Load environment variables from .env file
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Log the start of the EFS sync process
    console.log(f"Syncing {env['S3']} to {env['EFS']}")

    # Get the S3 and EFS paths from the environment variables
    s3_path = env.get("S3")
    efs_path = env.get("EFS")

    # Check if the S3 and EFS paths are not None
    if s3_path is not None and efs_path is not None:
        # If so, construct the AWS CLI command to sync files to the EFS volume
        proc = Popen(
            ["aws", "s3", "sync", s3_path, efs_path, "--exclude", "*.tmp"],
            stdout=PIPE,
            stderr=PIPE,
        )
    else:
        # If not, log that the S3 or EFS path is not defined in the environment variables
        console.log("S3 or EFS path is not defined in the environment variables")

    # Process the output of the AWS CLI command
    while True:
        # Read a line from stderr and decode it to utf-8
        if proc.stderr is not None:
            output = proc.stderr.readline().decode("utf-8").strip()
            # Process output further if needed
        else:
            # Handle the case when proc.stderr is None
            output = "No output available"
            console.log(output)

    # Wait for the AWS CLI command to complete
    proc.wait()

    # Log the completion of the EFS sync process
    console.log(f"Syncing {env['S3']} to {env['EFS']}: done")

    return True


def check_output(stdout, stderr) -> bool:
    """
    Checks the output of a command for errors.

    This function decodes the stderr output of a command and checks if it contains the string "Error". If "Error" is found, it logs the stderr output and returns False. Otherwise, it returns True.

    :param stdout: The stdout output of the command.
    :type stdout: bytes
    :param stderr: The stderr output of the command.
    :type stderr: bytes
    :return: True if no errors were found in the stderr output, False otherwise.
    :rtype: bool
    """

    # Decode the stderr output to utf-8
    stderr = stderr.decode("utf-8")

    # Check if the stderr output is not empty
    if len(stderr) > 1:
        # If so, check if the stderr output contains the string "Error"
        if stderr.find("Error") >= 1:
            # If "Error" is found, log the stderr output and return False
            console.log(stderr, style="blink bold white on red")
            return False

    # If no errors were found in the stderr output, return True
    return True


def slack_post(message: str) -> bool:
    """
    Posts a message to a Slack channel using a webhook.

    This function takes a message as input and posts it to a Slack channel using a webhook. The webhook URL is retrieved from the environment variables. The function returns True if the message was successfully posted.

    Note: This function is deprecated as it uses webhooks.

    :param message: The message to be posted to the Slack channel.
    :type message: str
    :return: True if the message was successfully posted, False otherwise.
    :rtype: bool
    """

    # Load environment variables from .env file
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Get the Slack webhook URL from the environment variables
    slack_channel = f"https://hooks.slack.com/services/{env['SLACK']}"

    # Create a WebhookClient object with the Slack webhook URL
    webhook = WebhookClient(slack_channel)

    # Send the message to the Slack channel using the webhook
    response = webhook.send(text=message)

    # Check if the message was successfully posted
    assert response.status_code == 200
    assert response.body == "ok"

    return True


def slack_message(messages: list, subject="Update") -> bool:
    """
    Sends a message to a Slack channel using the Slack API.

    This function takes a list of messages and a subject as input and posts them to a Slack channel using the Slack API. The Slack API token is retrieved from the environment variables. The function returns True if the message was successfully posted.

    :param messages: The list of messages to be posted to the Slack channel.
    :type messages: list
    :param subject: The subject of the message. By default, it's set to "Update".
    :type subject: str, optional
    :return: True if the message was successfully posted, False otherwise.
    :rtype: bool
    """

    # Load environment variables from .env file
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Create a WebClient object with the Slack API token
    client = WebClient(token=env["SLACK"])

    try:
        # Call the chat.postMessage method using the WebClient
        # This sends the message to the Slack channel
        response = client.chat_postMessage(
            channel="#blast-status",  # Channel to send message to
            text=subject,  # Subject of the message
            attachments=messages,
        )
        console.log("Done sending message to Slack channel")
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

    return True


def slack_post(message: str) -> bool:
    """
    deprecated as it uses webhooks
    """

    env = dotenv_values(f"{Path.cwd()}/.env")

    # move to .env eventually
    slack_channel = f"https://hooks.slack.com/services/{env['SLACK']}"
    webhook = WebhookClient(slack_channel)
    response = webhook.send(text=message)
    assert response.status_code == 200
    assert response.body == "ok"

    return True


def list_databases_from_config(config_file: str) -> None:
    """
    Lists all database names from either a YAML or JSON configuration file.

    Parameters:
    config_file (str): Path to either YAML or JSON configuration file
    """
    console.log("\n[bold]Available databases:[/bold]")

    if config_file.endswith(".yaml") or config_file.endswith(".yml"):
        # Load and process YAML file
        config = yaml.load(open(config_file), Loader=yaml.FullLoader)

        for provider in config["data_providers"]:
            console.log(f"\n[bold cyan]{provider['name']}:[/bold cyan]")
            for environment in provider["environments"]:
                json_file = (
                    Path(config_file).parent
                    / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
                )
                if json_file.exists():
                    db_coordinates = json.load(open(json_file, "r"))
                    for entry in db_coordinates["data"]:
                        console.log(f"  • {entry['blast_title']}")
                else:
                    console.log(f"  Warning: JSON file not found - {json_file}")

    elif config_file.endswith(".json"):
        # Load and process JSON file
        db_coordinates = json.load(open(config_file, "r"))
        for entry in db_coordinates["data"]:
            console.log(f"  • {entry['blast_title']}")
    else:
        console.log("[red]Error: Config file must be either YAML or JSON[/red]")


def needs_parse_seqids(fasta_file: str) -> bool:
    """
    Determines if a FASTA file needs the -parse_seqids flag by examining its headers.
    BLAST's -parse_seqids is needed when headers contain certain formats like:
    - lcl|123
    - gb|123|456
    - ref|NM_123.4|
    - etc.

    Parameters:
    fasta_file (str): Path to the FASTA file to examine

    Returns:
    bool: True if the file contains headers that need parsing, False otherwise
    """
    # Common sequence identifier patterns that need parsing
    id_patterns = [
        r"^>.*\|.*\|",  # Matches patterns like gb|123|456 or ref|NM_123.4|
        r"^>lcl\|",  # Local identifiers
        r"^>ref\|",  # Reference sequences
        r"^>gb\|",  # GenBank
        r"^>emb\|",  # EMBL
        r"^>dbj\|",  # DDBJ
        r"^>pir\|",  # PIR
        r"^>prf\|",  # Protein Research Foundation
        r"^>sp\|",  # Swiss-Prot
        r"^>pdb\|",  # Protein Data Bank
        r"^>pat\|",  # Patents
        r"^>bbs\|",  # GenInfo Backbone Id
        r"^>gnl\|",  # General database identifier
        r"^>gi\|",  # GenInfo Id
    ]

    # Compile patterns for efficiency
    patterns = [re.compile(pattern) for pattern in id_patterns]

    try:
        with open(fasta_file, "r") as f:
            # Only need to check header lines
            for line in f:
                if line.startswith(">"):
                    # Check if any pattern matches this header
                    if any(pattern.match(line) for pattern in patterns):
                        return True
    except Exception as e:
        # If there's any error reading the file, err on the side of caution
        console.log(f"Warning: Error checking FASTA headers: {e}")
        return True

    return False


def process_entry(entry, mod_code, file_logger, environment=None, check_only=False):
    """Helper function to process a single database entry"""
    fasta_file = Path(entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    # Only show checking message if in check mode
    if check_only:
        console.log(f"\n[bold]Checking {entry['blast_title']}[/bold]")

    # Download and verify the file
    if entry["uri"].startswith('ftp://'):
        success = get_files_ftp(entry["uri"], entry["md5sum"], file_logger, mod=mod_code)
    else:
        success = get_files_http(entry["uri"], entry["md5sum"], file_logger, mod=mod_code)

    if not success:
        if check_only:
            console.log(f"[red]Could not download {fasta_file} - skipping check[/red]")
        return

    # Unzip if needed
    if not Path(unzipped_fasta).exists():
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()

    # Check parse_seqids requirement
    if Path(unzipped_fasta).exists():
        needs_parse = needs_parse_seqids(unzipped_fasta)
        if check_only:
            status = "[green]requires[/green]" if needs_parse else "[yellow]does not require[/yellow]"
            console.log(f"{entry['blast_title']}: {status} -parse_seqids")

    # Clean up if we're only checking
    if check_only:
        if Path(unzipped_fasta).exists():
            Path(unzipped_fasta).unlink()

    # If not check_only, proceed with database creation
    if not check_only:
        output_dir, config_dir = create_db_structure(
            environment, mod_code, entry, file_logger
        )
        if not run_makeblastdb(entry, output_dir, file_logger):
            console.log(
                f"[red]Error creating database for {entry['blast_title']}[/red]"
            )


def process_json_entries(
    json_file, environment, mod=None, db_list=None, check_only=False
):
    """
    Process entries from a JSON configuration file.

    Parameters:
    json_file (str): Path to JSON configuration file
    environment (str): Environment name
    mod (str, optional): Model organism code
    db_list (list, optional): List of database names to process
    check_only (bool): If True, only check parse_seqids without creating databases

    Returns:
    bool: True if processing was successful, False otherwise
    """
    try:
        with open(json_file, "r") as f:
            db_coordinates = json.load(f)
    except json.JSONDecodeError as e:
        console.log(f"[red]Error: Invalid JSON file: {e}[/red]")
        return False

    mod_code = mod if mod is not None else get_mod_from_json(json_file)
    if not mod_code:
        console.log("[red]Error: Invalid or missing MOD code[/red]")
        return False

    date_to_add = datetime.now().strftime("%Y_%b_%d")
    Path("../logs").mkdir(parents=True, exist_ok=True)

    for entry in db_coordinates.get("data", []):
        if db_list and entry["blast_title"] not in db_list:
            continue

        log_path = f"../logs/{entry['genus']}_{entry['species']}_{entry['seqtype']}_{date_to_add}.log"
        file_logger = extendable_logger(entry["blast_title"], log_path)
        file_logger.info(f"Mod found/provided: {mod_code}")

        process_entry(entry, mod_code, file_logger, environment, check_only)

    return True


def process_files(config_yaml, input_json, environment, db_list=None, check_only=False):
    """
    Process files either from YAML or JSON configuration.

    Parameters:
    config_yaml (str): Path to YAML configuration file
    input_json (str): Path to JSON configuration file
    environment (str): Environment name
    db_list (list, optional): List of database names to process
    check_only (bool): If True, only check parse_seqids without creating databases
    """
    if config_yaml:
        config = yaml.load(open(config_yaml), Loader=yaml.FullLoader)
        for provider in config["data_providers"]:
            console.log(f"Processing {provider['name']}")
            for env in provider["environments"]:
                json_file = (
                    Path(config_yaml).parent
                    / f"{provider['name']}/databases.{provider['name']}.{env}.json"
                )
                if json_file.exists():
                    process_json_entries(
                        json_file, env, provider["name"], db_list, check_only
                    )

    elif input_json:
        process_json_entries(input_json, environment, None, db_list, check_only)


# In utils.py
def get_files_http(file_uri, md5sum, file_logger, mod=None) -> bool:
    """
    Function to download files from an HTTP/HTTPS site.

    Parameters:
    file_uri (str): The URI of the file that needs to be downloaded.
    md5sum (str): The MD5 checksum of the file.
    file_logger (logging.Logger): The logger object used for logging the process.
    mod (str, optional): Model organism identifier to determine if MD5 check should be skipped.

    Returns:
    bool: True if the file was successfully downloaded and verified (unless verification is skipped), False otherwise.
    """
    today_date = datetime.now().strftime("%Y_%b_%d")
    try:
        console.log(f"Downloading {file_uri}")
        file_name = f"../data/{Path(file_uri).name}"

        console.log(f"Saving to {file_name}")
        file_logger.info(f"Saving to {file_name}")

        if not Path(f"../data/database_{today_date}/{Path(file_uri).name}").exists():
            wget.download(file_uri, file_name)
            store_fasta_files(file_name, file_logger)
        else:
            console.log(f"{Path(file_uri).name} already processed")
            file_logger.info(f"{file_name} already processed")
            return False

        # Skip MD5 check for ZFIN
        if mod == "ZFIN":
            file_logger.info("Skipping MD5 check for ZFIN")
            console.log("Skipping MD5 check for ZFIN")
            return True

        if check_md5sum(file_name, md5sum):
            return True
        else:
            file_logger.info("MD5sums do not match")
            return False

    except Exception as e:
        console.log(f"Error downloading {file_uri}: {e}")
        return False


def get_files_ftp(fasta_uri, md5sum, file_logger, mod=None) -> bool:
    """
    Function to download files from an FTP site.

    Parameters:
    fasta_uri (str): The URI of the file that needs to be downloaded.
    md5sum (str): The MD5 checksum of the file.
    file_logger (logging.Logger): The logger object used for logging the process.
    mod (str, optional): Model organism identifier to determine if MD5 check should be skipped.

    Returns:
    bool: True if the file was successfully downloaded and verified (unless verification is skipped), False otherwise.
    """
    today_date = datetime.now().strftime("%Y_%b_%d")
    try:
        console.log(f"Downloading {fasta_uri}")
        fasta_file = f"../data/{Path(fasta_uri).name}"
        fasta_name = f"{Path(fasta_uri).name}"

        console.log(f"Saving to {fasta_file}")
        file_logger.info(f"Saving to {fasta_file}")

        if not Path(f"../data/database_{today_date}/{fasta_name}").exists():
            wget.download(fasta_uri, fasta_file)
            store_fasta_files(fasta_file, file_logger)
        else:
            console.log(f"{fasta_name} already processed")
            file_logger.info(f"{fasta_file} already processed")
            return False

        # Skip MD5 check for ZFIN
        if mod == "ZFIN":
            file_logger.info("Skipping MD5 check for ZFIN")
            console.log("Skipping MD5 check for ZFIN")
            return True

        if check_md5sum(fasta_file, md5sum):
            return True
        else:
            file_logger.info("MD5sums do not match")
            return False
    except Exception as e:
        console.log(f"Error downloading {fasta_uri}: {e}")
        return False

    return True


# def split_zfin_fasta(filename) -> Any:
#     """ """
#
#     fasta = open(filename).read().splitlines()
#     Path(f"{filename}.tmp").touch()
#
#     for line in fasta:
#         temp = line.split("\\n")
#         for item in temp:
#             with open(f"{filename}.tmp", "a") as fh:
#                 fh.write(f"{item}\n")
#
#     Path(filename).unlink()
#     Path(f"{filename}.tmp").rename(filename)
#
#     return True
