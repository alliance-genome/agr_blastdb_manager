"""
create_blast_db.py

This script is used to create BLAST databases from FASTA files. It includes functions to download files from an FTP site,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in YAML and JSON formats.

Authors: Paulo Nuin, Adam Wright
Date: started July 2023
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile, rmtree
from subprocess import PIPE, Popen

import click
import yaml
from dotenv import dotenv_values
from rich.console import Console

from utils import (check_md5sum, setup_enhanced_logger, get_files_ftp,
                  get_files_http, get_mod_from_json,
                  list_databases_from_config, needs_parse_seqids,
                  process_files, s3_sync, slack_message, store_fasta_files,
                  check_output)

console = Console()

slack_messages = []


def create_db_structure(environment, mod, config_entry, file_logger) -> tuple[str, str]:
    """
    Function that creates the database and folder structure for storing the downloaded FASTA files.
    """
    blast_title = config_entry["blast_title"]
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)
    file_logger.info("Creating database structure")

    if "seqcol" in config_entry.keys():
        file_logger.info("seqcol found in config file")
        p = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/"
    else:
        file_logger.info("seqcol not found in config file")
        p = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{sanitized_blast_title.replace(' ', '_')}/"
        )
    c = f"../data/config/{mod}/{environment}"

    Path(p).mkdir(parents=True, exist_ok=True)
    Path(c).mkdir(parents=True, exist_ok=True)

    console.log(f"Directory {p} created")
    file_logger.info(f"Directory {p} created")

    return p, c


def run_makeblastdb(config_entry, output_dir, file_logger):
    """
    This function runs the makeblastdb command to create a BLAST database.
    """
    env = dotenv_values(f"{Path.cwd()}/.env")
    fasta_file = Path(config_entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    console.log(f"Running makeblastdb for {fasta_file}")
    slack_messages.append(
        {"title": "Running makeblastdb", "text": fasta_file, "color": "#36a64f"},
    )

    if not Path(unzipped_fasta).exists():
        file_logger.info(f"Unzipping {fasta_file}")
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        console.log("Unzip: done\nEditing FASTA file")
        file_logger.info(f"Unzipping {fasta_file}: done")

    parse_ids_flag = ""
    if needs_parse_seqids(unzipped_fasta):
        parse_ids_flag = "-parse_seqids"
        file_logger.info("FASTA headers require -parse_seqids flag")
        console.log("FASTA headers require -parse_seqids flag")

    blast_title = config_entry["blast_title"]
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)
    extensions = "".join(Path(fasta_file).suffixes)

    try:
        makeblast_command = (
            f"makeblastdb -in {unzipped_fasta} -dbtype {config_entry['seqtype']} "
            f"-title '{sanitized_blast_title}' "
            f"-out {output_dir}/{fasta_file.replace(extensions, 'db')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
            f"{parse_ids_flag}"
        ).strip()

        file_logger.info(f"Running makeblastdb: {makeblast_command}")
        console.log(f"Running makeblastdb:\n {makeblast_command}")

        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        p.wait()

        if check_output(stdout, stderr):
            console.log("Makeblastdb: done")
            slack_messages.append(
                {
                    "title": "Makeblastdb completed",
                    "text": fasta_file,
                    "color": "#36a64f",
                },
            )
            file_logger.info("Makeblastdb: done")

            Path(unzipped_fasta).unlink()
            file_logger.info(f"Removed {fasta_file.replace('.gz', '')}")
            console.log("Removed unzipped file")
        else:
            console.log("Error running makeblastdb")
            slack_messages.append(
                {
                    "title": "Error running makeblastdb",
                    "text": fasta_file,
                    "color": "#8D2707",
                },
            )
            file_logger.info("Error running makeblastdb")
            console.log("Removing folders")
            rmtree(output_dir)
            return False
    except Exception as e:
        console.log(f"Error running makeblastdb: {e}")
        slack_messages.append(
            {
                "title": "Error running makeblastdb",
                "text": fasta_file,
                "color": "#8D2707",
            },
        )
        file_logger.info(f"Error running makeblastdb: {e}")
        return False

    return True


def process_entry(entry, mod_code, file_logger, environment=None, check_only=False, keep_files=False):
    """Helper function to process a single database entry"""
    fasta_file = Path(entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"
    downloaded_file = f"../data/{fasta_file}"

    try:
        # Only show checking message if in check mode
        if check_only:
            console.log(f"\n[bold]Checking {entry['blast_title']}[/bold]")

        # Download and verify the file
        if entry["uri"].startswith('ftp://'):
            success = get_files_ftp(entry["uri"], entry["md5sum"], file_logger, mod=mod_code, keep_files=keep_files)
        else:
            success = get_files_http(entry["uri"], entry["md5sum"], file_logger, mod=mod_code, keep_files=keep_files)

        if not success:
            if check_only:
                console.log(f"[red]Could not download {fasta_file} - skipping check[/red]")
            return

        # Process the database
        if not check_only:
            output_dir, config_dir = create_db_structure(
                environment, mod_code, entry, file_logger
            )
            if not run_makeblastdb(entry, output_dir, file_logger):
                console.log(
                    f"[red]Error creating database for {entry['blast_title']}[/red]"
                )
                return

        # Clean up files if not keeping them
        if not keep_files and Path(downloaded_file).exists():
            file_logger.info(f"Removing downloaded file: {downloaded_file}")
            Path(downloaded_file).unlink()
            console.log(f"Removed {downloaded_file}")

        if not keep_files and Path(unzipped_fasta).exists():
            file_logger.info(f"Removing unzipped file: {unzipped_fasta}")
            Path(unzipped_fasta).unlink()
            console.log(f"Removed {unzipped_fasta}")

    except Exception as e:
        file_logger.error(f"Error processing {entry['blast_title']}: {str(e)}")
        console.log(f"[red]Error processing {entry['blast_title']}: {str(e)}[/red]")
        raise


@click.command()
@click.option("-g", "--config_yaml", help="YAML file with all MODs configuration")
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-e", "--environment", help="Environment", default="dev")
@click.option("-m", "--mod", help="Model organism")
@click.option(
    "-s", "--skip_efs_sync", help="Skip EFS sync", is_flag=True, default=False
)
@click.option("-u", "--update-slack", help="Update Slack", is_flag=True, default=False)
@click.option("-s3", "--sync-s3", help="Sync to S3", is_flag=True, default=False)
@click.option(
    "-d",
    "--db_names",
    help="Comma-separated list of database names to create",
    default=None,
)
@click.option(
    "-l",
    "--list",
    "list_dbs",
    help="List available databases",
    is_flag=True,
    default=False,
)
@click.option(
    "-c",
    "--check-parse-seqids",
    help="Only check if files need parse_seqids",
    is_flag=True,
    default=False,
)
@click.option(
    "-k",
    "--keep-files",
    help="Keep downloaded FASTA files after processing",
    is_flag=True,
    default=False,
)
def create_dbs(
    config_yaml,
    input_json,
    environment,
    mod,
    skip_efs_sync,
    update_slack,
    sync_s3,
    db_names,
    list_dbs,
    check_parse_seqids,
    keep_files,
) -> None:
    """
    Main function that runs the pipeline for processing the configuration files and creating the BLAST databases.
    """
    db_list = None
    if db_names:
        db_list = [name.strip() for name in db_names.split(",")]

    if list_dbs:
        if config_yaml:
            list_databases_from_config(config_yaml)
        elif input_json:
            list_databases_from_config(input_json)
        else:
            click.echo(
                "Please provide either a YAML (-g) or JSON (-j) configuration file to list databases."
            )
        return

    try:
        if config_yaml:
            process_files(config_yaml, None, None, db_list, check_parse_seqids, keep_files)
        elif input_json:
            process_files(None, input_json, environment, db_list, check_parse_seqids, keep_files)

        if update_slack and not check_parse_seqids:
            slack_message(slack_messages)

        if sync_s3 and not check_parse_seqids:
            s3_sync(Path("../data"), skip_efs_sync)

    except Exception as e:
        console.log(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    create_dbs()