# Paulo Nuin July 2023

import json
import urllib.request
from pathlib import Path
import hashlib

import click
from rich.console import Console

console = Console()


def check_md5sum(fasta_file, md5sum) -> bool:
    """
    Function that checks the md5sum of the downloaded file
    """

    downloaded_md5sum = hashlib.md5(open(fasta_file, 'rb').read()).hexdigest()
    # console.log(f"Expected md5sum: {md5sum}")
    # console.log(f"Downloaded md5sum: {downloaded_md5sum}")
    if downloaded_md5sum != md5sum:
        console.log(f"MD5sums do not match: {md5sum} != {downloaded_md5sum}")
        return False
    else:
        console.log(f"MD5sums match: {md5sum} {downloaded_md5sum}")
        return True


def get_files_ftp(fasta_uri, md5sum, dry_run) -> bool:
    """
    Function that downloads the files from the FTP site
    :param fasta_url:
    :param dry_run:
    :return:
    """
    try:
        console.log(f"Downloading {fasta_uri}")
        if dry_run:
            console.log("Dry run, not downloading")

        fasta_file = f"../data/{Path(fasta_uri).name}"
        console.log(f"Saving to {fasta_file}")

        if not dry_run:
            if not Path(fasta_file).exists():
                with urllib.request.urlopen(fasta_uri) as r:
                    data = r.read()
                    with open(fasta_file, "wb") as f:
                        f.write(data)
            else:
                console.log(f"{fasta_file} already exists")
            check_md5sum(fasta_file, md5sum)
        return True
    except Exception as e:
        console.log(f"Error downloading {fasta_uri}: {e}")
        return False


@click.command()
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-d", "--dry_run", help="Don't download anything", is_flag=True)
def create_dbs(input_json, dry_run=False):

    db_coordinates = json.load(open(input_json, "r"))

    for entry in db_coordinates["data"]:
        get_files_ftp(entry["uri"], entry["md5sum"], dry_run)


if __name__ == "__main__":

    create_dbs()
