from subprocess import Popen, PIPE
import yaml

import agr_blastdb_manager.agr.snakemake as agr_sm
from agr_blastdb_manager.agr.utils import get_blast_files
from agr_blastdb_manager.agr.utils import copy_config_files_to_data_dir
from agr_blastdb_manager.agr.utils import add_md5_config_files

from pathlib import Path

configfile= "/conf/global.yaml"
with open(configfile, "r") as file:
    config=yaml.safe_load(file)

BLASTDB_DIR = config.get("BLASTDB_DIR", Path("data","blast"))

print("starting processing")
#process = Popen(["snakemake", "--config", "MAKEBLASTDB_BIN=/blast/bin/makeblastdb", "--cores", "all"],
process = Popen("snakemake --cores all MAKEBLASTDB_BIN=/blast/bin/makeblastdb", shell=True, stdout=PIPE, stderr=PIPE)
process.wait()
stdout, stderr = process.communicate()
print("stdout")
print(stdout)
print("stderr")
print(stderr)
print("finished processing")
copy_config_files_to_data_dir(config, BLASTDB_DIR)
#add_md5_config_files(config)
