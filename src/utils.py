"""
utils.py

This module contains utility functions that are used across the project. These functions include, but are not limited to,
functions for logging, checking MD5 checksums, editing FASTA files, and more. These functions are designed to be reusable
and generic to improve the modularity and maintainability of the code.

Author: Paulo Nuin, Adam Wright
Date: started September 2023
"""

import hashlib
import logging
import re
from datetime import datetime
from ftplib import FTP
from pathlib import Path
from shutil import copyfile
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Optional

import wget
from dotenv import dotenv_values
from rich.console import Console
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

console = Console()

# TODO: move to ENV
MODS = ["FB", "SGD", "WB", "XB", "ZFIN"]


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
        logger.info(f"File stored successfully")

    except Exception as e:
        logger.error(f"Failed to store file {fasta_file}: {str(e)}", exc_info=True)
        # Don't raise the exception - make storage truly optional
        logger.warning("Continuing process despite storage failure")


def cleanup_fasta_files(data_dir: Path, logger) -> None:
    """
    Cleans up all FASTA files in the specified directory after database generation.

    Args:
        data_dir (Path): Directory containing FASTA files
        logger (logging.Logger): Logger instance
    """
    logger.info(f"Starting cleanup of FASTA files in {data_dir}")

    try:
        # Find all FASTA files (both gzipped and uncompressed)
        fasta_files = (
            list(data_dir.glob("*.fa*"))
            + list(data_dir.glob("*.fasta*"))
            + list(data_dir.glob("*.fna*"))
        )

        if not fasta_files:
            logger.info("No FASTA files found for cleanup")
            return

        logger.info(f"Found {len(fasta_files)} FASTA files to clean up")

        for fasta_file in fasta_files:
            try:
                file_size = fasta_file.stat().st_size
                logger.info(f"Removing {fasta_file.name} (size: {file_size:,} bytes)")
                fasta_file.unlink()
                logger.info(f"Successfully removed {fasta_file.name}")
            except Exception as e:
                logger.error(f"Failed to remove {fasta_file.name}: {str(e)}")
                # Continue with other files even if one fails
                continue

        logger.info("FASTA file cleanup completed")

    except Exception as e:
        logger.error(f"Error during FASTA cleanup: {str(e)}", exc_info=True)
        # Don't raise the exception - cleanup should be non-blocking
        logger.warning("Cleanup process encountered errors but continuing")


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
    """
    filename = Path(input_json).name
    mod = filename.split(".")[1]

    if mod not in MODS:
        console.log(f"Mod {mod} not found in {MODS}")
        return False

    console.log(f"Mod found: {mod}")
    return mod


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
    """
    env = dotenv_values(f"{Path.cwd()}/.env")
    client = WebClient(token=env["SLACK"])

    try:
        response = client.chat_postMessage(
            channel="#blast-status",
            text=subject,
            attachments=messages,
        )
        console.log("Done sending message to Slack channel")
    except SlackApiError as e:
        assert e.response["ok"] is False
        assert e.response["error"]
        print(f"Got an error: {e.response['error']}")

    return True


