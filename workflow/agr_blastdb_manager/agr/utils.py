import hashlib
from pathlib import Path

import agr_blastdb_manager.agr.snakemake as agr_sm


def get_md5sum_hash(file_path):
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)

    return file_hash.hexdigest()


def get_blast_files(config, meta_dir, blastdb_dir):
    # Build the list of BLAST indices that we are expecting from the pipeline.
    # This is used as the starting point for our pipeline. Snakemake uses this to
    # build a list of dependent rules (DAG) that need to be executed to produce them.
    blast_files = []
    print("Get blast files")
    print(config)
    # Loop over each MOD defined in conf/global.yaml.
    for data_provider in config["data_providers"]:
        data_provider_name = data_provider["name"]
        for environment in data_provider["environments"]:
            filename = "databases." + data_provider_name + "." + environment + ".json"
            config_path = Path("/conf", data_provider_name, filename)
            config_md5_path = Path("/conf", data_provider_name, filename + ".md5")
            if not config_path.exists():
                print("config does not exist: " + config_path)
                print("Will not process")

            if config_md5_path.exists():
                with open(config_md5_path) as f:
                    md5contents = f.readline().strip()
                config_md5sum = get_md5sum_hash(config_path)
                if config_md5sum == md5contents:
                    print("skipping:" + config_path)
                    continue

            blast_files.append(
                # Using the list of metadata files, returns a list of expected BLAST database files.
                agr_sm.expected_blast_files(
                    # Reads the MOD metadata file and writes the individual database metadata
                    # to its own file that is used throughout the pipeline.
                    # Returns a list of files written.
                    db_files=agr_sm.write_db_metadata_files(
                            data_provider=data_provider_name,
                            environment=environment,
                            json_file=config_path,
                            db_meta_dir=meta_dir
                        ),
                    data_provider=data_provider_name,
                    environment=environment,
                    base_dir=blastdb_dir
                )
            )

    return blast_files
