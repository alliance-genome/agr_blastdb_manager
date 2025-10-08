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
from typing import Any, Optional

from dotenv import dotenv_values
from rich import print as rprint
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from terminal import create_progress, log_error, print_status

console = Console()

# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN", "RGD"]


def copy_config_file(json_file: Path, config_dir: Path, logger) -> bool:
    """
    Copies the configuration file to the config directory.
    """
    try:
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Copy the JSON configuration file
        target_file = config_dir / "environment.json"
        target_file.write_text(json_file.read_text())
        logger.info(f"Copied configuration file to {target_file}")

        return True
    except Exception as e:
        logger.error(f"Failed to copy configuration file: {str(e)}")
        return False


def copy_to_production(
    source_databases_path: str,
    mod: str,
    environment: str,
    logger,
    dry_run: bool = False,
) -> bool:
    """
    Copies BLAST databases from data directory to production location (/var/sequenceserver-data).
    If dry_run is True, only shows what would be copied without actually copying.
    """
    try:
        source_path = Path(source_databases_path)
        dest_path = Path(
            f"/var/sequenceserver-data/blast/{mod}/{environment}/databases"
        )

        if not source_path.exists():
            logger.error(f"Source databases path does not exist: {source_path}")
            return False

        if dry_run:
            # Show what would be copied
            from terminal import console

            console.print("[yellow]DRY RUN[/yellow] - Would copy databases:")
            console.print(f"  Source: {source_path}")
            console.print(f"  Destination: {dest_path}")

            # Show directory contents to be copied
            try:
                db_dirs = [d for d in source_path.iterdir() if d.is_dir()]
                if db_dirs:
                    console.print(f"  Database directories to copy ({len(db_dirs)}):")
                    for db_dir in sorted(db_dirs):
                        db_files = list(db_dir.glob("*"))
                        file_count = len(db_files)
                        total_size = sum(
                            f.stat().st_size for f in db_files if f.is_file()
                        )
                        size_mb = total_size / (1024 * 1024)
                        console.print(
                            f"    - {db_dir.name}/ ({file_count} files, {size_mb:.1f} MB)"
                        )

                if dest_path.exists():
                    console.print(
                        f"  [red]Will replace existing directory:[/red] {dest_path}"
                    )
                else:
                    console.print(
                        f"  [green]Will create new directory:[/green] {dest_path}"
                    )

            except Exception as e:
                console.print(f"  [red]Error analyzing source directory: {e}[/red]")

            return True

        # Create production directory structure
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy database directory structure
        import shutil

        # Remove existing databases directory if it exists
        if dest_path.exists():
            shutil.rmtree(dest_path)
            logger.info(f"Removed existing databases directory: {dest_path}")

        # Copy the entire databases directory
        shutil.copytree(source_path, dest_path)
        logger.info(f"Copied databases from {source_path} to {dest_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to copy databases to production: {str(e)}")
        return False


def copy_config_to_production(
    source_config_path: str, mod: str, environment: str, logger, dry_run: bool = False
) -> bool:
    """
    Copies config files from data directory to production location (/var/sequenceserver-data).
    If dry_run is True, only shows what would be copied without actually copying.
    """
    try:
        source_path = Path(source_config_path)
        dest_path = Path(f"/var/sequenceserver-data/config/{mod}/{environment}")

        if not source_path.exists():
            logger.error(f"Source config path does not exist: {source_path}")
            return False

        if dry_run:
            # Show what would be copied
            from terminal import console

            console.print("[yellow]DRY RUN[/yellow] - Would copy config:")
            console.print(f"  Source: {source_path}")
            console.print(f"  Destination: {dest_path}")

            # Show config files to be copied
            try:
                config_files = [f for f in source_path.iterdir() if f.is_file()]
                if config_files:
                    console.print(f"  Config files to copy ({len(config_files)}):")
                    for config_file in sorted(config_files):
                        file_size = config_file.stat().st_size
                        size_kb = file_size / 1024
                        console.print(f"    - {config_file.name} ({size_kb:.1f} KB)")

                if dest_path.exists():
                    console.print(
                        f"  [red]Will replace existing directory:[/red] {dest_path}"
                    )
                else:
                    console.print(
                        f"  [green]Will create new directory:[/green] {dest_path}"
                    )

            except Exception as e:
                console.print(f"  [red]Error analyzing config directory: {e}[/red]")

            return True

        # Create production directory structure
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy config directory structure
        import shutil

        # Remove existing config directory if it exists
        if dest_path.exists():
            shutil.rmtree(dest_path)
            logger.info(f"Removed existing config directory: {dest_path}")

        # Copy the entire config directory
        shutil.copytree(source_path, dest_path)
        logger.info(f"Copied config from {source_path} to {dest_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to copy config to production: {str(e)}")
        return False


