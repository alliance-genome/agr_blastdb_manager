# Paulo Nuin Sep 2023

import hashlib
import logging
from ftplib import FTP
from pathlib import Path

from rich.console import Console

import boto3
console = Console()


def extendable_logger(log_name, file_name, level=logging.INFO):
    """
    Function that creates a logger that can be extended
    :param log_name:
    :param file_name:
    :param level:
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
    Function that checks the md5sum of the downloaded file
    :param fasta_file:
    :param md5sum:
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
    Function that gets the mod from the JSON file
    :param input_json:
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