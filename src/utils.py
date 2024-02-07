"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wrioght
Date: started September 2023
"""


import hashlib
import logging
from ftplib import FTP
from pathlib import Path

from rich.console import Console

import boto3
console = Console()


# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]

def extendable_logger(log_name, file_name, level=logging.INFO):
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
    else:
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
    size = ftp.size(filename)
    console.log(f"File size is {size} bytes")
    file_logger.info(f"File size is {size} bytes")

    return size


def get_mod_from_json(input_json) -> str:
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

    client53 = boto3.client('route53')
    response = client53.list_resource_record_sets(
        HostedZoneId='alliancegenome.org',
        StartRecordType='TXT'
    )
    print(response)


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
