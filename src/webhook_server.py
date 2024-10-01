import hashlib
import hmac
import json
import logging
import os
import subprocess
from pathlib import Path

import yaml
from dotenv import find_dotenv, load_dotenv
from flask import Flask, abort, request

# Load environment variables from .env file in src directory
load_dotenv(find_dotenv(filename="src/.env"))

# Ensure logs directory exists
log_file = os.getenv("LOG_FILE", "logs/webhook.log")
log_dir = os.path.dirname(log_file)
Path(log_dir).mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=log_file,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def verify_signature(payload_body, secret_token, signature):
    """Verify that the payload was sent from GitHub by validating SHA256."""
    expected_signature = hmac.new(
        secret_token.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


def run_script(script_path, config_path):
    """Run the create_blast_db.py script."""
    try:
        result = subprocess.run(
            ["python", script_path, "--input_config", config_path],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Script output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running script: {e.stderr}")
        raise


def get_config_files(repo_path):
    """Get all JSON and YAML config files in the repository."""
    config_files = []
    for ext in [".json", ".yaml", ".yml"]:
        config_files.extend(Path(repo_path).glob(f"**/*{ext}"))
    return config_files


def process_config_file(config_file, script_path):
    """Process a single configuration file."""
    file_ext = config_file.suffix.lower()

    if file_ext == ".json":
        with open(config_file, "r") as f:
            config_data = json.load(f)
    elif file_ext in [".yaml", ".yml"]:
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
    else:
        logger.warning(f"Unsupported file type: {file_ext}")
        return

    # Extract necessary information from config_data
    # This part may need to be adjusted based on your specific JSON/YAML structure
    input_json = config_data.get("input_json")
    environment = config_data.get("environment", "dev")
    mod = config_data.get("mod")

    if input_json:
        run_script(script_path, str(config_file))
    else:
        logger.warning(f"No input_json found in {config_file}")


@app.route("/webhook", methods=["POST"])
def webhook():
    # Verify GitHub webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        logger.warning("No signature provided")
        abort(400, "No signature provided")

    github_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not github_secret:
        logger.error("GitHub webhook secret not configured")
        abort(500, "Server configuration error")

    if not verify_signature(request.data, github_secret, signature):
        logger.warning("Invalid signature")
        abort(401, "Invalid signature")

    # Parse the payload
    payload = request.json

    # Check if it's a push event
    if request.headers.get("X-GitHub-Event") != "push":
        logger.info(f"Received non-push event: {request.headers.get('X-GitHub-Event')}")
        return "OK", 200

    # Get the repository details
    repo_name = payload["repository"]["full_name"]
    branch = payload["ref"].split("/")[-1]

    logger.info(f"Received push event for {repo_name} on branch {branch}")

    try:
        # Update the local repository
        repo_path = os.getenv("REPO_LOCAL_PATH")
        if not repo_path:
            logger.error("Repository local path not configured")
            abort(500, "Server configuration error")

        subprocess.run(["git", "-C", repo_path, "pull", "origin", branch], check=True)
        logger.info(f"Successfully pulled latest changes for {repo_name}")

        # Get the script path
        script_path = os.getenv("SCRIPT_PATH")
        if not script_path:
            logger.error("Script path not configured")
            abort(500, "Server configuration error")

        # Process all config files
        config_files = get_config_files(repo_path)
        for config_file in config_files:
            process_config_file(config_file, script_path)

        return "OK", 200
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in git pull or running script: {e}")
        abort(500, "Error processing webhook")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
