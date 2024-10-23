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
import sys
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Optional, Tuple

import click
import yaml
from rich.console import Console

from utils import (check_output, extendable_logger, get_files_ftp,
                   get_files_http, get_mod_from_json, needs_parse_seqids,
                   s3_sync)
from utils import setup_detailed_logger as setup_logger
from utils import slack_message, update_genome_browser_map

console = Console()

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
LOGGER = setup_logger("create_blast_db", "blast_db_creation.log")


def create_db_structure(
    environment: str, mod: str, config_entry: Dict, logger
) -> Tuple[str, str]:
    """
    Creates the database and folder structure for storing the BLAST databases.

    Args:
        environment: The deployment environment (dev, stage, prod)
        mod: The model organism database identifier
        config_entry: Configuration dictionary containing database details
        logger: Logger instance for tracking operations

    Returns:
        Tuple containing paths to database and config directories
    """
    start_time = datetime.now()
    logger.info(
        f"Starting database structure creation for {config_entry['blast_title']}"
    )

    blast_title = config_entry["blast_title"]
    sanitized_blast_title = re.sub(r"\W+", "_", blast_title)

    # Determine the path based on config
    if "seqcol" in config_entry:
        db_path = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{sanitized_blast_title}/"
        logger.info(f"Using seqcol path structure: {db_path}")
    else:
        db_path = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{sanitized_blast_title.replace(' ', '_')}/"
        )
        logger.info(f"Using species path structure: {db_path}")

    config_path = f"../data/config/{mod}/{environment}"

    # Create directories
    try:
        Path(db_path).mkdir(parents=True, exist_ok=True)
        Path(config_path).mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Created directory structure - DB: {db_path}, Config: {config_path}"
        )
    except Exception as e:
        logger.error(f"Failed to create directory structure: {str(e)}")
        raise

    duration = datetime.now() - start_time
    logger.info(f"Database structure creation completed in {duration}")

    return db_path, config_path


