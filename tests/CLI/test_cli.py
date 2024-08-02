# blastn -db
# /Users/nuin/Projects/wormbase/blast/agr_blastdb_manager/data/blast/SGD/fungal/databases/Zygosaccharomyces/rouxii/Z_rouxii_Genome_Assembly/zygosaccharomyces_rouxii_genomicdb
# -query input_files/SGD.fasta                               │


import pathlib
from pathlib import Path
import click
import json
from subprocess import Popen, PIPE


def run_blast(db, fasta, mod, environment):

    print(db)
    temp = open("temp.fasta", "w")
    temp.write(fasta)
    temp.close()

    blast_command = f"blastn -db {db} -query temp.fasta -out output/{mod}/{environment}/{Path(db).name}.txt -num_threads 4 -evalue 1 -outfmt 6"

    print(blast_command)
    p = Popen(blast_command, shell=True, stdout=PIPE, stderr=PIPE)


@click.command()
@click.option("-d", "--datadir", help="The path to the data directory", required=True)
@click.option("-M", "--mod", help="The MOD to test", required=True)
@click.option("-e", "--environment", help="The environment to test", required=True)
def setup_blast(datadir, mod, environment):

    data = json.loads(open("config.json").read())

    p = pathlib.Path(f"{datadir}/{mod}/{environment}/databases/")
    dbs = data[mod][environment]["dbs"]
    fasta = f">test\n{data[mod][environment]["nucl"]}"


    for db in dbs:
        full_dir = p / db
        run_blast(full_dir, fasta, mod, environment)



if __name__ == "__main__":
    setup_blast()