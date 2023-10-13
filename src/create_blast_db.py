# Paulo Nuin July 2023


import json
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from subprocess import PIPE, Popen

import boto3
import click
import wget
import yaml
from dotenv import dotenv_values
from rich.console import Console

from utils import (check_md5sum, edit_fasta, extendable_logger,
                   get_ftp_file_size, get_mod_from_json, route53_check,
                   s3_sync, split_zfin_fasta, validate_fasta)

console = Console()



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

    Path(p).mkdir(parents=True, exist_ok=True)
    console.log(f"Directory {p} created")
    file_logger.info(f"Directory {p} created")

    return p


def run_makeblastdb(config_entry, output_dir, file_logger):
    """
    Function that runs makeblastdb
    :param config_entry:
    :param output_dir:
    :param dry_run:
    :param file_logger:
    """

    env = dotenv_values(f"{Path.cwd()}/.env")

    fasta_file = Path(config_entry["uri"]).name
    console.log(f"Running makeblastdb for {fasta_file}")

    if not Path(f"../data/{fasta_file.replace('.gz', '')}").exists():
        file_logger.info(f"Unzipping {fasta_file}")
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        console.log("Unzip: done\nEditing FASATA file")
        file_logger.info(f"Unzipping {fasta_file}: done")

    if config_entry["taxon_id"] == "NCBITaxon:7955":
        console.log("Editing ZFIN FASTA file")
        split_zfin_fasta(f"../data/{fasta_file.replace('.gz', '')}")

    edit_fasta(f"../data/{fasta_file.replace('.gz', '')}", config_entry)
    try:
        makeblast_command = (
            f"{env['MAKEBLASTDB_BIN']} -in ../data/{fasta_file.replace('.gz', '')} -dbtype {config_entry['seqtype']} "
            f"-title '{config_entry['blast_title']}' -parse_seqids "
            f"-out {output_dir}/{fasta_file.replace('fa.gz', 'db ')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
        )
        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        console.log(f"Running makeblastdb: {makeblast_command}")
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        p.wait()

        console.log(stdout.decode("utf-8"))
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


def process_yaml(config_yaml) -> bool:
    """
    Function that processes the YAML file

    :param config_yaml:
    """

    config = yaml.load(open(config_yaml), Loader=yaml.FullLoader)

    for provider in config["data_providers"]:
        console.log(f"Processing {provider['name']}")
        for environment in provider["environments"]:
            console.log(f"Processing {environment}")
            json_file = (
                Path(config_yaml).parent
                / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
            )
            console.log(f"Processing {json_file}")
            process_json(json_file, environment, provider["name"])



def process_json(json_file, environment, mod) -> bool:
    """

    :param json_file:
    :param environment:
    :param mod:

    """

    date_to_add = datetime.now().strftime("%Y_%b_%d")
    console.log(f"Processing {json_file}")

    if mod is None:
        mod_code = get_mod_from_json(json_file)
    else:
        mod_code = mod

    if mod_code is not False:
        db_coordinates = json.load(open(json_file, "r"))
        for entry in db_coordinates["data"]:
            file_logger = extendable_logger(
                entry["blast_title"],
                f"../logs/{entry['genus']}_{entry['species']}"
                f"_{entry['seqtype']}_{date_to_add}.log",
            )
            file_logger.info(f"Mod found/provided: {mod_code}")
            if get_files_ftp(entry["uri"], entry["md5sum"], file_logger):
                output_dir = create_db_structure(
                    environment, mod_code, entry, file_logger
                )
                if Path(output_dir).exists():
                    run_makeblastdb(entry, output_dir, file_logger)


@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option("-r", "--check_route53", help="Check Route53", is_flag=True, default=False)
@click.option("-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False)
# @click.option("-d", "--dry_run", help="Don't download anything", is_flag=True, default=False)
def create_dbs(config_yaml, input_json, environment, mod, check_route53, skip_efs_sync
    """
    Function that runs the pipeline
    :param input_json:
    :param dry_run:
    :param environment:
    :param mod:
    :return:
    """

    if len(sys.argv) == 1:
        click.main(["--help"])
    if config_yaml is not None:
        process_yaml(config_yaml)
    elif check_route53:
        console.log("Checking Route53")
        route53_check()
    else:
        process_json(input_json, environment, mod)

    s3_sync(Path("../data"), skip_efs_sync)

if __name__ == "__main__":
    create_dbs()