def run_makeblastdb(config_entry: Dict, output_dir: str, logger) -> bool:
    """
    Runs the makeblastdb command to create a BLAST database.

    Args:
        config_entry: Configuration dictionary containing database details
        output_dir: Directory where the database will be created
        logger: Logger instance for tracking operations

    Returns:
        bool: True if database creation was successful, False otherwise
    """
    start_time = datetime.now()
    fasta_file = Path(config_entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    logger.info(f"Starting makeblastdb process for {fasta_file}")
    logger.info(f"Configuration: {json.dumps(config_entry, indent=2)}")

    try:
        # Unzip if necessary
        if not Path(unzipped_fasta).exists():
            logger.info(f"Unzipping {fasta_file}")
            unzip_command = f"gunzip -v ../data/{fasta_file}"
            p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()

            if p.returncode != 0:
                logger.error(f"Unzip failed: {stderr.decode('utf-8')}")
                return False

            logger.info("File unzipped successfully")

        # Check for parse_seqids requirement
        parse_ids_flag = ""
        if needs_parse_seqids(unzipped_fasta):
            parse_ids_flag = "-parse_seqids"
            logger.info("FASTA headers require -parse_seqids flag")

        # Prepare makeblastdb command
        blast_title = config_entry["blast_title"]
        sanitized_blast_title = re.sub(r"\W+", "_", blast_title)
        extensions = "".join(Path(fasta_file).suffixes)

        makeblast_command = (
            f"makeblastdb -in {unzipped_fasta} -dbtype {config_entry['seqtype']} "
            f"-title '{sanitized_blast_title}' "
            f"-out {output_dir}/{fasta_file.replace(extensions, 'db')} "
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
            f"{parse_ids_flag}"
        ).strip()

        logger.info(f"Executing makeblastdb command: {makeblast_command}")

        # Run makeblastdb
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        # Log command output
        if stdout:
            logger.debug(f"makeblastdb stdout: {stdout.decode('utf-8')}")
        if stderr:
            logger.debug(f"makeblastdb stderr: {stderr.decode('utf-8')}")

        if check_output(stdout, stderr):
            duration = datetime.now() - start_time
            logger.info(f"makeblastdb completed successfully in {duration}")

            # Update genome browser mapping if applicable
            if "genome_browser" in config_entry:
                logger.info("Updating genome browser mapping")
                if update_genome_browser_map(config_entry, logger):
                    logger.info("Genome browser mapping updated successfully")
                else:
                    logger.error("Failed to update genome browser mapping")

            # Clean up unzipped file
            if Path(unzipped_fasta).exists():
                file_size = Path(unzipped_fasta).stat().st_size
                logger.info(
                    f"Cleaning up unzipped file: {unzipped_fasta} (size: {file_size} bytes)"
                )
                Path(unzipped_fasta).unlink()

            # Clean up original gzipped file
            original_gzip = f"../data/{fasta_file}"
            if Path(original_gzip).exists():
                file_size = Path(original_gzip).stat().st_size
                logger.info(
                    f"Cleaning up original gzipped file: {original_gzip} (size: {file_size} bytes)"
                )
                Path(original_gzip).unlink()

            return True

        else:
            logger.error("makeblastdb command failed")
            logger.error(f"stderr: {stderr.decode('utf-8')}")
            rmtree(output_dir)
            return False

    except Exception as e:
        logger.error(f"Error in makeblastdb process: {str(e)}", exc_info=True)
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


# In create_blast_db.py


def process_files(
    config_yaml: Optional[str],
    input_json: Optional[str],
    environment: str,
    db_list: Optional[List[str]] = None,
    check_only: bool = False,
    store_files: bool = False,
    cleanup: bool = False,
) -> None:
    """
    Process configuration files with enhanced logging.
    """
    LOGGER.info("Starting configuration file processing")
    LOGGER.info(
        f"Parameters: check_only={check_only}, store_files={store_files}, cleanup={cleanup}"
    )

    try:
        if config_yaml:
            LOGGER.info(f"Processing YAML config: {config_yaml}")
            with open(config_yaml) as f:
                config = yaml.safe_load(f)

            for provider in config["data_providers"]:
                provider_start = datetime.now()
                LOGGER.info(f"Processing provider: {provider['name']}")

                for env in provider["environments"]:
                    json_file = (
                        Path(config_yaml).parent
                        / f"{provider['name']}/databases.{provider['name']}.{env}.json"
                    )

                    if json_file.exists():
                        LOGGER.info(f"Found JSON file: {json_file}")
                        process_json_entries(
                            str(json_file),
                            env,
                            provider["name"],
                            db_list,
                            check_only,
                            store_files,
                            cleanup,
                        )
                    else:
                        LOGGER.warning(f"JSON file not found: {json_file}")

                duration = datetime.now() - provider_start
                LOGGER.info(
                    f"Completed processing provider {provider['name']} in {duration}"
                )

        elif input_json:
            LOGGER.info(f"Processing single JSON file: {input_json}")
            process_json_entries(
                input_json, environment, None, db_list, check_only, store_files, cleanup
            )

    except Exception as e:
        LOGGER.error(f"Failed to process configuration files: {str(e)}", exc_info=True)
        raise


def process_json_entries(
    json_file: str,
    environment: str,
    mod: Optional[str] = None,
    db_list: Optional[List[str]] = None,
    check_only: bool = False,
    store_files: bool = False,
    cleanup: bool = True,
) -> bool:
    """
    Process entries from a JSON configuration file with enhanced logging.

    Args:
        json_file: Path to JSON config file
        environment: Deployment environment
        mod: Model organism database identifier (optional)
        db_list: List of specific databases to process (optional)
        check_only: Whether to only check parse_seqids
        store_files: Whether to store original files
        cleanup: Whether to clean up FASTA files after processing (defaults to True)

    Returns:
        bool: Success status
    """
    start_time = datetime.now()
    LOGGER.info(f"Processing JSON entries from: {json_file}")
    LOGGER.info(
        f"Environment: {environment}, Check only: {check_only}, "
        f"Store files: {store_files}, Cleanup: {cleanup}"
    )

    try:
        with open(json_file, "r") as f:
            db_coordinates = json.load(f)
            LOGGER.info("Successfully loaded JSON configuration")

        # Get MOD code
        mod_code = mod if mod is not None else get_mod_from_json(json_file)
        if not mod_code:
            LOGGER.error("Invalid or missing MOD code")
            console.log("[red]Error: Invalid or missing MOD code[/red]")
            return False

        LOGGER.info(f"Using MOD code: {mod_code}")

        # Create logs directory
        Path("../logs").mkdir(parents=True, exist_ok=True)

        # Process entries
        entries = db_coordinates.get("data", [])
        total_entries = len(entries)
        processed = 0
        successful = 0

        LOGGER.info(f"Found {total_entries} entries to process")

        for entry in entries:
            processed += 1
            LOGGER.info(
                f"\nProcessing entry {processed}/{total_entries}: {entry['blast_title']}"
            )

            # Skip if not in requested list
            if db_list and entry["blast_title"] not in db_list:
                LOGGER.info(f"Skipping {entry['blast_title']} (not in requested list)")
                continue

            # Process entry
            try:
                if process_entry(entry, mod_code, environment, check_only, store_files):
                    successful += 1
            except Exception as e:
                LOGGER.error(
                    f"Failed to process entry {entry['blast_title']}: {str(e)}",
                    exc_info=True,
                )

        # Clean up all FASTA files after processing all entries if cleanup is enabled
        if cleanup and not check_only:
            LOGGER.info("Starting post-processing cleanup")
            cleanup_fasta_files(Path("../data"), LOGGER)

        # Log summary
        duration = datetime.now() - start_time
        LOGGER.info(f"\nJSON processing summary:")
        LOGGER.info(f"Total entries: {total_entries}")
        LOGGER.info(f"Processed: {processed}")
        LOGGER.info(f"Successful: {successful}")
        LOGGER.info(f"Failed: {processed - successful}")
        LOGGER.info(f"Total duration: {duration}")

        return successful > 0

    except Exception as e:
        LOGGER.error(
            f"Failed to process JSON file {json_file}: {str(e)}", exc_info=True
        )
        return False


def process_entry(
    entry: Dict,
    mod_code: str,
    environment: str,
    check_only: bool = False,
    store_files: bool = False,
) -> bool:
    """
    Process a single database entry with comprehensive logging.

    Args:
        entry: Database entry configuration
        mod_code: Model organism database identifier
        environment: Deployment environment
        check_only: Whether to only check parse_seqids
        store_files: Whether to store original files

    Returns:
        bool: Success status
    """
    start_time = datetime.now()
    entry_name = entry["blast_title"]

    # Setup entry-specific logging
    date_to_add = datetime.now().strftime("%Y_%b_%d")
    log_path = f"../logs/{entry['genus']}_{entry['species']}_{entry['seqtype']}_{date_to_add}.log"
    logger = extendable_logger(entry_name, log_path)

    logger.info(f"Starting processing of entry: {entry_name}")
    logger.info(
        f"Configuration details: {json.dumps({k: v for k, v in entry.items() if k != 'uri'}, indent=2)}"
    )

    try:
        fasta_file = Path(entry["uri"]).name
        unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

        # Log processing parameters
        logger.info(f"Processing parameters:")
        logger.info(f"  MOD code: {mod_code}")
        logger.info(f"  Environment: {environment}")
        logger.info(f"  Check only: {check_only}")
        logger.info(f"  Store files: {store_files}")

        # Download file
        logger.info(f"Downloading file from {entry['uri']}")
        if entry["uri"].startswith("ftp://"):
            success = get_files_ftp(
                entry["uri"],
                entry["md5sum"],
                logger,
                mod=mod_code,
                store_files=store_files,
            )
        else:
            success = get_files_http(
                entry["uri"],
                entry["md5sum"],
                logger,
                mod=mod_code,
                store_files=store_files,
            )

        if not success:
            logger.error("File download failed")
            return False

        # Create database if not check_only
        if not check_only:
            logger.info("Creating database structure")
            output_dir, config_dir = create_db_structure(
                environment, mod_code, entry, logger
            )

            logger.info("Running makeblastdb")
            if not run_makeblastdb(entry, output_dir, logger):
                logger.error("Database creation failed")
                return False

            SLACK_MESSAGES.append(
                {
                    "title": "Database Creation Success",
                    "text": f"Successfully processed {entry_name}",
                    "color": "#36a64f",
                }
            )
        else:
            # Check parse_seqids requirement
            if Path(unzipped_fasta).exists():
                needs_parse = needs_parse_seqids(unzipped_fasta)
                status = "requires" if needs_parse else "does not require"
                logger.info(f"Parse seqids check: {entry_name} {status} -parse_seqids")
                console.log(
                    f"{entry_name}: " f"[green]requires[/green]"
                    if needs_parse
                    else "[yellow]does not require[/yellow]" f" -parse_seqids"
                )

        # Clean up files
        try:
            if Path(unzipped_fasta).exists():
                if check_only or not store_files:
                    file_size = Path(unzipped_fasta).stat().st_size
                    logger.info(
                        f"Cleaning up unzipped file: {unzipped_fasta} (size: {file_size:,} bytes)"
                    )
                    Path(unzipped_fasta).unlink()

            original_gzip = f"../data/{fasta_file}"
            if Path(original_gzip).exists() and not store_files:
                file_size = Path(original_gzip).stat().st_size
                logger.info(
                    f"Cleaning up original gzipped file: {original_gzip} (size: {file_size:,} bytes)"
                )
                Path(original_gzip).unlink()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
            # Don't fail the whole process for cleanup errors

        # Log completion
        duration = datetime.now() - start_time
        logger.info(f"Entry processing completed successfully in {duration}")
        return True

    except Exception as e:
        logger.error(f"Entry processing failed: {str(e)}", exc_info=True)
        SLACK_MESSAGES.append(
            {
                "title": "Processing Error",
                "text": f"Failed to process {entry_name}: {str(e)}",
                "color": "#8D2707",
            }
        )
        return False


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
@click.option("--store-files", help="Store original files", is_flag=True, default=False)
@click.option(
    "-cl",
    "--cleanup",
    help="Clean up FASTA files after processing",
    is_flag=True,
    default=True,
)
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
    config_yaml: str,
    input_json: str,
    environment: str,
    mod: str,
    skip_efs_sync: bool,
    update_slack: bool,
    sync_s3: bool,
    store_files: bool,
    cleanup: bool,
    db_names: Optional[str],
    list_dbs: bool,
    check_parse_seqids: bool,
) -> None:
    """
    Main function that runs the pipeline for processing configuration files and creating BLAST databases.
    """
    start_time = datetime.now()
    LOGGER.info("Starting BLAST database creation process")
    LOGGER.info(
        f"Parameters: environment={environment}, mod={mod}, store_files={store_files}, cleanup={cleanup}"
    )

    try:
        if db_names:
            db_list = [name.strip() for name in db_names.split(",")]
            LOGGER.info(f"Processing specific databases: {db_list}")
        else:
            db_list = None
            LOGGER.info("Processing all databases")

        if list_dbs:
            if config_yaml or input_json:
                list_databases_from_config(config_yaml or input_json)
            else:
                msg = "Please provide either a YAML (-g) or JSON (-j) configuration file to list databases."
                LOGGER.error(msg)
                click.echo(msg)
            return

        if len(sys.argv) == 1:
            LOGGER.info("No arguments provided, showing help")
            click.echo(create_dbs.get_help(ctx=None))
            return

        if config_yaml:
            LOGGER.info(f"Processing YAML config: {config_yaml}")
            process_files(
                config_yaml,
                None,
                None,
                db_list,
                check_parse_seqids,
                store_files,
                cleanup,
            )
        elif input_json:
            LOGGER.info(f"Processing JSON config: {input_json}")
            process_files(
                None,
                input_json,
                environment,
                db_list,
                check_parse_seqids,
                store_files,
                cleanup,
            )

        if update_slack and not check_parse_seqids:
            LOGGER.info("Sending Slack update")
            slack_message(SLACK_MESSAGES)

        if sync_s3 and not check_parse_seqids:
            LOGGER.info("Starting S3 sync")
            s3_sync(Path("../data"), skip_efs_sync)

        duration = datetime.now() - start_time
        LOGGER.info(f"Process completed successfully in {duration}")

    except Exception as e:
        LOGGER.error(f"Process failed: {str(e)}", exc_info=True)
        console.log(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    create_dbs()
