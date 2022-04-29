#!/usr/bin/env python3
import argparse
from pathlib import Path
from Bio import Entrez
from agr_blastdb_manager.ncbi import taxonomy as tax
from agr_blastdb_manager.ncbi import genomes as genomes
import agr_blastdb_manager.agr.metadata as blast_metadata

import logging

project_dir = Path(__file__).resolve().parent.parent

logging.basicConfig(
    filename=Path(project_dir, "logs", "create_flybase_metadata.log"),
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logger = logging.getLogger(__name__)


def flyblast_organisms() -> tuple[tuple[str, str], ...]:
    """
    Returns a tuple of tuples of the form (genus, species) for each organism
    the FlyBase BLAST databases.
    """
    return (
        ("Drosophila", "grimshawi"),
        ("Drosophila", "albomicans"),
        ("Drosophila", "ananassae"),
        ("Drosophila", "arizonae"),
        ("Drosophila", "biarmipes"),
        ("Drosophila", "bipectinata"),
        ("Drosophila", "busckii"),
        ("Drosophila", "elegans"),
        ("Drosophila", "erecta"),
        ("Drosophila", "eugracilis"),
        ("Drosophila", "ficusphila"),
        ("Drosophila", "grimshawi"),
        ("Drosophila", "guanche"),
        ("Drosophila", "hydei"),
        ("Drosophila", "innubila"),
        ("Drosophila", "kikkawai"),
        ("Drosophila", "mauritiana"),
        # ("Drosophila", "melanogaster"),
        ("Drosophila", "miranda"),
        ("Drosophila", "mojavensis"),
        ("Drosophila", "navojoa"),
        ("Drosophila", "novamexicana"),
        ("Drosophila", "obscura"),
        ("Drosophila", "persimilis"),
        ("Drosophila", "pseudoobscura"),
        ("Drosophila", "rhopaloa"),
        ("Drosophila", "santomea"),
        ("Drosophila", "sechellia"),
        ("Drosophila", "serrata"),
        ("Drosophila", "simulans"),
        ("Drosophila", "subobscura"),
        ("Drosophila", "subpulchrella"),
        ("Drosophila", "suzukii"),
        ("Drosophila", "takahashii"),
        ("Drosophila", "teissieri"),
        ("Drosophila", "virilis"),
        ("Drosophila", "willistoni"),
        ("Drosophila", "yakuba"),
        ("Musca", "domestica"),
        ("Glossina", "morsitans morsitans"),
        ("Culex", "quinquefasciatus"),
        ("Aedes", "aegypti"),
        ("Anopheles", "darlingi"),
        ("Anopheles", "gambiae"),
        ("Mayetiola", "destructor"),
        ("Bombyx", "mori"),
        ("Danaus", "plexippus"),
        ("Tribolium", "castaneum"),
        ("Nasonia", "giraulti"),
        ("Nasonia", "longicornis"),
        ("Nasonia", "vitripennis"),
        ("Apis", "mellifera"),
        ("Apis", "florea"),
        ("Bombus", "impatiens"),
        ("Bombus", "terrestris"),
        ("Megachile", "rotundata"),
        ("Acromyrmex", "echinatior"),
        ("Atta", "cephalotes"),
        ("Camponotus", "floridanus"),
        ("Harpegnathos", "saltator"),
        ("Linepithema", "humile"),
        ("Pogonomyrmex", "barbatus"),
        ("Solenopsis", "invicta"),
        ("Acyrthosiphon", "pisum"),
        ("Rhodnius", "prolixus"),
        ("Pediculus", "humanus corporis"),
        ("Ixodes", "scapularis"),
        ("Rhipicephalus", "microplus"),
    )


def create_flybase_metadata(options: argparse.Namespace) -> None:
    dbs = []
    assembly_targets = [
        {
            "file_regex": "(?<!_from)_genomic.fna.gz$",
            "blast_title": "{}. {} Genome Assembly ({})",
            "description": "{} {} genome assembly",
        },
        {
            "file_regex": "_protein.faa.gz$",
            "blast_title": "{}. {} Protein Sequences ({})",
            "description": "{} {} protein sequences",
        },
    ]
    for genus, species in flyblast_organisms():
        logger.info(f"Creating metadata for {genus} {species}")
        for target in assembly_targets:
            assembly_files = genomes.get_current_genome_assembly_files(
                genus, species, file_regex=target["file_regex"]
            )
            if not assembly_files:
                logger.error(f"No assembly files found for {genus} {species}")
                continue

            # Get taxonomy ID.
            taxid = tax.get_taxonomy_id(genus, species)
            db = {
                "version": assembly_files[0],
                "URI": assembly_files[1],
                "md5sum": assembly_files[2],
                "genus": genus,
                "species": species,
                "blast_title": target["blast_title"].format(
                    genus[0].upper(), species, assembly_files[0]
                ),
                "description": target["description"].format(genus, species),
                "taxon_id": f"NCBITaxon:{taxid}",
            }
            dbs.append(blast_metadata.BlastDBMetaData(**db))

    dbs.extend(
        [
            blast_metadata.BlastDBMetaData(
                version=options.dmel_annot,
                URI=f"ftp://ftp.flybase.org/genomes/Drosophila_melanogaster/dmel_r{options.dmel_annot}_{options.release}/fasta/dmel-all-chromosome-r{options.dmel_annot}.fasta.gz",
                md5sum="8dd4464e993ffdcf8591719255a4a3d8",  # TODO - Hard coded for now, need to fetch this from the MD5SUM file
                genus="Drosophila",
                species="melanogaster",
                blast_title=f"D. melanogaster Genome Assembly ({options.dmel_annot})",
                description="Drosophila melanogaster genome assembly",
                taxon_id="NCBITaxon:7227",
            ),
            blast_metadata.BlastDBMetaData(
                version=options.dmel_annot,
                URI=f"ftp://ftp.flybase.org/genomes/Drosophila_melanogaster/dmel_r{options.dmel_annot}_{options.release}/fasta/dmel-all-translation-r{options.dmel_annot}.fasta.gz",
                # TODO - Hard coded for now, need to fetch this from the MD5SUM file
                md5sum="57912149894db436a70e0926c9364998",
                genus="Drosophila",
                species="melanogaster",
                blast_title=f"D. melanogaster Protein Sequences ({options.dmel_annot})",
                description="Drosophila melanogaster protein sequences",
                taxon_id="NCBITaxon:7227",
            ),
        ]
    )

    flybase_blast_metadata = blast_metadata.AGRBlastDatabases(
        metaData=blast_metadata.AGRBlastMetadata(
            contact=options.email, dataProvider="FlyBase", release=options.release
        ),
        data=dbs,
    )
    print(flybase_blast_metadata.json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate FlyBase databases metadata file."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for metadata contact info and NCBI Entrez queries.",
    )
    parser.add_argument(
        "--release", required=True, help="FlyBase release number. e.g. FB2022_01"
    )
    parser.add_argument(
        "--dmel-annot",
        dest="dmel_annot",
        required=True,
        help="Dmel Annotation release number. e.g. 6.45",
    )
    args = parser.parse_args()
    Entrez.email = args.email
    create_flybase_metadata(options=args)