def needs_parse_seqids(fasta_file: str) -> bool:
    """
    Determines if a FASTA file needs the -parse_seqids flag by examining its headers.
    """
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
    Downloads files from HTTP/HTTPS sites with comprehensive logging.
    """
    start_time = datetime.now()
    logger.info(f"Starting HTTP download from: {file_uri}")

    try:
        file_name = f"../data/{Path(file_uri).name}"
        logger.info(f"Download target: {file_name}")

        # Download file
        download_start = datetime.now()
        wget.download(file_uri, file_name)
        download_duration = datetime.now() - download_start

        # Log download statistics
        file_size = Path(file_name).stat().st_size
        logger.info(
            f"Download completed | Size: {file_size} bytes | "
            f"Duration: {download_duration} | "
            f"Speed: {file_size / download_duration.total_seconds() / 1024:.2f} KB/s"
        )

        # Store file if requested
        if store_files:
            logger.info(f"Storing original file (store_files=True)")
            store_fasta_files(file_name, logger)

        # Verify checksum
        if mod != "ZFIN":
            logger.info(f"Verifying MD5 checksum: expected={md5sum}")
            if not check_md5sum(file_name, md5sum):
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
    Downloads files from FTP sites with comprehensive logging and optional storage.

    Args:
        fasta_uri (str): FTP URI of the file to download
        md5sum (str): Expected MD5 checksum
        logger (logging.Logger): Logger instance
        mod (Optional[str]): Model organism database identifier
        store_files (bool): Whether to store the original file

    Returns:
        bool: Success status of the download operation
    """
    start_time = datetime.now()
    logger.info(f"Starting FTP download from: {fasta_uri}")

    try:
        # Parse FTP URI components
        ftp_host = Path(fasta_uri).parts[1]
        ftp_path = "/".join(Path(fasta_uri).parts[2:-1])
        fasta_file = f"../data/{Path(fasta_uri).name}"
        fasta_name = Path(fasta_uri).name

        logger.info(f"FTP Details:")
        logger.info(f"  Host: {ftp_host}")
        logger.info(f"  Path: {ftp_path}")
        logger.info(f"  File: {fasta_name}")
        logger.info(f"Local target: {fasta_file}")

        # Check if file already exists in storage
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

        # Download file
        download_start = datetime.now()
        logger.info("Starting file download")

        try:
            wget.download(fasta_uri, fasta_file)
            download_duration = datetime.now() - download_start

            # Verify downloaded file
            if Path(fasta_file).exists():
                local_size = Path(fasta_file).stat().st_size
                logger.info(
                    f"Download completed:\n"
                    f"  Duration: {download_duration}\n"
                    f"  Local size: {local_size:,} bytes\n"
                    f"  Speed: {local_size / download_duration.total_seconds() / 1024:.2f} KB/s"
                )

                # Verify size if remote size is known
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

        # Store file if requested
        if store_files:
            logger.info(f"Storing original file (store_files=True)")
            try:
                store_fasta_files(fasta_file, logger, store_files)
                logger.info(f"File stored successfully")
            except Exception as e:
                logger.error(f"File storage failed: {str(e)}", exc_info=True)
                return False

        # Skip MD5 check for ZFIN
        if mod == "ZFIN":
            logger.info("Skipping MD5 check for ZFIN")
            return True

        # Verify MD5 checksum
        logger.info(f"Verifying MD5 checksum: expected={md5sum}")
        if check_md5sum(fasta_file, md5sum, logger):
            logger.info("MD5 checksum verification successful")

            # Log overall success
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
            f"FTP download process failed:\n"
            f"  URI: {fasta_uri}\n"
            f"  Error: {str(e)}",
            exc_info=True,
        )
        return False


def get_ftp_file_size(fasta_uri: str, logger) -> int:
    """
    Gets the size of a file on an FTP server with enhanced logging.

    Args:
        fasta_uri (str): FTP URI of the file
        logger (logging.Logger): Logger instance

    Returns:
        int: Size of the file in bytes
    """
    logger.info(f"Getting file size from FTP: {fasta_uri}")

    try:
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
        logger.error(f"Failed to get FTP file size: {str(e)}", exc_info=True)
        return 0


def update_genome_browser_map(config_entry: Dict, logger) -> bool:
    """
    Updates the genome browser mapping files (Ruby and JSON), mapping FASTA filenames
    to genome browser URLs. Creates the files if they don't exist.

    Args:
        config_entry (Dict): Configuration dictionary containing database details
        logger: Logger instance for tracking operations

    Returns:
        bool: Success status
    """
    try:
        ruby_file = Path("../data/config/genome_browser_map.rb")
        json_file = Path("../data/config/genome_browser_map.json")

        # Only process if genome_browser information exists
        if "genome_browser" not in config_entry:
            logger.debug(
                "No genome browser information in config entry, skipping mapping update"
            )
            return True

        filename = Path(config_entry["uri"]).name
        browser_url = config_entry["genome_browser"]["url"]

        # Initialize mapping dict
        current_map = {}

        # Read existing mappings if either file exists
        if ruby_file.exists():
            logger.info(f"Reading existing genome browser mappings from {ruby_file}")
            with open(ruby_file, "r") as f:
                content = f.read()
                # Extract existing mappings using regex
                pattern = r"'([^']+)'\s*=>\s*'([^']+)'"
                matches = re.findall(pattern, content)
                current_map = dict(matches)
                logger.info(f"Found {len(current_map)} existing mappings in Ruby file")
        elif json_file.exists():
            logger.info(f"Reading existing genome browser mappings from {json_file}")
            with open(json_file, "r") as f:
                current_map = json.load(f)
                logger.info(f"Found {len(current_map)} existing mappings in JSON file")

        # Update mapping with new entry
        current_map[filename] = browser_url
        logger.info(f"Adding/updating mapping for {filename}")

        # Ensure config directory exists
        ruby_file.parent.mkdir(parents=True, exist_ok=True)

        # Write updated Ruby mapping
        with open(ruby_file, "w") as f:
            f.write("GENOME_BROWSER_MAP = {\n")
            for fname, url in sorted(current_map.items()):
                f.write(f"  '{fname}' => '{url}',\n")
            f.write("}.freeze\n")
        logger.info(f"Successfully updated Ruby mapping file at {ruby_file}")

        # Write updated JSON mapping
        with open(json_file, "w") as f:
            json.dump(current_map, f, indent=2, sort_keys=True)
        logger.info(f"Successfully updated JSON mapping file at {json_file}")

        return True

    except Exception as e:
        logger.error(
            f"Failed to update genome browser mapping: {str(e)}", exc_info=True
        )
        return False
