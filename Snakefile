from pathlib import Path
from agr_blastdb_manager.genbank import genomes
from agr_blastdb_manager.agr.snakemake import write_db_metadata_files, expected_blast_files, get_blastdb_obj, file_md5_is_valid


configfile: "conf/global.yaml"

DATA_DIR = Path(config.get("DATA_DIR", 'data'))
# Use user specified directories or default to subdirectories of the data directory.
FASTA_DIR = config.get("FASTA_DIR", Path(DATA_DIR,"fasta"))
BLASTDB_DIR = config.get("BLASTDB_DIR", Path(DATA_DIR,"blast"))
META_DIR = config.get("META_DIR", Path(DATA_DIR,"meta"))

# Path to NCBI makeblastdb binary
MAKEBLASTDB_BIN = config.get("MAKEBLASTDB_BIN", Path("/usr","local","ncbi","blast","bin","makeblastdb"))

blast_files = []
for mod, mod_json in config["mods"].items():
        blast_files.append(
            expected_blast_files(
                db_files=write_db_metadata_files(
                    mod=mod,
                    json_file=mod_json,
                    db_meta_dir=META_DIR
                ),
            mod=mod,
            base_dir=BLASTDB_DIR
            )
        )



#=========================================================
# Global wildcard regex patterns.
#=========================================================
wildcard_constraints:
    genus="[A-Za-z]+",
    species="[A-Za-z_]+",
    org="[A-Za-z]+_[A-Za-z_]+",
    fasta="[\w\._\-]+(\.gz|\.bz2|\.fasta|\.fa|\.f[na]a)"

rule all:
    input: blast_files

rule makeblastdb:
    output: touch(Path(BLASTDB_DIR,"{mod}", "{org}", "{fasta}.done"))
    input:
        fa=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.org, wildcards.fasta),
        md5=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.org, wildcards.fasta + '.md5_validated')
    params:
        db_info=lambda wildcards: get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod),
        # TODO - This will fail with certain variations of filename extensions.
        # Strip the '.gz.done' from the output name
        out=lambda wildcards, output: Path(str(output)).with_suffix('').with_suffix('')
    log: "logs/makeblastdb_{mod}_{org}_{fasta}.log"
    shell:
        """
        dirname {output} | xargs mkdir -p
        gunzip -c {input.fa} | {MAKEBLASTDB_BIN} -in - -dbtype {params.db_info.seqtype} \
            -title "{params.db_info.blast_title}" -parse_seqids -out {params.out} \
            -taxid {params.db_info.taxon_id} -logfile {log} 2>&1
        """

rule validate_fasta_md5:
    output: touch(Path(FASTA_DIR, "{mod}", "{org}", "{fasta}.md5_validated"))
    input: lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.org, wildcards.fasta)
    params:
        db_info=lambda wildcards: get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod),
    run:
        is_valid = file_md5_is_valid(fasta_file=Path(str(input)), checksum=params.db_info.md5sum)
        if not is_valid:
            raise Exception("Invalid MD5 checksum")


rule retrieve_fasta:
    output: Path(FASTA_DIR, "{mod}", "{org}", "{fasta}")
    params:
        dir_prefix=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.org),
        db_info=lambda wildcards: get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod)
    log: "logs/wget_{mod}_{org}_{fasta}.log"
    run:
        shell("wget -c --timestamping {params.db_info.URI} --directory-prefix {params.dir_prefix} -o {log}")

# rule retrieve_ncbi_genome:
#     output: expand(Path(FASTA_DIR, "{org}", "{{ncbi_fasta}}"), org=["Drosophila_erecta"])
#     params:
#         organism=lambda wildcards: wildcards.org.split('_', maxsplit=2)
#     wildcard_constraints:
#         ncbi_fasta="GC[AF]_.*_(genomic|protein|rna)\.f[an]a\.gz"
#     run:
#         for o in output:
#             output_path = Path(o)
#             genomes.fetch_genome_files(genus=params.organism[0],
#                                        species=params.organism[1],
#                                        output_dir=output_path.parent)
#
#
# rule retrieve_dmel_fasta:
#     output: Path(FASTA_DIR, "Drosophila_melanogaster", "{fasta}")
#     params:
#         dir_prefix= Path(FASTA_DIR, "Drosophila_melanogaster")
#     log: "logs/wget_{fasta}.log"
#     shell:
#         """
#         wget -c --timestamping ftp://ftp.flybase.org/genomes/dmel/current/fasta/{wildcards.fasta} \
#              --directory-prefix {params.dir_prefix} -o {log}
#         """
#
# rule makeblastdb_dmel_nucleotide:
#     input: lambda wildcards: expand(Path(FASTA_DIR, "Drosophila_melanogaster","{fasta}"), fasta=DBS["Drosophila_melanogaster"][wildcards.blastdb]["fasta"])
#     output: Path(BLASTDB_DIR,"Drosophila_melanogaster","{blastdb}.nin")
#     params:
#         title=lambda wildcards: DBS["Drosophila_melanogaster"][wildcards.blastdb]["title"],
#         taxid=get_taxid("Drosophila", "melanogaster"),
#         dbpath=lambda wildcards, output: Path(str(output)).with_suffix('')
#     log: "logs/dmel_{blastdb}_makeblastdb.log"
#     shell:
#         """
#         gunzip -c {input} | {MAKEBLASTDB_BIN} -in - -dbtype nucl \
#             -title "{params.title}" -parse_seqids -out {params.dbpath} \
#             -taxid {params.taxid} -logfile {log} 2>&1
#         """
#
# rule makeblastdb_dmel_protein:
#     input: lambda wildcards: expand(Path(FASTA_DIR, "Drosophila_melanogaster","{fasta}"), fasta=DBS["Drosophila_melanogaster"][wildcards.blastdb]["fasta"])
#     output: Path(BLASTDB_DIR,"Drosophila_melanogaster","{blastdb}.pin")
#     params:
#         title=lambda wildcards: DBS["Drosophila_melanogaster"][wildcards.blastdb]["title"],
#         taxid=get_taxid("Drosophila", "melanogaster"),
#         dbpath=lambda wildcards, output: Path(str(output)).with_suffix('')
#     log: "logs/dmel_{blastdb}_makeblastdb.log"
#     shell:
#         """
#         gunzip -c {input} | {MAKEBLASTDB_BIN} -in - -dbtype prot \
#             -title "{params.title}" -parse_seqids -out {params.dbpath} \
#             -taxid {params.taxid} -logfile {log} 2>&1
#         """
