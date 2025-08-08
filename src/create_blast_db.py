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
from typing import Dict, List, Optional, Tuple

import click
import yaml

from terminal import (create_progress, log_error, print_header, print_status,
                      show_summary, log_success, log_warning, print_error_details)
from utils import (cleanup_fasta_files, copy_config_file, copy_to_production, copy_config_to_production,
                   extendable_logger, get_files_ftp, get_files_http,
                   get_mod_from_json, needs_parse_seqids, s3_sync,
                   setup_detailed_logger, slack_message,
                   update_genome_browser_map)

# Global variables
SLACK_MESSAGES: List[Dict[str, str]] = []
FAILURE_DETAILS: List[Dict[str, str]] = []  # Track detailed failure information
LOGGER = setup_detailed_logger("create_blast_db", "blast_db_creation.log")


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
    """
    start_time = datetime.now()
    fasta_file = Path(config_entry["uri"]).name
    unzipped_fasta = f"../data/{fasta_file.replace('.gz', '')}"

    logger.info(f"Starting makeblastdb process for {fasta_file}")
    logger.info(f"Configuration: {json.dumps(config_entry, indent=2)}")

    try:
        # Check if unzipped FASTA exists
        if not Path(unzipped_fasta).exists():
            logger.error(f"Unzipped FASTA file not found: {unzipped_fasta}")
            return False

        # Check for parse_seqids requirement
        parse_ids_flag = ""
        if needs_parse_seqids(unzipped_fasta, mod):
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
            stdout_str = stdout.decode("utf-8")
            logger.info(f"makeblastdb stdout: {stdout_str}")
        if stderr:
            stderr_str = stderr.decode("utf-8")
            logger.warning(f"makeblastdb stderr: {stderr_str}")

        if p.returncode != 0:
            error_msg = stderr.decode('utf-8')
            logger.error(f"makeblastdb command failed with return code {p.returncode}")
            logger.error(f"Command: {makeblast_command}")
            logger.error(f"Error output: {error_msg}")
            
            # Display detailed error information
            print_error_details("BLAST Database Creation Error", {
                "Return Code": p.returncode,
                "Command": makeblast_command,
                "Error Output": error_msg,
                "Output Directory": output_dir,
                "FASTA File": unzipped_fasta
            })
            
            if Path(output_dir).exists():
                rmtree(output_dir)
            return False

        logger.info("makeblastdb completed successfully")
        duration = datetime.now() - start_time
        logger.info(f"Process completed in {duration}")
        log_success(f"BLAST database created successfully in {duration}")

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

    except Exception as e:
        logger.error(f"Error in makeblastdb process: {str(e)}", exc_info=True)
        print_status(f"makeblastdb error: {str(e)}", "error")
        if Path(output_dir).exists():
            rmtree(output_dir)
        return False


def list_databases_from_config(config_file: str) -> None:
    """
    Lists all database names from either a YAML or JSON configuration file.
    """
    print_header("Available Databases")

    try:
        if config_file.endswith(".yaml") or config_file.endswith(".yml"):
            with open(config_file) as f:
                config = yaml.safe_load(f)

            for provider in config["data_providers"]:
                print_header(provider["name"])  # Using header for provider names
                for environment in provider["environments"]:
                    json_file = (
                        Path(config_file).parent
                        / f"{provider['name']}/databases.{provider['name']}.{environment}.json"
                    )
                    if json_file.exists():
                        with open(json_file, "r") as f:
                            db_coordinates = json.load(f)
                        for entry in db_coordinates["data"]:
                            print_status(f"• {entry['blast_title']}", "info")
                    else:
                        print_status(f"JSON file not found - {json_file}", "warning")

        elif config_file.endswith(".json"):
            with open(config_file, "r") as f:
                db_coordinates = json.load(f)
            for entry in db_coordinates["data"]:
                print_status(f"• {entry['blast_title']}", "info")
        else:
            log_error("Config file must be either YAML or JSON")

    except Exception as e:
        log_error("Failed to list databases", e)


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


def process_entry(
    entry: Dict,
    mod_code: str,
    environment: str,
    check_only: bool = False,
    store_files: bool = False,
) -> bool:
    """
    Process a single database entry with comprehensive logging and progress display.

    Args:
        entry: Database entry configuration
        mod_code: Model organism database identifier
        environment: Deployment environment
        check_only: Whether to only check parse_seqids
        store_files: Whether to store original files

    Returns:
        bool: Success status
    """
    print_header(f"Processing {entry['blast_title']}")
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
        print_status("Processing parameters:", "info")
        print_status(f"  MOD code: {mod_code}", "info")
        print_status(f"  Environment: {environment}", "info")
        print_status(f"  Check only: {check_only}", "info")
        print_status(f"  Store files: {store_files}", "info")

        # Download file
        print_status(f"Downloading {fasta_file}...", "info")
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
            error_msg = f"File download failed from {entry['uri']}"
            log_error(error_msg)
            FAILURE_DETAILS.append({
                "entry": entry_name,
                "error": error_msg,
                "stage": "download",
                "uri": entry.get("uri", "unknown")
            })
            return False

        log_success("File download complete")

        # Create database if not check_only
        if not check_only:
            # Create database structure
            print_status("Creating database structure", "info")
            output_dir, config_dir = create_db_structure(
                environment, mod_code, entry, logger
            )

            # Unzip file if needed
            if (
                not Path(unzipped_fasta).exists()
                and Path(f"../data/{fasta_file}").exists()
            ):
                logger.info(f"Unzipping {fasta_file}")
                print_status(f"Unzipping {fasta_file}...", "info")
                unzip_command = f"gunzip -v ../data/{fasta_file}"
                p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()

                if p.returncode != 0:
                    error_msg = f"Unzip failed: {stderr.decode('utf-8')}"
                    print_error_details("Unzip Error", {
                        "Command": unzip_command,
                        "Error": stderr.decode('utf-8'),
                        "File": fasta_file
                    })
                    log_error(error_msg)
                    FAILURE_DETAILS.append({
                        "entry": entry_name,
                        "error": error_msg,
                        "stage": "unzip",
                        "uri": entry.get("uri", "unknown")
                    })
                    return False

            # Run makeblastdb
            print_status("Running makeblastdb...", "info")
            if not run_makeblastdb(entry, output_dir, logger):
                error_msg = "Database creation failed"
                log_error(error_msg)
                FAILURE_DETAILS.append({
                    "entry": entry_name,
                    "error": error_msg,
                    "stage": "makeblastdb",
                    "uri": entry.get("uri", "unknown")
                })
                return False

            log_success("Database created successfully")

            SLACK_MESSAGES.append(
                {
                    "title": "Database Creation Success",
                    "text": f"Successfully processed {entry_name}",
                    "color": "#36a64f",
                }
            )

        # Check parse_seqids requirement if in check_only mode
        elif check_only:
            if Path(unzipped_fasta).exists():
                needs_parse = needs_parse_seqids(unzipped_fasta, mod)
                status = "requires" if needs_parse else "does not require"
                print_status(
                    f"{entry_name}: {'[green]requires[/green]' if needs_parse else '[yellow]does not require[/yellow]'} -parse_seqids flag",
                    "info",
                )
                logger.info(f"Parse seqids check: {entry_name} {status} -parse_seqids")

        # Clean up files
        try:
            if Path(unzipped_fasta).exists():
                if check_only or not store_files:
                    file_size = Path(unzipped_fasta).stat().st_size
                    print_status(
                        f"Cleaning up unzipped file: {unzipped_fasta} (size: {file_size:,} bytes)",
                        "info",
                    )
                    Path(unzipped_fasta).unlink()

            original_gzip = f"../data/{fasta_file}"
            if Path(original_gzip).exists() and not store_files:
                file_size = Path(original_gzip).stat().st_size
                print_status(
                    f"Cleaning up original gzipped file: {original_gzip} (size: {file_size:,} bytes)",
                    "info",
                )
                Path(original_gzip).unlink()

        except Exception as e:
            log_error("Cleanup failed", e)
            logger.error(f"Cleanup failed: {str(e)}", exc_info=True)

        # Log completion
        duration = datetime.now() - start_time
        logger.info(f"Entry processing completed in {duration}")
        return True

    except Exception as e:
        error_msg = f"Entry processing failed: {str(e)}"
        log_error("Entry processing failed", e)
        logger.error(f"Entry processing failed: {str(e)}", exc_info=True)
        FAILURE_DETAILS.append({
            "entry": entry_name,
            "error": error_msg,
            "stage": "processing",
            "uri": entry.get("uri", "unknown")
        })
        SLACK_MESSAGES.append(
            {
                "title": "Processing Error",
                "text": f"Failed to process {entry_name}: {str(e)}",
                "color": "#8D2707",
            }
        )
        return False


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
    Process entries from a JSON configuration file with enhanced progress display.
    """
    print_header("Processing JSON Entries")
    start_time = datetime.now()
    LOGGER.info(f"Processing JSON entries from: {json_file}")

    try:
        with open(json_file, "r") as f:
            db_coordinates = json.load(f)
            print_status("Successfully loaded JSON configuration", "success")

        # Get MOD code
        mod_code = mod if mod is not None else get_mod_from_json(json_file)
        if not mod_code:
            log_error("Invalid or missing MOD code")
            return False

        print_status(f"Using MOD code: {mod_code}", "info")

        # Create logs directory
        Path("../logs").mkdir(parents=True, exist_ok=True)

        # Process entries with progress tracking
        entries = db_coordinates.get("data", [])
        total_entries = len(entries)
        processed = 0
        successful = 0

        print_status(f"Found {total_entries} entries to process", "info")

        with create_progress() as progress:
            task = progress.add_task("Processing entries...", total=total_entries)

            for entry in entries:
                processed += 1
                entry_name = entry.get("blast_title", "Unknown")
                
                # Update progress display
                progress.update(task, description=f"Processing {entry_name}...")

                if db_list and entry_name not in db_list:
                    log_warning(f"Skipping {entry_name} (not in requested list)")
                    progress.advance(task)
                    continue

                try:
                    if process_entry(
                        entry, mod_code, environment, check_only, store_files
                    ):
                        successful += 1
                        print_status(f"[{processed}/{total_entries}] ✓ {entry_name}", "success")
                    else:
                        print_status(f"[{processed}/{total_entries}] ✗ {entry_name}", "error")
                except Exception as e:
                    log_error(f"Failed to process entry {entry_name}", e)
                    print_status(f"[{processed}/{total_entries}] ✗ {entry_name}", "error")

                progress.advance(task)

        # After all entries are processed successfully, copy the configuration file
        if successful > 0 and not check_only:
            print_status("Copying configuration file", "info")
            config_dir = Path(f"../data/config/{mod_code}/{environment}")
            if copy_config_file(Path(json_file), config_dir, LOGGER):
                print_status("Configuration file copied successfully", "success")
            else:
                log_error("Failed to copy configuration file")

            # Update genome browser mappings after all entries are processed
            print_status("Updating genome browser mappings", "info")
            for entry in entries:
                if "genome_browser" in entry:
                    if update_genome_browser_map(entry, mod_code, environment, LOGGER):
                        print_status(
                            f"Updated mapping for {entry['blast_title']}", "success"
                        )
                    else:
                        log_error(
                            f"Failed to update mapping for {entry['blast_title']}"
                        )

        # Clean up all FASTA files after processing if cleanup is enabled
        if cleanup and not check_only:
            print_status("Starting post-processing cleanup", "info")
            try:
                cleanup_fasta_files(Path("../data"), LOGGER)
                print_status("Cleanup completed successfully", "success")
            except Exception as e:
                log_error("Cleanup failed", e)

        # Show final summary
        duration = datetime.now() - start_time
        failed_count = processed - successful
        
        show_summary(
            "JSON Processing",
            {
                "Total Entries": total_entries,
                "Processed": processed,
                "Successful": successful,
                "Failed": failed_count,
                "Success Rate": f"{(successful/total_entries*100):.1f}%" if total_entries > 0 else "0%",
                "Cleanup Performed": str(cleanup and not check_only),
            },
            duration,
        )
        
        # Show detailed failure summary if there were failures
        if failed_count > 0:
            show_failure_summary()

        # Create failure summary for Slack if there were failures
        failure_summary = ""
        if failed_count > 0:
            stage_counts = {}
            for failure in FAILURE_DETAILS:
                stage = failure.get("stage", "unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            failure_summary = "\n\n*Failure Breakdown:*\n"
            for stage, count in sorted(stage_counts.items()):
                failure_summary += f"• {stage.title()}: {count}\n"
        
        summary_text = (
            "*JSON Processing Summary*\n"
            f"• *Total Entries:* {total_entries}\n"
            f"• *Processed:* {processed}\n"
            f"• *Successful:* {successful}\n"
            f"• *Failed:* {failed_count}\n"
            f"• *Success Rate:* {(successful/total_entries*100):.1f}%\n"
            f"• *Cleanup Performed:* {cleanup and not check_only}\n"
            f"• *Duration:* {duration}"
            f"{failure_summary}"
        )

        SLACK_MESSAGES.append(
            {
                "color": "#36a64f" if successful == total_entries else "#ff9900",
                "title": "Processing Summary",
                "text": summary_text,
                "mrkdwn_in": ["text"],
            }
        )

        return successful > 0

    except Exception as e:
        log_error(f"Failed to process JSON file {json_file}", e)
        return False


def show_failure_summary() -> None:
    """
    Display a detailed summary of all failures that occurred during processing.
    """
    if not FAILURE_DETAILS:
        return
    
    print_header("Failure Summary")
    print_status(f"Total failures: {len(FAILURE_DETAILS)}", "error")
    
    # Group failures by stage
    stage_failures = {}
    for failure in FAILURE_DETAILS:
        stage = failure.get("stage", "unknown")
        if stage not in stage_failures:
            stage_failures[stage] = []
        stage_failures[stage].append(failure)
    
    # Display failures by stage
    for stage, failures in stage_failures.items():
        print_status(f"\n{stage.upper()} failures ({len(failures)}):", "warning")
        for failure in failures:
            print_status(f"  ✗ {failure['entry']}", "error")
            print_status(f"    Error: {failure['error']}", "error")
            if failure.get('uri'):
                print_status(f"    URI: {failure['uri']}", "info")
    
    # Show common failure patterns
    error_patterns = {}
    for failure in FAILURE_DETAILS:
        error = failure.get("error", "")
        # Extract common error patterns
        if "makeblastdb" in error.lower():
            key = "BLAST database creation"
        elif "download" in error.lower():
            key = "File download"
        elif "unzip" in error.lower():
            key = "File extraction"
        elif "md5" in error.lower():
            key = "Checksum validation"
        else:
            key = "Other"
        
        if key not in error_patterns:
            error_patterns[key] = 0
        error_patterns[key] += 1
    
    print_status("\nFailure patterns:", "warning")
    for pattern, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
        print_status(f"  {pattern}: {count} failures", "info")


def send_slack_messages_in_batches(messages: List[Dict[str, str]], batch_size: int = 20) -> None:
    """
    Sends Slack messages in smaller batches to avoid the too_many_attachments error.

    Args:
        messages: List of message dictionaries to send
        batch_size: Maximum number of messages to send in each batch
    """
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        try:
            slack_message(batch)
        except Exception as e:
            LOGGER.error(f"Failed to send Slack batch {i//batch_size + 1}: {str(e)}")


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
                print_status(msg, "error")
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

        # Handle Slack updates with better error checking and batching
        if update_slack and not check_parse_seqids and SLACK_MESSAGES:
            try:
                LOGGER.info("Sending Slack updates in batches")
                send_slack_messages_in_batches(SLACK_MESSAGES)
            except Exception as e:
                log_error("Failed to send Slack updates - check SLACK token in .env", e)

        # Copy databases and config to production location
        if not check_parse_seqids:
            LOGGER.info("Preparing to copy to production location")
            from terminal import console
            
            try:
                # Collect all directories to copy
                copy_operations = []
                
                # Find databases to copy
                data_blast_dir = Path("../data/blast")
                if data_blast_dir.exists():
                    for mod_dir in data_blast_dir.iterdir():
                        if mod_dir.is_dir():
                            mod_name = mod_dir.name
                            for env_dir in mod_dir.iterdir():
                                if env_dir.is_dir():
                                    env_name = env_dir.name
                                    databases_dir = env_dir / "databases"
                                    if databases_dir.exists():
                                        copy_operations.append(("databases", str(databases_dir), mod_name, env_name))
                
                # Find config files to copy
                data_config_dir = Path("../data/config")
                if data_config_dir.exists():
                    for mod_dir in data_config_dir.iterdir():
                        if mod_dir.is_dir():
                            mod_name = mod_dir.name
                            for env_dir in mod_dir.iterdir():
                                if env_dir.is_dir():
                                    env_name = env_dir.name
                                    copy_operations.append(("config", str(env_dir), mod_name, env_name))
                
                if not copy_operations:
                    print_status("No data to copy to production", "info")
                else:
                    # Show dry run
                    console.print("\n[bold yellow]═══ PRODUCTION COPY PREVIEW ═══[/bold yellow]")
                    for copy_type, source_path, mod_name, env_name in copy_operations:
                        if copy_type == "databases":
                            copy_to_production(source_path, mod_name, env_name, LOGGER, dry_run=True)
                        else:
                            copy_config_to_production(source_path, mod_name, env_name, LOGGER, dry_run=True)
                        console.print()
                    
                    # Ask for confirmation
                    console.print("[bold]Do you want to proceed with copying to production? [y/N]:[/bold]", end=" ")
                    response = input().strip().lower()
                    
                    if response == 'y' or response == 'yes':
                        console.print("[green]Proceeding with production copy...[/green]\n")
                        
                        # Perform actual copy
                        for copy_type, source_path, mod_name, env_name in copy_operations:
                            if copy_type == "databases":
                                if copy_to_production(source_path, mod_name, env_name, LOGGER):
                                    print_status(f"Copied {mod_name}/{env_name} databases to production", "success")
                                else:
                                    log_error(f"Failed to copy {mod_name}/{env_name} databases to production")
                            else:
                                if copy_config_to_production(source_path, mod_name, env_name, LOGGER):
                                    print_status(f"Copied {mod_name}/{env_name} config to production", "success")
                                else:
                                    log_error(f"Failed to copy {mod_name}/{env_name} config to production")
                    else:
                        console.print("[yellow]Skipped copying to production location[/yellow]")
                        
            except Exception as e:
                log_error("Failed to copy to production", e)

        if sync_s3 and not check_parse_seqids:
            LOGGER.info("Starting S3 sync")
            s3_sync(Path("../data"), skip_efs_sync)

        duration = datetime.now() - start_time
        LOGGER.info(f"Process completed successfully in {duration}")

    except Exception as e:
        LOGGER.error(f"Process failed: {str(e)}", exc_info=True)
        log_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    create_dbs()
