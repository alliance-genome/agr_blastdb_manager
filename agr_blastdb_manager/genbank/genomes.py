import logging
import re
import subprocess
from ftplib import FTP
from os.path import dirname, join

logger = logging.getLogger(__name__)
FTP_HOST = "ftp.ncbi.nlm.nih.gov"
PROJECT_DIR = dirname(__file__)
DEFAULT_OUTPUT_DIR = join(PROJECT_DIR, 'data')


def get_assembly_dir(path: str) -> str | None:
    directories = []
    with FTP(FTP_HOST) as ftp:
        ftp.login()
        files = ftp.mlsd(path)
        for filename, facts in files:
            if re.match(r"^GC[AF]_", filename.strip()):
                logger.debug(f"Found {filename}")
                directories.append(filename)
    num_dirs = len(directories)
    if num_dirs > 1:
        logger.warning(
            f"Found multiple genome assemblies in the 'latest' directory, using the first one: {directories}")
    elif num_dirs == 1:
        logger.debug(f"Returning genome assembly dir {directories[0]}")
        return directories[0]
    else:
        logger.error("Could not find any genome assembly directories.")
        return None


# Fetch Genome files
def fetch_genome_files(genus: str, species: str, organism_group: str = 'invertebrate',
                       output_dir: str = DEFAULT_OUTPUT_DIR, force: bool = False) -> None:
    genome_ftp_dir = f'genomes/refseq/{organism_group}/{genus}_{species}/latest_assembly_versions'
    assembly_dir = get_assembly_dir(genome_ftp_dir)

    try:
        wget_url = f'ftp://{FTP_HOST}/{genome_ftp_dir}/{assembly_dir}/GC[AF]_*.f[na]a.gz'
        logger.debug(f"URL for wget: {wget_url}")
        cmd = [
            'wget',
            '--no-directories',
            '--no-host-directories',
            '--passive-ftp',
            '--continue',
            '--directory-prefix',
            output_dir,
            wget_url
        ]
        if not force:
            cmd.insert(1, '--timestamping')

        proc_complete: subprocess.CompletedProcess = subprocess.run(cmd, capture_output=True)
        if proc_complete.returncode != 0:
            logger.error(proc_complete.args)
            raise ConnectionError(proc_complete.stderr)
    except ConnectionError as ce:
        logger.error(f'Error downloading genome assembly. {ce}')