def setup_detailed_logger(
    log_name: str, file_name: str, level=logging.INFO
) -> logging.Logger:
    """
    Creates a detailed logger with comprehensive formatting.
    """
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(log_name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # File handler
    handler = logging.FileHandler(file_name)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def store_fasta_files(fasta_file: str, logger, store_files: bool = False) -> None:
    """
    Stores FASTA files in a dated directory if storage is enabled.

    Args:
        fasta_file (str): Path to the FASTA file
        logger (logging.Logger): Logger instance
        store_files (bool): Whether to store the file
    """
    if not store_files:
        logger.info(f"File storage disabled, skipping storage of {fasta_file}")
        return

    date_to_add = datetime.now().strftime("%Y_%b_%d")
    original_files_store = Path(f"../data/database_{date_to_add}")

    try:
        if not original_files_store.exists():
            logger.info(f"Creating storage directory: {original_files_store}")
            original_files_store.mkdir(parents=True, exist_ok=True)

        file_size = Path(fasta_file).stat().st_size
        dest_path = original_files_store / Path(fasta_file).name

        logger.info(
            f"Storing file {fasta_file} (size: {file_size} bytes) to {dest_path}"
        )
        copyfile(fasta_file, dest_path)
        logger.info("File stored successfully")

    except Exception as e:
        logger.error(f"Failed to store file {fasta_file}: {str(e)}", exc_info=True)
        # Don't raise the exception - make storage truly optional
        logger.warning("Continuing process despite storage failure")


def cleanup_fasta_files(data_dir: Path, logger) -> None:
    """
    Cleans up all FASTA files in the specified directory after database generation.
    """
    logger.info(f"Starting cleanup of FASTA files in {data_dir}")
    print_status("Starting final cleanup...", "info")

    try:
        # Find all FASTA files (both gzipped and uncompressed)
        fasta_patterns = ["*.fa*", "*.fasta*", "*.fna*", "*.gz"]
        fasta_files = []
        for pattern in fasta_patterns:
            fasta_files.extend(list(data_dir.glob(pattern)))

        if not fasta_files:
            logger.info("No FASTA files found for cleanup")
            print_status("No files to clean up", "info")
            return

        logger.info(f"Found {len(fasta_files)} files to clean up")
        print_status(f"Found {len(fasta_files)} files to clean up", "info")

        with create_progress() as progress:
            cleanup_task = progress.add_task(
                "Cleaning up files...", total=len(fasta_files)
            )

            for fasta_file in fasta_files:
                try:
                    file_size = fasta_file.stat().st_size
                    logger.info(
                        f"Removing {fasta_file.name} (size: {file_size:,} bytes)"
                    )
                    fasta_file.unlink()
                    logger.info(f"Successfully removed {fasta_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {fasta_file.name}: {str(e)}")
                    print_status(f"Failed to remove {fasta_file.name}", "warning")

                progress.advance(cleanup_task)

        print_status("Cleanup completed successfully", "success")
        logger.info("FASTA file cleanup completed")

    except Exception as e:
        error_msg = f"Error during FASTA cleanup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print_status(error_msg, "error")


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


def check_md5sum(fasta_file: str, expected_md5: str, logger) -> bool:
    """
    Checks MD5 checksum of a file with detailed logging.

    Args:
        fasta_file (str): Path to the file
        expected_md5 (str): Expected MD5 checksum
        logger (logging.Logger): Logger instance

    Returns:
        bool: True if checksums match, False otherwise
    """
    logger.info(f"Calculating MD5 checksum for {fasta_file}")
    try:
        with open(fasta_file, "rb") as f:
            file_size = Path(fasta_file).stat().st_size
            logger.info(f"File size: {file_size} bytes")

            # Calculate MD5
            start_time = datetime.now()
            calculated_md5 = hashlib.md5(f.read()).hexdigest()
            duration = datetime.now() - start_time

            logger.info(f"MD5 calculation completed in {duration}")
            logger.info(f"Expected MD5: {expected_md5}")
            logger.info(f"Calculated MD5: {calculated_md5}")

            if calculated_md5 != expected_md5:
                logger.error("MD5 checksums do not match")
                return False

            logger.info("MD5 checksums match")
            return True

    except Exception as e:
        logger.error(f"MD5 checksum verification failed: {str(e)}", exc_info=True)
        return False


def get_mod_from_json(input_json) -> str:
    """
    Retrieves the model organism (mod) from the input JSON file.
    Supports generic MOD extraction with prefix matching for variants like "SGD_test".
    """
    filename = Path(input_json).name
    parts = filename.split(".")

    # Extract the potential MOD from the second part (index 1)
    if len(parts) > 1:
        mod_part = parts[1]

        # First, check if it matches exactly with known MODs
        if mod_part.upper() in [m.upper() for m in MODS]:
            console.log(f"Mod found (exact match): {mod_part.upper()}")
            return mod_part.upper()

        # Try to match prefix against known MODs, handling cases like "SGD_test"
        for known_mod in MODS:
            if mod_part.upper().startswith(known_mod.upper()):
                console.log(f"Mod found (prefix match): {known_mod}")
                return known_mod

        # If no match found in predefined list, just return the extracted part
        # This allows for flexibility with new or test MODs
        console.log(f"Using extracted MOD (not in predefined list): {mod_part}")
        return mod_part

    console.log(f"Could not extract MOD from filename {filename}")
    return False


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


def check_output(stdout: bytes, stderr: bytes) -> bool:
    """
    Checks the output of a command for errors.
    """
    stderr = stderr.decode("utf-8")
    if len(stderr) > 1:
        if stderr.find("Error") >= 1:
            console.log(stderr, style="blink bold white on red")
            return False
    return True


def slack_message(messages: list, subject="BLAST Database Update") -> bool:
    """
    Sends a message to a Slack channel using the Slack API.
    If no Slack configuration is found, skips silently.
    """
    env = dotenv_values(f"{Path.cwd()}/.env")

    # Check if Slack token is configured
    if "SLACK" not in env:
        print_status("Skipping Slack update - no Slack token configured", "warning")
        return True

    try:
        client = WebClient(token=env["SLACK"])
        client.chat_postMessage(
            channel="#blast-status",
            text=subject,
            attachments=messages,
        )
        print_status("Slack message sent successfully", "success")
        return True

    except SlackApiError as e:
        log_error(f"Failed to send Slack message: {e.response['error']}")
        return False
    except Exception as e:
        log_error("Unexpected error sending Slack message", e)
        return False


def needs_parse_seqids(fasta_file: str, mod: str = None) -> bool:
    """
    Determines if a FASTA file needs the -parse_seqids flag by examining its headers.
    ZFIN files should NOT use parse_seqids, all others should check headers.
    """
    # ZFIN files should NOT use parse_seqids
    if mod == "ZFIN":
        return False
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


def get_files_http(
    file_uri: str,
    md5sum: str,
    logger,
    mod: Optional[str] = None,
    store_files: bool = False,
) -> bool:
    """
    Downloads files from HTTP/HTTPS sites with controlled output.
    """
    logger.info(f"Starting HTTP download from: {file_uri}")

    try:
        # Ensure data directory exists
        Path("../data").mkdir(parents=True, exist_ok=True)
        
        file_name = f"../data/{Path(file_uri).name}"
        logger.info(f"Download target: {file_name}")

        # Download file with system wget for better handling
        download_start = datetime.now()
        try:
            # Use system wget with timeout and progress options
            wget_command = [
                "wget",
                "--timeout=30",
                "--tries=3",
                "--no-verbose",
                "--show-progress",
                "-O",
                file_name,
                file_uri,
            ]

            logger.info(f"Running command: {' '.join(wget_command)}")
            p = Popen(wget_command, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()

            download_duration = datetime.now() - download_start

            if p.returncode != 0:
                error_msg = stderr.decode("utf-8")
                logger.error(f"wget failed with return code {p.returncode}")
                logger.error(f"Error: {error_msg}")
                return False

            logger.info(f"wget stdout: {stdout.decode('utf-8')}")
            if stderr:
                logger.info(f"wget stderr: {stderr.decode('utf-8')}")
        except Exception as e:
            logger.error(f"Download command failed: {str(e)}", exc_info=True)
            return False

        # Rest of the function remains the same
        file_size = Path(file_name).stat().st_size
        logger.info(
            f"Download completed | Size: {file_size:,} bytes | "
            f"Duration: {download_duration} | "
            f"Speed: {file_size / download_duration.total_seconds() / 1024:.2f} KB/s"
        )

        if store_files:
            logger.info("Storing original file (store_files=True)")
            store_fasta_files(file_name, logger)

        if mod != "ZFIN":
            logger.info(f"Verifying MD5 checksum: expected={md5sum}")
            if not check_md5sum(file_name, md5sum, logger):
                logger.error("MD5 checksum verification failed")
                return False
            logger.info("MD5 checksum verified successfully")
        else:
            logger.info("Skipping MD5 check for ZFIN")

        return True

    except Exception as e:
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        return False


def get_files_ftp(
    fasta_uri: str,
    md5sum: str,
    logger,
    mod: Optional[str] = None,
    store_files: bool = False,
) -> bool:
    """
    Downloads files from FTP sites with controlled output.
    """
    start_time = datetime.now()
    logger.info(f"Starting FTP download from: {fasta_uri}")

    try:
        # Ensure data directory exists
        Path("../data").mkdir(parents=True, exist_ok=True)
        
        ftp_host = Path(fasta_uri).parts[1]
        ftp_path = "/".join(Path(fasta_uri).parts[2:-1])
        fasta_file = f"../data/{Path(fasta_uri).name}"
        fasta_name = Path(fasta_uri).name

        logger.info("FTP Details:")
        logger.info(f"  Host: {ftp_host}")
        logger.info(f"  Path: {ftp_path}")
        logger.info(f"  File: {fasta_name}")
        logger.info(f"Local target: {fasta_file}")

        if store_files:
            date_to_add = datetime.now().strftime("%Y_%b_%d")
            stored_path = Path(f"../data/database_{date_to_add}/{fasta_name}")
            if stored_path.exists():
                logger.info(f"File already exists in storage: {stored_path}")
                return False

        # Get remote file size
        try:
            remote_size = get_ftp_file_size(fasta_uri, logger)
            logger.info(f"Remote file size: {remote_size:,} bytes")
        except Exception as e:
            logger.warning(f"Could not get remote file size: {str(e)}")
            remote_size = None

        # Download file with system wget for better FTP handling
        download_start = datetime.now()
        logger.info("Starting file download")

        try:
            # Use system wget with timeout and progress options
            wget_command = [
                "wget",
                "--timeout=30",
                "--tries=3",
                "--no-verbose",
                "--show-progress",
                "-O",
                fasta_file,
                fasta_uri,
            ]

            logger.info(f"Running command: {' '.join(wget_command)}")
            p = Popen(wget_command, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()

            download_duration = datetime.now() - download_start

            if p.returncode != 0:
                error_msg = stderr.decode("utf-8")
                logger.error(f"wget failed with return code {p.returncode}")
                logger.error(f"Error: {error_msg}")
                return False

            logger.info(f"wget stdout: {stdout.decode('utf-8')}")
            if stderr:
                logger.info(f"wget stderr: {stderr.decode('utf-8')}")

            # Rest of the verification code...
            if Path(fasta_file).exists():
                local_size = Path(fasta_file).stat().st_size
                logger.info(
                    f"Download completed:\n"
                    f"  Duration: {download_duration}\n"
                    f"  Local size: {local_size:,} bytes\n"
                    f"  Speed: {local_size / download_duration.total_seconds() / 1024:.2f} KB/s"
                )

                if remote_size and remote_size != local_size:
                    logger.error(
                        f"Size mismatch - Remote: {remote_size:,} bytes, Local: {local_size:,} bytes"
                    )
                    return False
            else:
                logger.error("Downloaded file not found")
                return False

        except Exception as e:
            logger.error(f"Download failed: {str(e)}", exc_info=True)
            return False

        # Rest of the function remains the same...
        if store_files:
            logger.info("Storing original file (store_files=True)")
            try:
                store_fasta_files(fasta_file, logger, store_files)
                logger.info("File stored successfully")
            except Exception as e:
                logger.error(f"File storage failed: {str(e)}", exc_info=True)
                return False

        if mod == "ZFIN":
            logger.info("Skipping MD5 check for ZFIN")
            return True

        logger.info(f"Verifying MD5 checksum: expected={md5sum}")
        if check_md5sum(fasta_file, md5sum, logger):
            logger.info("MD5 checksum verification successful")
            duration = datetime.now() - start_time
            logger.info(
                f"FTP download and verification completed successfully in {duration}"
            )
            return True
        else:
            logger.error(
                f"MD5 checksum verification failed:\n"
                f"  File: {fasta_file}\n"
                f"  Expected: {md5sum}"
            )
            return False

    except Exception as e:
        logger.error(
            f"FTP download process failed:\n  URI: {fasta_uri}\n  Error: {str(e)}",
            exc_info=True,
        )
        return False


def get_ftp_file_size(fasta_uri: str, logger) -> int:
    """
    Gets the size of a file from FTP or HTTP/HTTPS server with enhanced logging.

    Args:
        fasta_uri (str): URI of the file (FTP, HTTP, or HTTPS)
        logger (logging.Logger): Logger instance

    Returns:
        int: Size of the file in bytes
    """
    try:
        # Check if it's an HTTP/HTTPS URL
        if fasta_uri.startswith(('http://', 'https://')):
            logger.info(f"Getting file size from HTTP/HTTPS: {fasta_uri}")
            import requests
            response = requests.head(fasta_uri, allow_redirects=True, timeout=10)
            size = int(response.headers.get('content-length', 0))
            if size > 0:
                logger.info(f"File size retrieved: {size:,} bytes")
                return size
            else:
                logger.warning(f"Couldn't determine size for {fasta_uri}")
                return 0

        # Handle FTP URLs
        logger.info(f"Getting file size from FTP: {fasta_uri}")

        # Parse FTP URI
        ftp_host = Path(fasta_uri).parts[1]
        ftp_path = "/".join(Path(fasta_uri).parts[2:-1])
        filename = Path(fasta_uri).name

        logger.info(f"Connecting to FTP server: {ftp_host}")

        # Connect to FTP server
        ftp = FTP(ftp_host)
        ftp.login()

        logger.info(f"Navigating to directory: {ftp_path}")
        ftp.cwd(ftp_path)

        # Get file size
        size = ftp.size(filename)

        if size is not None:
            logger.info(f"File size retrieved: {size:,} bytes")
            ftp.quit()
            return size
        else:
            logger.error("File size not available")
            ftp.quit()
            return 0

    except Exception as e:
        logger.error(f"Failed to get file size: {str(e)}", exc_info=True)
        return 0


def update_genome_browser_map(
    config_entry: dict, mod: str, environment: str, logger
) -> bool:
    """
    Updates genome browser mappings for both Ruby and JSON formats.
    """

    def log_and_print(message: str, level: str = "info"):
        """Helper to both log and print messages"""
        if level == "error":
            logger.error(message)
            rprint(f"[red]ERROR: {message}[/red]")
        elif level == "warning":
            logger.warning(message)
            rprint(f"[yellow]WARNING: {message}[/yellow]")
        else:
            logger.info(message)
            rprint(f"[blue]INFO: {message}[/blue]")

    try:
        # Debug current directory
        current_dir = Path.cwd()
        log_and_print(f"Current working directory: {current_dir}")

        # Skip if no genome browser info
        if "genome_browser" not in config_entry:
            log_and_print("No genome browser info found in entry, skipping", "warning")
            return True

        # Get filename and browser URL for current entry
        filename = Path(config_entry["uri"]).name
        browser_url = config_entry["genome_browser"]["url"]
        log_and_print(f"Processing: {filename} -> {browser_url}")

        # Define target directory with correct path and create if needed
        target_dir = Path("../data/config") / mod / environment
        target_dir.mkdir(parents=True, exist_ok=True)
        log_and_print(
            f"Target directory: {target_dir.absolute()} (exists: {target_dir.exists()})"
        )

        # Define file paths
        json_file = target_dir / "genome_browser_map.json"
        ruby_file = target_dir / "genome_browser_map.rb"
        log_and_print(
            f"Will write to:\n  JSON: {json_file.absolute()}\n  Ruby: {ruby_file.absolute()}"
        )

        # Load existing mappings from JSON if it exists
        mapping = {}
        if json_file.exists():
            try:
                with open(json_file, "r") as f:
                    content = f.read()
                    log_and_print(f"Existing JSON content: {content[:100]}...")
                    if content.strip():
                        mapping = json.loads(content)
                log_and_print(f"Loaded {len(mapping)} existing mappings")
            except Exception as e:
                log_and_print(
                    f"Starting fresh due to error reading JSON: {e}", "warning"
                )

        # Add new mapping
        mapping[filename] = browser_url
        log_and_print(f"Added new mapping. Total mappings now: {len(mapping)}")

        # Write JSON file
        try:
            json_content = json.dumps(mapping, indent=2, sort_keys=True)
            log_and_print(f"Writing JSON content: {json_content[:100]}...")
            with open(json_file, "w") as f:
                f.write(json_content)
            log_and_print(
                f"Wrote JSON file: {json_file} (size: {json_file.stat().st_size} bytes)"
            )
        except Exception as e:
            log_and_print(f"Failed to write JSON file: {e}", "error")
            return False

        # Write Ruby file
        try:
            ruby_content = "GENOME_BROWSER_MAP = {\n"
            for fname, url in sorted(mapping.items()):
                ruby_content += f"  '{fname}' => '{url}',\n"
            ruby_content += "}.freeze\n"

            log_and_print(f"Writing Ruby content: {ruby_content[:100]}...")
            with open(ruby_file, "w") as f:
                f.write(ruby_content)
            log_and_print(
                f"Wrote Ruby file: {ruby_file} (size: {ruby_file.stat().st_size} bytes)"
            )
        except Exception as e:
            log_and_print(f"Failed to write Ruby file: {e}", "error")
            return False

        # Final verification
        if not json_file.exists() or not ruby_file.exists():
            log_and_print("One or both files missing after writing!", "error")
            log_and_print(f"JSON exists: {json_file.exists()}", "error")
            log_and_print(f"Ruby exists: {ruby_file.exists()}", "error")
            return False

        log_and_print("✓ Successfully updated both mapping files")
        return True

    except Exception as e:
        log_and_print(f"Failed to update mapping: {str(e)}", "error")
        return False
