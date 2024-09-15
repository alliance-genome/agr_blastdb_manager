"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wright
Date: started September 2023
"""

import gzip
import hashlib
import logging
from ftplib import FTP
from logging.handlers import RotatingFileHandler
from pathlib import Path
from subprocess import PIPE, CalledProcessError, Popen, run
from typing import Any, List, Tuple

import requests
from dotenv import dotenv_values
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.webhook import WebhookClient

console = Console()

# Define LOGGER at the top of utils.py
LOGGER = logging.getLogger(__name__)

# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]


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


def check_output(stdout: bytes, stderr: bytes) -> bool:
    """
    Check the output of a subprocess for errors.

    Args:
        stdout (bytes): Standard output from the subprocess.
        stderr (bytes): Standard error from the subprocess.

    Returns:
        bool: True if no errors were found, False otherwise.
    """
    stderr_str = stderr.decode("utf-8")
    if stderr_str and "Error" in stderr_str:
        console.log(
            f"Error in subprocess output: {stderr_str}", style="blink bold white on red"
        )
        return False
    return True


def run_command(command: List[str]) -> Tuple[bool, str]:
    """
    Run a shell command and return its output.

    Args:
        command (List[str]): The command to run as a list of strings.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating success and the command output.
    """
    try:
        result = run(command, check=True, capture_output=True, text=True)
        return True, result.stdout
    except CalledProcessError as e:
        return False, f"Command failed with error: {e.stderr}"


def needs_parse_id(fasta_file: Path) -> bool:
    """
    Determine if the FASTA file needs parse_id option for makeblastdb.

    Args:
        fasta_file (Path): Path to the gzipped FASTA file

    Returns:
        bool: True if parse_id is needed, False otherwise
    """
    open_func = gzip.open if fasta_file.suffix == ".gz" else open
    mode = "rt" if fasta_file.suffix == ".gz" else "r"

    with open_func(fasta_file, mode) as f:
        headers = [next(f).strip() for _ in range(100) if next(f).startswith(">")]

    # Analyze headers here
    complex_headers = any("|" in header for header in headers)
    consistent_format = len(set(header.count("|") for header in headers)) == 1

    return complex_headers and consistent_format


def setup_logger(name, log_file, level=logging.INFO):
    """Function to set up a logger with file and console handlers."""
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # File Handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def slack_message(messages: list, subject="BLAST Database Update") -> bool:
    """
    Sends a message to a Slack channel using the Slack API.

    :param messages: The list of messages to be posted to the Slack channel.
    :type messages: list
    :param subject: The subject of the message. By default, it's set to "BLAST Database Update".
    :type subject: str, optional
    :return: True if the message was successfully posted, False otherwise.
    :rtype: bool
    """
    # Load environment variables from .env file
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Create a WebClient object with the Slack API token
    client = WebClient(token=env["SLACK"])

    try:
        for msg in messages:
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": subject, "emoji": True},
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": msg["text"]}},
                {"type": "divider"},
            ]

            # Call the chat.postMessage method using the WebClient
            response = client.chat_postMessage(
                channel="#blast-status",  # Channel to send message to
                blocks=blocks,
                text=subject,  # Fallback text for notifications
            )

        LOGGER.info("Successfully sent message to Slack channel")
        return True
    except SlackApiError as e:
        LOGGER.error(f"Error sending message to Slack: {e.response['error']}")
        return False


def get_ftp_file_size(fasta_uri: str) -> int:
    """
    Get the size of a file on an FTP server.

    Args:
        fasta_uri (str): The URI of the FASTA file on the FTP server.

    Returns:
        int: The size of the file in bytes, or 0 if size couldn't be determined.
    """
    try:
        ftp_parts = fasta_uri.split("/")
        ftp_server = ftp_parts[2]
        ftp_path = "/".join(ftp_parts[3:-1])
        filename = ftp_parts[-1]

        with FTP(ftp_server) as ftp:
            ftp.login()
            ftp.cwd(ftp_path)
            size = ftp.size(filename)

        if size is not None:
            console.log(f"File size for {filename} is {size} bytes")
            return size
        else:
            console.log(f"Couldn't determine size for {filename}")
            return 0

    except Exception as e:
        console.log(f"Error getting FTP file size: {e}")
        return 0


def get_https_file_size(https_uri: str) -> int:
    try:
        response = requests.head(https_uri, allow_redirects=True)
        if response.status_code == 200:
            size = int(response.headers.get("content-length", 0))
            console.log(f"File size for {https_uri} is {size} bytes")
            return size
        else:
            console.log(
                f"Couldn't determine size for {https_uri}. Status code: {response.status_code}"
            )
            return 0
    except Exception as e:
        console.log(f"Error getting HTTPS file size: {e}")
        return 0
