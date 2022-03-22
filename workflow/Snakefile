from pathlib import Path
from typing import Iterator

DATA_DIR = Path("data")
FASTA_DIR = Path(DATA_DIR,"fasta")
BLASTDB_DIR = Path(DATA_DIR,"blastdb")
MAKEBLASTDB_BIN = Path("/usr","local","ncbi","blast","bin","makeblastdb")

BLASTDB_EXTS = {
    "nucl": ['.ndb', '.nhr', '.nin', '.nog', '.nos', '.not', '.nsq', '.ntf', '.nto'],
    "prot": ['.pdb', '.phd', '.phi', '.phr', '.pin', '.pog', '.pos', '.pot', '.psq', '.ptf', '.pto']
}

ORGANISMS = [
    {
        "genus": "Drosophila",
        "species": "melanogaster",
        "taxid": 7227
    },
    #{"genus": "Drosophila", "species": "erecta", "taxid": 7220 },
]

DBS = {
    "Drosophila_melanogaster": {
        "genomic": {
            "fasta": ["dmel-all-chromosome-r6.44.fasta.gz"],
            "title": "Drosophila melanogaster assembly",
            "dbtype": "nucl"
        },
        "genes": {
            "fasta": [
                "dmel-all-miRNA-r6.44.fasta.gz",
                "dmel-all-miscRNA-r6.44.fasta.gz",
                "dmel-all-ncRNA-r6.44.fasta.gz",
                "dmel-all-pseudogene-r6.44.fasta.gz",
                "dmel-all-transcript-r6.44.fasta.gz",
                "dmel-all-tRNA-r6.44.fasta.gz",
            ],
            "title": "Drosophila melanogaster annoated genes",
            "dbtype": "nucl"
        },
        "protein": {
            "fasta": ["dmel-all-translation-r6.44.fasta.gz"],
            "title": "Drosophila melanogaster annotated proteins",
            "dbtype": "prot"
        }
    }
}

def get_taxid(genus: str, species: str) -> int:
    """
    Return the taxonomy ID

    :param genus:
    :param species:
    :return:
    """
    organism = next((o for o in ORGANISMS if o["genus"] == genus and o["species"] == species), None)
    return organism["taxid"] if organism else organism


def get_organism_paths(organisms: list[dict] = None) -> Iterator[str]:
    if organisms is None: organisms = []

    for org in organisms:
        yield org['genus'] + '_' + org['species']


def get_fasta(wildcards: dict) -> list:
    print(list(wildcards.keys()))
    dbtype = wildcards["blastdb"]
    org: str = wildcards["org"]

    for fasta_files in DBS[org][dbtype]:
        yield Path(BLASTDB_DIR,fasta_files)


#=========================================================
# Global wildcard regex patterns.
#=========================================================
wildcard_constraints:
    org="[A-Za-z]+_[A-Za-z]+",
    annot_rel="\d+\.\d+"

rule all:
    input:
        expand(Path(BLASTDB_DIR, "{org}/genomic.nin"), org=get_organism_paths(ORGANISMS)),
        expand(Path(BLASTDB_DIR,"{org}/protein.pin"), org=get_organism_paths(ORGANISMS)),
        expand(Path(BLASTDB_DIR,"{org}/genes.nin"),org=get_organism_paths(ORGANISMS))

#expand("{blastdbdir}/{org}/gene.nin", blastdbdir=BLASTDB_DIR, org=get_organism_paths(ORGANISMS)),
    #expand("{blastdbdir}/{org}/protein.nin", blastdbdir=BLASTDB_DIR, org=get_organism_paths(ORGANISMS)),
    #expand("{blastdb}/{org}/gene.{ext}",blastdb=BLASTDB_DIR,org=get_organism_paths(ORGANISMS), ext=BLASTDB_EXTS['nucl']),
    #expand("{blastdb}/{org}/protein.{ext}",blastdb=BLASTDB_DIR,org=get_organism_paths(ORGANISMS),ext=BLASTDB_EXTS['prot'])

rule retrieve_dmel_fasta:
    output: Path(FASTA_DIR, "Drosophila_melanogaster", "{fasta}")
    params:
        dir_prefix= Path(FASTA_DIR, "Drosophila_melanogaster")
    log: "logs/wget_{fasta}.log"
    shell:
        """
        wget -c --timestamping ftp://ftp.flybase.org/genomes/dmel/current/fasta/{wildcards.fasta} \
             --directory-prefix {params.dir_prefix} -o {log}
        """

rule makeblastdb_non_dmel:
    output: expand(Path(BLASTDB_DIR,"{org}","{{blastdb}}.nin"), org=['Drosophila_erecta'])
    log: "logs/{blastdb}_makeblastdb.log"
    shell:
        """
        echo "Hello" > {output} 2> {log}
        """

rule makeblastdb_dmel_nucleotide:
    input: lambda wildcards: expand(Path(FASTA_DIR, "Drosophila_melanogaster","{fasta}"), fasta=DBS["Drosophila_melanogaster"][wildcards.blastdb]["fasta"])
    output: Path(BLASTDB_DIR,"Drosophila_melanogaster","{blastdb}.nin")
    params:
        title=lambda wildcards: DBS["Drosophila_melanogaster"][wildcards.blastdb]["title"],
        taxid=get_taxid("Drosophila", "melanogaster"),
        dbpath=lambda wildcards, output: Path(str(output)).with_suffix('')
    log: "logs/dmel_{blastdb}_makeblastdb.log"
    shell:
        """
        gunzip -c {input} | {MAKEBLASTDB_BIN} -in - -dbtype nucl \
            -title "{params.title}" -parse_seqids -out {params.dbpath} \
            -taxid {params.taxid} -logfile {log} 2>&1
        """

rule makeblastdb_dmel_protein:
    input: lambda wildcards: expand(Path(FASTA_DIR, "Drosophila_melanogaster","{fasta}"), fasta=DBS["Drosophila_melanogaster"][wildcards.blastdb]["fasta"])
    output: Path(BLASTDB_DIR,"Drosophila_melanogaster","{blastdb}.pin")
    params:
        title=lambda wildcards: DBS["Drosophila_melanogaster"][wildcards.blastdb]["title"],
        taxid=get_taxid("Drosophila", "melanogaster"),
        dbpath=lambda wildcards, output: Path(str(output)).with_suffix('')
    log: "logs/dmel_{blastdb}_makeblastdb.log"
    shell:
        """
        gunzip -c {input} | {MAKEBLASTDB_BIN} -in - -dbtype prot \
            -title "{params.title}" -parse_seqids -out {params.dbpath} \
            -taxid {params.taxid} -logfile {log} 2>&1
        """
