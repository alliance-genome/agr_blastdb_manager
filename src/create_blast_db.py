# Paulo Nuin July 2023

import hashlib
import json
import urllib.request
from pathlib import Path
from subprocess import PIPE, Popen

import click
from rich.console import Console

console = Console()
MAKEBLASTDB_BIN = "/usr/local/bin/makeblastdb"


def check_md5sum(fasta_file, md5sum) -> bool:
    """
    Function that checks the md5sum of the downloaded file
    :param fasta_file:
    :param md5sum:
    """

    downloaded_md5sum = hashlib.md5(open(fasta_file, "rb").read()).hexdigest()
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
    :param fasta_uri:
    :param md5sum:
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
            if not Path(fasta_file.replace(".gz", "")).exists():
                if not Path(fasta_file).exists():
                    with urllib.request.urlopen(fasta_uri) as r:
                        data = r.read()
                        with open(fasta_file, "wb") as f:
                            f.write(data)
                else:
                    console.log(f"{fasta_file} already exists")
                if not check_md5sum(fasta_file, md5sum):
                    return False
            return True
    except Exception as e:
        console.log(f"Error downloading {fasta_uri}: {e}")
        return False


def create_db_structure(environment, mod, config_entry, dry_run) -> bool:
    """
    Function that creates the database and folder structure
    :param environment:
    :param mod:
    :param config_entry:
    :param dry_run:
    """

    if "seqcol" in config_entry.keys():
        console.log(
            f"Directory '../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}"
            f"/{config_entry['blast_title']}/' will be created"
        )
        p = f"../data/blast/{mod}/{environment}/databases/{config_entry['seqcol']}/{config_entry['blast_title']}/"
    else:
        console.log(
            f"Directory '../data/blast/{mod}/{environment}/databases/{config_entry['genus']}"
            f"{config_entry['species']}"
            f"/{config_entry['blast_title']}/' will be created"
        )
        p = (
            f"../data/blast/{mod}/{environment}/databases/{config_entry['genus']}/{config_entry['species']}/"
            f"{config_entry['blast_title'].replace(' ', '_')}/"
        )

    Path(p).mkdir(parents=True, exist_ok=True)
    console.log(f"Directory {p} created")

    return p


def run_makeblastdb(config_entry, output_dir, dry_run):
    """
    Function that runs makeblastdb
    """

    fasta_file = Path(config_entry["uri"]).name
    console.log(f"Running makeblastdb for {fasta_file}")

    if not Path(f"../data/{fasta_file.replace('.gz', '')}").exists():
        unzip_command = f"gunzip -v ../data/{fasta_file}"
        p = Popen(unzip_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        console.log(f"Unzip: done")
    else:
        console.log("File already unzipped")

        # if not dry_run:
        makeblast_command = (
            f"{MAKEBLASTDB_BIN} -in ../data/{fasta_file.replace('.gz', '')} -dbtype {config_entry['seqtype']} "
            f"-title '{config_entry['blast_title']}' -parse_seqids "
            f"-out {output_dir}/{fasta_file.replace('fa.gz', 'db ')}"
            f"-taxid {config_entry['taxon_id'].replace('NCBITaxon:', '')} "
        )
        p = Popen(makeblast_command, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        stdout, stderr = p.communicate()
        console.log(f"Makeblastdb: done")
        console.log(f"stdout: {stdout}")


@click.command()
@click.option("-j", "--input_json", help="JSON file input coordinates", required=True) # glob for multiple files or from the YAML file
@click.option("-d", "--dry_run", help="Don't download anything", is_flag=True, default=False)
@click.option("-e", "--environment", help="Environment", default="prod")
@click.option("-m", "--mod", help="Model organism")
def create_dbs(input_json, dry_run, environment, mod):
    db_coordinates = json.load(open(input_json, "r"))

    for entry in db_coordinates["data"]:
        if get_files_ftp(entry["uri"], entry["md5sum"], dry_run):
            output_dir = create_db_structure(environment, mod, entry, dry_run)
            if Path(output_dir).exists():
                run_makeblastdb(entry, output_dir, dry_run)


if __name__ == "__main__":
    create_dbs()
