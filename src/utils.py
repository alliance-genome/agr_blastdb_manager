"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wright
Date: started September 2023
"""

from typing import Any

import hashlib
import logging
from ftplib import FTP
from pathlib import Path
from subprocess import PIPE, Popen

import boto3
from Bio import SeqIO # type: ignore
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

    :param fasta_uri:
    :param file_logger:
    """
    size = 0

    ftp = FTP(Path(fasta_uri).parts[1])
    ftp.login()
    ftp.cwd("/".join(Path(fasta_uri).parts[2:-1]))
    filename = Path(fasta_uri).name
    if filename is not None:
        size = ftp.size(filename)
        if size is not None:
            # Proceed with the value of size
            print("File size:", size)
        else:
            # Handle the case where size is None
            print("Error: File size is not available.")
            return 0
    else:
        print("Error: Filename is None.")
        size = ftp.size(filename)
        console.log(f"File size is {size} bytes")
        file_logger.info(f"File size is {size} bytes")
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


def route53_check() -> bool:
    """
    Function that checks if the route53 record exists
    """

    client53 = boto3.client("route53")
    response = client53.list_resource_record_sets(
        HostedZoneId="alliancegenome.org", StartRecordType="TXT"
    )
    print(response)

    return True

def edit_fasta(fasta_file: str, config_entry: dict) -> bool:
    """

    :param fasta_file:
    """

    original_file = []
    with open(fasta_file, "r") as fh:
        lines = fh.readlines()
        for line in lines:
            if line.startswith(">"):
                line = line.strip()
                if "seqcol" in config_entry.keys():
                    line += f" {config_entry['seqcol']} {config_entry['genus']} {config_entry['species']}\n"
                else:
                    line += f" {config_entry['genus']} {config_entry['species']} {config_entry['version']}\n"
                original_file.append(line)
            else:
                original_file.append(line)

    edited_file = open(fasta_file, "w")
    edited_file.writelines(original_file)
    edited_file.close()

    return True


def validate_fasta(filename) -> Any:
    """
    Function that validates the FASTA file
    """

    with open(filename, "r") as handle:
        fasta = SeqIO.parse(handle, "fasta")
        return any(fasta)


def split_zfin_fasta(filename) -> Any:
    """ """

    fasta = open(filename).read().splitlines()
    Path(f"{filename}.tmp").touch()

    for line in fasta:
        temp = line.split("\\n")
        for item in temp:
            with open(f"{filename}.tmp", "a") as fh:
                fh.write(f"{item}\n")

    Path(filename).unlink()
    Path(f"{filename}.tmp").rename(filename)

    return True


def s3_sync(path_to_copy: Path, skip_efs_sync: bool) -> bool:
    """ """

    env = dotenv_values(f"{Path.cwd()}/.env")

    console.log(f"Syncing {path_to_copy} to S3")
    proc = Popen(
        ["aws", "s3", "sync", str(path_to_copy), env["S3"], "--exclude", "*.tmp"],
        stdout=PIPE,
        stderr=PIPE,
    )
    while True:
        output = proc.stderr.readline().strip()
        if output == b"":
            break
        else:
            console.log(output.decode("utf-8"))
    proc.wait()
    console.log(f"Syncing {path_to_copy} to S3: done")

    if not skip_efs_sync:
        sync_to_efs()

    return True

def sync_to_efs() -> bool:
    """Sync files from an S3 bucket to an EFS volume."""

    env = dotenv_values(f"{Path.cwd()}/.env")

    console.log(f"Syncing {env['S3']} to {env['EFS']}")
    s3_path = env.get("S3")
    efs_path = env.get("EFS")

    if s3_path is not None and efs_path is not None:
        proc = Popen(
            ["aws", "s3", "sync", s3_path, efs_path, "--exclude", "*.tmp"],
            stdout=PIPE,
            stderr=PIPE,
        )
    else:
        console.log("S3 or EFS path is not defined in the environment variables")

    while True:
        # Read a line from stderr and decode it to utf-8
        if proc.stderr is not None:
            output = proc.stderr.readline().decode("utf-8").strip()
            # Process output further if needed
        else:
            # Handle the case when proc.stderr is None
            # For example:
            output = "No output available"
            console.log(output)

    # Wait for the process to complete
    proc.wait()
    console.log(f"Syncing {env['S3']} to {env['EFS']}: done")

    return True

def check_output(stdout, stderr) -> bool:
    """ """

    stderr = stderr.decode("utf-8")
    if len(stderr) > 1:
        if stderr.find("Error") >= 1:
            console.log(stderr.decode("utf-8"), style="blink bold white on red")
            return False

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


def slack_message(messages: list, subject="Update") -> bool:
    """
    Function that sends a message to Slack
    :param message:
    """

    env = dotenv_values(f"{Path.cwd()}/.env")
    client = WebClient(token=env["SLACK"])

    try:
        # Call the chat.postMessage method using the WebClient
        response = client.chat_postMessage(
            channel="#blast-status",  # Channel to send message to
            text=subject,  # Subject of the message
            attachments=messages,
        )
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

    return True
