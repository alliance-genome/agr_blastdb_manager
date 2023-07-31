# Paulo Nuin July 2023

import json
import urllib.request
from pathlib import Path

import click
from rich.console import Console

console = Console()


def get_files_ftp(fasta_uri, dry_run):
    """
    Function that downloads the files from the FTP site
    :param fasta_url:
    :param gff_url:
    :param fasta_file:
    :param gff_file:
    :return:
    """

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


@click.command()
@click.option("-j", "--input_json", help="JSON file input coordinates")
@click.option("-d", "--dry_run", help="Don't download anything", is_flag=True)
def create_dbs(input_json, dry_run=False):

    db_coordinates = json.load(open(input_json, "r"))

    for entry in db_coordinates["data"]:
        get_files_ftp(entry["uri"], dry_run)


if __name__ == "__main__":

    create_dbs()
