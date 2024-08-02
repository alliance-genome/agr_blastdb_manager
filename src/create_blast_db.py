"""
utils.py

This module contains utility functions used across the project. These functions include
logging setup, MD5 checksum verification, FASTA file editing, S3 syncing, and Slack messaging.

Authors: Paulo Nuin, Adam Wright
Date: Started September 2023, Refactored [Current Date]
"""

import hashlib
import logging
from pathlib import Path
import subprocess
from typing import Dict, List, Optional
import os
import math

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from rich.console import Console

# Load environment variables
load_dotenv()

console = Console()

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name (str): Name of the logger.
        log_file (Optional[str]): Path to the log file. If None, only console logging is set up.
        level (int): Logging level.

    Returns:
        logging.Logger: Configured logger object.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler (if log_file is provided)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def check_md5sum(file_path: Path, expected_md5: str) -> bool:
    """
    Check the MD5 checksum of a file.

    Args:
        file_path (Path): Path to the file to check.
        expected_md5 (str): Expected MD5 checksum.

    Returns:
        bool: True if checksums match, False otherwise.
    """
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)

    calculated_md5 = file_hash.hexdigest()
    if calculated_md5 != expected_md5:
        console.log(f"MD5 mismatch for {file_path}: expected {expected_md5}, got {calculated_md5}")
        return False

    console.log(f"MD5 match for {file_path}: {calculated_md5}")
    return True

def edit_fasta(fasta_file: Path, config_entry: Dict[str, str]) -> bool:
    """
    Edit the FASTA file based on the configuration entry.

    Args:
        fasta_file (Path): Path to the FASTA file to edit.
        config_entry (Dict[str, str]): Configuration entry containing additional information.

    Returns:
        bool: True if edit was successful, False otherwise.
    """
    try:
        with open(fasta_file, 'r') as f:
            lines = f.readlines()

        edited_lines = []
        for line in lines:
            if line.startswith('>'):
                line = line.strip()
                if "seqcol" in config_entry:
                    line += f" {config_entry['seqcol']} {config_entry['genus']} {config_entry['species']}\n"
                else:
                    line += f" {config_entry['genus']} {config_entry['species']} {config_entry['version']}\n"
            edited_lines.append(line)

        with open(fasta_file, 'w') as f:
            f.writelines(edited_lines)

        return True
    except Exception as e:
        console.log(f"Error editing FASTA file {fasta_file}: {e}")
        return False

def s3_sync(path_to_copy: Path, skip_efs_sync: bool) -> bool:
    """
    Sync files from a local directory to an S3 bucket.

    Args:
        path_to_copy (Path): The path to the local directory to be synced.
        skip_efs_sync (bool): Whether to skip syncing to EFS.

    Returns:
        bool: True if sync was successful, False otherwise.
    """
    console.log(f"Syncing {path_to_copy} to S3")

    s3_sync_command = [
        "aws", "s3", "sync",
        str(path_to_copy),
        os.environ["S3_BUCKET"],
        "--exclude", "*.tmp",
        "--verbose",
        "--progress"
    ]

    try:
        result = subprocess.run(s3_sync_command, check=True, capture_output=True, text=True)
        for line in result.stderr.splitlines():
            console.log(line)

        console.log(f"Syncing {path_to_copy} to S3: done")

        if not skip_efs_sync:
            return sync_to_efs()
        return True
    except subprocess.CalledProcessError as e:
        console.log(f"Error syncing to S3: {e}")
        return False

def sync_to_efs() -> bool:
    """
    Sync files from an S3 bucket to an EFS volume.

    Returns:
        bool: True if sync was successful, False otherwise.
    """
    s3_path = os.environ.get("S3_BUCKET")
    efs_path = os.environ.get("EFS_PATH")

    if not s3_path or not efs_path:
        console.log("S3 or EFS path is not defined in the environment variables")
        return False

    console.log(f"Syncing {s3_path} to {efs_path}")

    efs_sync_command = [
        "aws", "s3", "sync",
        s3_path,
        efs_path,
        "--exclude", "*.tmp"
    ]

    try:
        result = subprocess.run(efs_sync_command, check=True, capture_output=True, text=True)
        for line in result.stderr.splitlines():
            console.log(line)

        console.log(f"Syncing {s3_path} to {efs_path}: done")
        return True
    except subprocess.CalledProcessError as e:
        console.log(f"Error syncing to EFS: {e}")
        return False

def get_mod_from_json(json_file: Path) -> Optional[str]:
    """
    Extract the model organism (MOD) from the JSON filename.

    Args:
        json_file (Path): Path to the JSON file.

    Returns:
        Optional[str]: The extracted MOD if found, None otherwise.
    """
    filename = json_file.name
    parts = filename.split('.')
    if len(parts) > 1:
        mod = parts[1]
        if mod in ["FB", "SGD", "WB", "XB", "ZFIN"]:
            console.log(f"MOD found: {mod}")
            return mod

    console.log(f"MOD not found in filename: {filename}")
    return None

def send_slack_message(messages: List[Dict[str, str]], batch_size: int = 20) -> None:
    """
    Send messages to Slack, handling large numbers of messages by batching and summarizing.

    Args:
        messages (List[Dict[str, str]]): List of message dictionaries to send.
        batch_size (int): Number of messages to include in each Slack message.
    """
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
    channel = "#blast-status"

    total_messages = len(messages)
    batches = math.ceil(total_messages / batch_size)

    for i in range(batches):
        start = i * batch_size
        end = min((i + 1) * batch_size, total_messages)
        batch = messages[start:end]

        summary_text = f"Processed sequences {start+1}-{end} of {total_messages}"

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{summary_text}*"}
            },
            {
                "type": "divider"
            }
        ]

        for msg in batch:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{msg['title']}*\n{msg['text']}"},
                "color": msg['color']
            })

        try:
            response = client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
        except SlackApiError as e:
            console.log(f"Error sending message to Slack: {e}")

    # Send a final summary message
    try:
        client.chat_postMessage(
            channel=channel,
            text=f"Completed processing {total_messages} sequences."
        )
    except SlackApiError as e:
        console.log(f"Error sending summary message to Slack: {e}")
