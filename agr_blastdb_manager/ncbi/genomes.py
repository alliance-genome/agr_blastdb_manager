import ftplib
import logging
import re
import urllib.error
import urllib.request as req
from ftplib import FTP
from pathlib import Path
from typing import Iterator, Union

logger = logging.getLogger(__name__)
FTP_HOST = "ftp.ncbi.nlm.nih.gov"
PROJECT_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = Path(PROJECT_DIR, "data")

DEFAULT_ORGANISM_GROUP = "invertebrate"


def get_current_genome_assembly_files(
    genus: str,
    species: str,
    organism_group: str = DEFAULT_ORGANISM_GROUP,
    file_regex: str = None,
) -> Union[tuple[str, str, str], None]:
    """
    Get the current genome assembly directory for a given organism.

    Organism group is one of:
    - 'archaea'
    - 'bacteria'
    - 'fungi'
    - 'invertebrate'
    - 'mitochondria'
    - 'plant'
    - 'plasmid'
    - 'plastid'
    - 'protozoa'
    - 'vertebrate_mammalian'
    - 'vertebrate_other'
    - 'viral'

    :param genus: Genus of organism
    :param species: Species of organism
    :param organism_group: Organism group (default: 'invertebrate', see above)
    :param file_regex: Regular expression to match files (default: None)
    :return: Tuple of (genome assembly directory, genome assembly file, md5 checksum file)
    """
    path = (
        f"/genomes/refseq/{organism_group}/{genus}_{species.replace(' ', '_')}/latest_assembly_versions"
    )
    with FTP(FTP_HOST) as ftp:
        # Use a passive connection to avoid firewall blocking and login.
        ftp.set_pasv(True)
        ftp.login()
        # Get a list of files in the directory.
        try:
            files = ftp.mlsd(path)
            # Look for the latest genome assembly directory.
            directories = filter_ftp_paths(files, "^GC[AF]_")
        except ftplib.error_perm as e:
            logger.error(f"FTP error: {e}")
            return None
        except ftplib.all_errors as e:
            logger.error(f"FTP error while processing {genus} {species}: {e}")
            return None

        if len(directories) >= 1:
            if len(directories) > 1:
                logger.warning(
                    f"Found multiple genome assemblies in the 'latest' directory, using the first one: {', '.join(directories)}"
                )
            assembly_dir = directories[0]
            # Get a list of files in the latest genome assembly directory.
            try:
                assembly_files = ftp.mlsd(f"{path}/{assembly_dir}")
                # Filter files based on the regular expression filter.
                files = filter_ftp_paths(assembly_files, file_regex)
            except ftplib.all_errors as e:
                logger.error(f"FTP error while processing {genus} {species}: {e}")
                return None

            files_with_md5 = []
            # Look for the md5 of the genome assembly file.
            for file in files:
                try:
                    # Fetch the md5 checksum file
                    with req.urlopen(
                        f"ftp://{FTP_HOST}{path}/{assembly_dir}/md5checksums.txt"
                    ) as response:
                        md5_body = response.read()
                    decoded_body = md5_body.decode("utf-8")
                    # Look for the corresponding genome assembly file checksum.
                    for md5_line in decoded_body.splitlines():
                        if file in md5_line:
                            md5 = re.split(r"\s+", md5_line)[0]
                            files_with_md5.append(
                                (
                                    assembly_dir,
                                    f"ftp://{FTP_HOST}{path}/{assembly_dir}/{file}",
                                    md5,
                                )
                            )
                    # Make sure we only found one checksum.
                    if len(files_with_md5) > 1:
                        logger.warning(
                            "Found multiple files with MD5 checksums, using the first one"
                        )
                    elif len(files_with_md5) == 0:
                        logger.warning("Could not find MD5 checksum for file")
                except (urllib.error.URLError, urllib.error.HTTPError) as error:
                    logger.error(f"Failed to get md5 checksum for {file}:\n{error}")
                    continue
            return files_with_md5[0] if len(files_with_md5) >= 1 else None

        else:
            logger.error(f"No genome assembly directory found for {genus} {species}")
            return None


def filter_ftp_paths(files: Iterator, file_regex: str = None) -> list[str]:
    """
    Given an iterator for files from the `mlsd` FTP command, filter the files based on the regular expression.

    :param files: Iterator for the files from the `mlsd` FTP command
    :param file_regex: Regular expression to match files (default: None)
    :return: List of files that match the regular expression
    """
    ftp_paths = []
    pattern = re.compile(file_regex) if file_regex else None
    for filename, facts in files:
        if pattern.search(filename.strip()):
            logger.debug(f"Found {filename}")
            ftp_paths.append(filename)
    return ftp_paths
