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
from shutil import copyfile
from subprocess import PIPE, Popen
from typing import Any

import wget
import yaml
from dotenv import dotenv_values
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.webhook import WebhookClient

console = Console()

# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]


def store_fasta_files(fasta_file, file_logger) -> None:
    """
    Function to store the downloaded FASTA files in a specific directory.
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
    """
    size = 0
    ftp = FTP(Path(fasta_uri).parts[1])
    ftp.login()
    ftp.cwd("/".join(Path(fasta_uri).parts[2:-1]))
    filename = Path(fasta_uri).name

    if filename is not None:
        size = ftp.size(filename)
        if size is not None:
            console.log(f"File size is {size} bytes")
            file_logger.info(f"File size is {size} bytes")
        else:
            console.log("Error: File size is not available.")
            return 0
    else:
        console.log("Error: Filename is None.")
        return 0

    return size


def get_mod_from_json(input_json) -> str | bool:
    """
    Retrieves the model organism (mod) from the input JSON file.
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


def validate_fasta(filename: str) -> bool:
    """
    Validates if a file is in FASTA format without using Biopython.
    """
    try:
        with open(filename, "r") as f:
            first_line = f.readline().strip()
            if not first_line:
                return False

            if not first_line.startswith(">"):
                return False

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
    """
    env = dotenv_values(f"{Path.cwd()}/.env")
    console.log(f"Syncing {path_to_copy} to S3")

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
    """
    Syncs files from an S3 bucket to an EFS volume.
    """
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
        return False

    while True:
        if proc.stderr is not None:
            output = proc.stderr.readline().decode("utf-8").strip()
            if not output:
                break
            console.log(output)
        else:
            break

    proc.wait()
    console.log(f"Syncing {env['S3']} to {env['EFS']}: done")
    return True


def check_output(stdout, stderr) -> bool:
    """
    Checks the output of a command for errors.
    """
    stderr = stderr.decode("utf-8")
    if len(stderr) > 1:
        if stderr.find("Error") >= 1:
            console.log(stderr, style="blink bold white on red")
            return False
    return True


def slack_message(messages: list, subject="Update") -> bool:
    """
    Sends a message to a Slack channel using the Slack API.
    """
    env = dotenv_values(f"{Path.cwd()}/.env")
    client = WebClient(token=env["SLACK"])

    try:
        response = client.chat_postMessage(
            channel="#blast-status",
            text=subject,
            attachments=messages,
        )
        console.log("Done sending message to Slack channel")
    except SlackApiError as e:
        assert e.response["ok"] is False
        assert e.response["error"]
        print(f"Got an error: {e.response['error']}")

    return True


def needs_parse_seqids(fasta_file: str) -> bool:
    """
    Determines if a FASTA file needs the -parse_seqids flag by examining its headers.
    """
    id_patterns = [
        r"^>.*\|.*\|",
        r"^>lcl\|",
        r"^>ref\|",
        r"^>gb\|",
        r"^>emb\|",
        r"^>dbj\|",
        r"^>pir\|",
        r"^>prf\|",
        r"^>sp\|",
        r"^>pdb\|",
        r"^>pat\|",
        r"^>bbs\|",
        r"^>gnl\|",
        r"^>gi\|",
    ]

    patterns = [re.compile(pattern) for pattern in id_patterns]

    try:
        with open(fasta_file, "r") as f:
            for line in f:
                if line.startswith(">"):
                    if any(pattern.match(line) for pattern in patterns):
                        return True
    except Exception as e:
        console.log(f"Warning: Error checking FASTA headers: {e}")
        return True

    return False


def get_files_http(file_uri, md5sum, file_logger, mod=None) -> bool:
    """
    Function to download files from an HTTP/HTTPS site.
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
