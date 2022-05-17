from pathlib import Path
import agr_blastdb_manager.agr.snakemake as agr_sm


configfile: "conf/global.yaml"

DATA_DIR = Path(config.get("DATA_DIR", 'data'))
# Use user specified directories or default to subdirectories of the data directory.
FASTA_DIR = config.get("FASTA_DIR", Path(DATA_DIR,"fasta"))
BLASTDB_DIR = config.get("BLASTDB_DIR", Path(DATA_DIR,"blast"))
META_DIR = config.get("META_DIR", Path(DATA_DIR,"meta"))

# Path to NCBI makeblastdb binary
MAKEBLASTDB_BIN = config.get("MAKEBLASTDB_BIN", Path("/usr","local","ncbi","blast","bin","makeblastdb"))

# Build the list of BLAST indices that we are expecting from the pipeline.
# This is used as the starting point for our pipeline. Snakemake uses this to
# build a list of dependent rules (DAG) that need to be executed to produce them.
blast_files = []
# Loop over each MOD defined in conf/global.yaml.
for mod, mod_json in config["mods"].items():
        blast_files.append(
            # Using the list of metadata files, returns a list of expected BLAST database files.
            agr_sm.expected_blast_files(
                # Reads the MOD metadata file and writes the individual database metadata
                # to its own file that is used throughout the pipeline.
                # Returns a list of files written.
                db_files=agr_sm.write_db_metadata_files(
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


#=========================================================
# Start of pipeline.
#=========================================================
rule all:
    input: blast_files

#============================================================================
# Generate the blast databases using the NCBI makeblastdb command.
# Takes the FASTA file and a file that indicates that the MD5 checksum
# from the metadata validates the file that was mirrored.
#============================================================================
rule makeblastdb:
    output: touch(Path(BLASTDB_DIR,"{mod}", "{genus}", "{org}", "{fasta}.done"))
    input:
        fa=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.genus, wildcards.org, wildcards.fasta),
        md5=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.genus, wildcards.org, wildcards.fasta + '.md5_validated')
    params:
        # Fetch the database metadata object from the JSON file.
        db_info=lambda wildcards: agr_sm.get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod),
        # Strip Taxon DB prefix.
        taxid=lambda wildcards: agr_sm.get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod).taxon_id.replace('NCBITaxon:',''),
        # Strip the '.gz.done' from the output name
        # TODO - This will fail with certain variations of filename extensions.
        out=lambda wildcards, output: Path(output[0]).with_suffix('').with_suffix('')
    log: "logs/makeblastdb_{mod}_{genus}_{org}_{fasta}.log"
    shell:
        # Create the BLAST DB directory and then pipe the FASTA file into makeblastdb.
        """
        dirname {output} | xargs mkdir -p
        gunzip -c {input.fa} | {MAKEBLASTDB_BIN} -in - -dbtype {params.db_info.seqtype} \
            -title "{params.db_info.blast_title}" -parse_seqids -out {params.out} \
            -taxid {params.taxid} -logfile {log} 2>&1
        """

#============================================================================
# Validates that the downloaded file has the same MD5 checksum as the
# database metadata. If it does not, an
#============================================================================
rule validate_fasta_md5:
    output: touch(Path(FASTA_DIR, "{mod}", "{genus}", "{org}", "{fasta}.md5_validated"))
    input: lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.genus, wildcards.org, wildcards.fasta)
    params:
        db_info=lambda wildcards: agr_sm.get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod),
    run:
        is_valid = agr_sm.file_md5_is_valid(fasta_file=Path(input[0]), checksum=params.db_info.md5sum)
        if not is_valid:
            raise ValueError(f'The MD5 checksum for {input} did not validate')


#==============================================================================
# Retrieves the FASTA file from the remote source defined in the metadata file.
#==============================================================================
rule retrieve_fasta:
    output: Path(FASTA_DIR, "{mod}", "{genus}", "{org}", "{fasta}")
    params:
        dir_prefix=lambda wildcards: Path(FASTA_DIR, wildcards.mod, wildcards.genus, wildcards.org),
        db_info=lambda wildcards: agr_sm.get_blastdb_obj(meta_dir=META_DIR, fasta=wildcards.fasta, mod=wildcards.mod)
    log: "logs/wget_{mod}_{genus}_{org}_{fasta}.log"
    run:
        shell("wget -c --tries 3 --timestamping {params.db_info.URI} --directory-prefix {params.dir_prefix} -o {log}")



#==============================================================================
# Generates the BLAST database metadata schema file.
#==============================================================================
rule generate_metatadata_schema:
    output: "conf/metadata_schema.json"
    run:
        with Path(output[0]).open('w', encoding="utf-8") as f:
            f.write(agr_sm.AGRBlastDatabases.schema_json())
