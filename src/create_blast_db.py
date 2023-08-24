# Paulo Nuin July 2023


import hashlib
import json
import logging
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from subprocess import PIPE, Popen
from ftplib import FTP
import wget

from tqdm import tqdm
import click
from rich.console import Console

console = Console()
MAKEBLASTDB_BIN = "/usr/local/bin/makeblastdb"
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


def get_files_ftp(fasta_uri, md5sum, dry_run, file_logger) -> bool:
    """
    Function that downloads the files from the FTP site
    :param fasta_uri:
    :param md5sum:
    :param dry_run:
    :return:
    """

    file_logger.info(f"Downloading {fasta_uri}")

    size = get_ftp_file_size(fasta_uri, file_logger)

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


def create_db_structure(environment, mod, config_entry, dry_run, file_logger) -> bool:
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

    Path(p).mkdir(parents=True, exist_ok=True)
    console.log(f"Directory {p} created")
    file_logger.info(f"Directory {p} created")

    return p


def run_makeblastdb(config_entry, output_dir, dry_run, file_logger):
    """
    Function that runs makeblastdb
    :param config_entry:
    :param output_dir:
    :param dry_run:
    :param file_logger:
    """

    fasta_file = Path(config_entry["uri"]).name
    console.log(f"Running makeblastdb for {fasta_file}")

    if not Path(f"../data/{fasta_file.replace('.gz', '')}").exists():
        file_logger.info(f"Unzipping {fasta_file}")
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        console.log("Unzip: done")
        file_logger.info(f"Unzipping {fasta_file}: done")
        console.log("File already unzipped")

    try:
        makeblast_command = (
            f"{MAKEBLASTDB_BIN} -in ../data/{fasta_file.replace('.gz', '')} -dbtype {config_entry['seqtype']} "
            f"-title '{config_entry['blast_title']}' -parse_seqids "
            f"-out {output_dir}/{fasta_file.replace('fa.gz', 'db ')}"
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
        )
        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        stdout, stderr = p.communicate()
        console.log("Makeblastdb: done")
        file_logger.info("Makeblastdb: done")
        Path(f"../data/{fasta_file.replace('.gz', '')}").unlink()
        file_logger.info(f"Removed {fasta_file.replace('.gz', '')}")
        console.log("Removed unzipped file")
    except Exception as e:
        console.log(f"Error running makeblastdb: {e}")
        file_logger.info(f"Error running makeblastdb: {e}")
        return False

    return True


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


@click.command()
# @click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="prod")
@click.option("-m", "--mod", help="Model organism")
@click.option(
    "-d", "--dry_run", help="Don't download anything", is_flag=True, default=False
)
def create_dbs(input_json, dry_run, environment, mod):
    """
    Function that runs the pipeline
    :param input_json:
    :param dry_run:
    :param environment:
    :param mod:
    :return:
    """

    date_to_add = datetime.now().strftime("%Y_%b_%d")

    if len(sys.argv) == 1:
        click.main(["--help"])
    else:
        if mod is None:
            mod_code = get_mod_from_json(input_json)

        if mod_code is not False:
            db_coordinates = json.load(open(input_json, "r"))
            for entry in db_coordinates["data"]:
                file_logger = extendable_logger(
                    entry["blast_title"],
                    f"../logs/{entry['genus']}_{entry['species']}"
                    f"_{entry['seqtype']}_{date_to_add}.log",
                )
                file_logger.info(f"Mod found/provided: {mod_code}")

                if get_files_ftp(entry["uri"], entry["md5sum"], dry_run, file_logger):
                    output_dir = create_db_structure(
                        environment, mod_code, entry, dry_run, file_logger
                    )
                    if Path(output_dir).exists():
                        run_makeblastdb(entry, output_dir, dry_run, file_logger)
        else:
            console.log("Mod not found")
            sys.exit(1)


if __name__ == "__main__":
    create_dbs()
