"""
create_blast_db.py

This script creates BLAST databases from FASTA files. It includes functions to download files from an FTP site,
store the downloaded FASTA files, create the database and folder structure, run the makeblastdb command, and process
configuration files in YAML and JSON formats.

Authors: Paulo Nuin, Adam Wright
Date: Started July 2023, Refactored [Current Date]
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from subprocess import PIPE, Popen

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TaskID,
                           TextColumn)
from rich.style import Style
from rich.table import Table

from utils import (check_md5sum, check_output, extendable_logger,
                   get_files_ftp, get_files_http, get_mod_from_json,
                   needs_parse_seqids, s3_sync, slack_message,
                   store_fasta_files)

console = Console()

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
LOGGER = setup_logger("create_blast_db", "blast_db_creation.log")


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
    LOGGER.info(f"Directory {db_path} created")

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
                "title": "Makeblastdb completed",
                "text": f"Successfully processed {fasta_file}",
            }
        )
        return True
    else:
        LOGGER.error(f"Error running makeblastdb: {output}")
        SLACK_MESSAGES.append(
            {"title": "Makeblastdb Error", "text": f"Failed to process {fasta_file}"}
        )
        file_logger.info(f"Error running makeblastdb: {e}")
        return False


def list_databases_from_config(config_file: str) -> None:
    """
    Lists all database names from either a YAML or JSON configuration file.
    """
    console.log("\n[bold]Available databases:[/bold]")

    if config_file.endswith(".yaml") or config_file.endswith(".yml"):
        config = yaml.load(open(config_file), Loader=yaml.FullLoader)

        for provider in config["data_providers"]:
            console.log(f"\n[bold cyan]{provider['name']}:[/bold cyan]")
            for environment in provider["environments"]:
                json_file = (
                    Path(config_file).parent
                    / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
                )
                if json_file.exists():
                    db_coordinates = json.load(open(json_file, "r"))
                    for entry in db_coordinates["data"]:
                        console.log(f"  • {entry['blast_title']}")
                else:
                    console.log(f"  Warning: JSON file not found - {json_file}")

    elif config_file.endswith(".json"):
        db_coordinates = json.load(open(config_file, "r"))
        for entry in db_coordinates["data"]:
            console.log(f"  • {entry['blast_title']}")
    else:
        console.log("[red]Error: Config file must be either YAML or JSON[/red]")


def process_entry(entry, mod_code, file_logger, environment=None, check_only=False):
    """Helper function to process a single database entry"""
    fasta_file = Path(entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    if check_only:
        console.log(f"\n[bold]Checking {entry['blast_title']}[/bold]")

    if entry["uri"].startswith("ftp://"):
        success = get_files_ftp(
            entry["uri"], entry["md5sum"], file_logger, mod=mod_code
        )
    else:
        success = get_files_http(
            entry["uri"], entry["md5sum"], file_logger, mod=mod_code
        )

    if not success:
        if check_only:
            console.log(f"[red]Could not download {fasta_file} - skipping check[/red]")
        return

    if not Path(unzipped_fasta).exists():
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()

    if Path(unzipped_fasta).exists():
        needs_parse = needs_parse_seqids(unzipped_fasta)
        if check_only:
            status = (
                "[green]requires[/green]"
                if needs_parse
                else "[yellow]does not require[/yellow]"
            )
            console.log(f"{entry['blast_title']}: {status} -parse_seqids")

    if check_only:
        if Path(unzipped_fasta).exists():
            Path(unzipped_fasta).unlink()

    if not check_only:
        output_dir, config_dir = create_db_structure(
            environment, mod_code, entry, file_logger
        )
        if not run_makeblastdb(entry, output_dir, file_logger):
            console.log(
                f"[red]Error creating database for {entry['blast_title']}[/red]"
            )


def process_json_entries(
    json_file, environment, mod=None, db_list=None, check_only=False
):
    """
    Process entries from a JSON configuration file.
    """
    try:
        with open(json_file, "r") as f:
            db_coordinates = json.load(f)
    except json.JSONDecodeError as e:
        console.log(f"[red]Error: Invalid JSON file: {e}[/red]")
        return False

    mod_code = mod if mod is not None else get_mod_from_json(json_file)
    if not mod_code:
        console.log("[red]Error: Invalid or missing MOD code[/red]")
        return False

    date_to_add = datetime.now().strftime("%Y_%b_%d")
    Path("../logs").mkdir(parents=True, exist_ok=True)

    for entry in db_coordinates.get("data", []):
        if db_list and entry["blast_title"] not in db_list:
            continue

        log_path = f"../logs/{entry['genus']}_{entry['species']}_{entry['seqtype']}_{date_to_add}.log"
        file_logger = extendable_logger(entry["blast_title"], log_path)
        file_logger.info(f"Mod found/provided: {mod_code}")

        process_entry(entry, mod_code, file_logger, environment, check_only)

    return True


def process_files(config_yaml, input_json, environment, db_list=None, check_only=False):
    """
    Process files either from YAML or JSON configuration.
    """
    if config_yaml:
        config = yaml.load(open(config_yaml), Loader=yaml.FullLoader)
        for provider in config["data_providers"]:
            console.log(f"Processing {provider['name']}")
            for env in provider["environments"]:
                json_file = (
                    Path(config_yaml).parent
                    / f"{provider['name']}/databases.{provider['name']}.{env}.json"
                )
                if json_file.exists():
                    process_json_entries(
                        json_file, env, provider["name"], db_list, check_only
                    )

    elif input_json:
        process_json_entries(input_json, environment, None, db_list, check_only)


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

    if len(sys.argv) == 1:
        click.echo(create_dbs.get_help(ctx=None))
        return

    try:
        if config_yaml:
            process_files(config_yaml, None, None, db_list, check_parse_seqids)
        elif input_json:
            process_files(None, input_json, environment, db_list, check_parse_seqids)

        if update_slack and not check_parse_seqids:
            slack_message(slack_messages)

        if sync_s3 and not check_parse_seqids:
            s3_sync(Path("../data"), skip_efs_sync)

    except Exception as e:
        console.log(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    create_dbs()
