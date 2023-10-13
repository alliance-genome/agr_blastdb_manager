# Paulo Nuin Sep 2023

import hashlib
import logging
from ftplib import FTP
from pathlib import Path
from subprocess import PIPE, Popen

import boto3
from Bio import SeqIO
from dotenv import dotenv_values
from rich.console import Console

console = Console()


# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]

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


def validate_fasta(filename):
    """
    Function that validates the FASTA file
    """

    with open(filename, "r") as handle:
        fasta = SeqIO.parse(handle, "fasta")
        return any(fasta)


def split_zfin_fasta(filename):
    """

    """

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
    """

    """

    env = dotenv_values(f"{Path.cwd()}/.env")

    console.log(f"Syncing {path_to_copy} to S3")
    proc = Popen(["aws", "s3", "sync", str(path_to_copy), env['S3'], "--exclude", "*.tmp"], stdout=PIPE, stderr=PIPE)
    while True:
        output = proc.stderr.readline().strip()
        if output == b"":
            break
        else:
            console.log(output.decode("utf-8"))
    proc.wait()
    console.log(f"Syncing {path_to_copy} to S3: done")

    if skip_efs_sync:
        sync_to_efs()


def sync_to_efs():
    """

    """

    env = dotenv_values(f"{Path.cwd()}/.env")

    console.log(f"Syncing {env['EFS']} to {env['FMS']}")
    proc = Popen(["aws", "s3", "sync", env["S3"], env["EFS"], "--exclude", "*.tmp"], stdout=PIPE, stderr=PIPE)
    while True:
        output = proc.stderr.readline().strip()
        if output == b"":
            break
        else:
            console.log(output.decode("utf-8"))
    proc.wait()
    console.log(f"Syncing {env['EFS']} to {env['FMS']}: done")