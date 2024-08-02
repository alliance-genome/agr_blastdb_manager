"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wright
Date: started September 2023
"""

import hashlib
import logging
from ftplib import FTP
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any

from Bio import SeqIO  # type: ignore
from dotenv import dotenv_values
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.webhook import WebhookClient

console = Console()


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


def validate_fasta(filename) -> Any:
    """
    Function that validates the FASTA file
    """

    with open(filename, "r") as handle:
        fasta = SeqIO.parse(handle, "fasta")
        return any(fasta)


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

