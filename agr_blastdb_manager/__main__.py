#!/usr/bin/env python3
import logging
from pathlib import Path
from agr_blastdb_manager.genbank import genomes

logging.basicConfig(encoding='utf-8', level=logging.DEBUG, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Project root directory
project_dir = Path(__file__).resolve().parent.parent
# Data directory
data_dir = project_dir.joinpath('data')


def connect_ncbi():
    logging.debug("Fetching Genomes")

    logging.debug(data_dir)
    #output_dir = join(abspath(join(dirname(__file__), '..')), 'data', 'fasta', 'Drosophila_erecta')
    #Path.makedir(output_dir, exist_ok=True)
    # genomes.fetch_genome_files(genus="Drosophila", species="erecta", output_dir=output_dir)
    return None


if __name__ == '__main__':
    connect_ncbi()
