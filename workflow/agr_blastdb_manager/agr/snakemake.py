import sys
import hashlib
from pathlib import Path

from orjson import JSONEncodeError, JSONDecodeError

from agr_blastdb_manager.agr.metadata import AGRBlastDatabases, BlastDBMetaData


def write_db_metadata_files(data_provider: str, environment: str, json_file: str, db_meta_dir: Path) -> list[Path]:
    """
    Parses a database metadata file with many databases into individual JSON files
    that are used as targets for snakemake to process.

    Returns a list of JSON file paths produced from the metadata file.

    :param data_provider:  The model organism database being processed (e.g. wormbase, flybase, etc.)
    :param json_file:  The database metadata file in JSON format.
    :param db_meta_dir:  The directory to place the parsed metadata files.
    :return: List of Path objects for the JSON metadata files produced.
    """
    try:
        mod_blast_metadata: AGRBlastDatabases = AGRBlastDatabases.parse_file(json_file)
        metadata_files: list[Path] = []
        for db in mod_blast_metadata.data:
            # Set up and create the directory to store the metadata files.
            db_dir = Path(db_meta_dir, data_provider, environment)
            db_dir.mkdir(parents=True, exist_ok=True)

            # Get the fasta filename from the URI
            db_uri = db.uri
            # Everything after the last '/'
            fasta_file = extract_fasta_file(db_uri)
            # Create metadata Path object with the suffix replaced with '.json'
            metadata_file = Path(db_dir, fasta_file).with_suffix(".json")
            # Write the DB metadata to the JSON file.
            with metadata_file.open(mode="w", encoding="utf-8") as fp:
                fp.write(db.json())
                metadata_files.append(metadata_file)

        return metadata_files

    except JSONEncodeError as jee:
        print(
            f"Error while encoding JSON file {metadata_file}:\n{jee}",
            file=sys.stderr,
        )
    except JSONDecodeError as jde:
        print(
            f"Error while decoding AGR BLAST metadata from JSON: {json_file}\n{jde}",
            file=sys.stderr,
        )
    except FileNotFoundError as fnf:
        print(
            f"Couldn't open database metadata file: {json_file}\n{fnf}", file=sys.stderr
        )
    except IOError as io:
        print(
            f"IO Error while reading database metadata file: {json_file}\n{io}",
            file=sys.stderr,
        )


def extract_fasta_file(uri: str) -> str | None:
    """
    Returns all characters after the last slash '/'.

    :param uri:  The URI string to process.
    :return: Returns any characters after the last character or None if no slash is present.
    """
    return uri[uri.rindex("/") + 1 :] if "/" in uri else None


def read_db_json(db_file: Path | str) -> BlastDBMetaData | None:
    """
    Reads the BLAST database metadata file for a single database.

    :param db_file:  Database metadata file.
    :return:  The metadata object or None
    """
    try:
        db_info: BlastDBMetaData = BlastDBMetaData.parse_file(db_file)
        return db_info
    except FileNotFoundError as fnf:
        print(f"Couldn't open the database file: {db_file}\n{fnf}", file=sys.stderr)
    except IOError as io:
        print(
            f"Error while reading the database file: {db_file}\n{io}", file=sys.stderr
        )
    return None


def expected_blast_files(db_files: list[Path], base_dir: Path, data_provider: str, environment: str) -> list[Path]:
    """
    Given a list of BLAST database metadata files, returns a list of '.done' files in the BLAST database
    location that is expected based on the MOD and metadata.

    :param db_files: List of Path objects for the database metadata files.
    :param base_dir: The base BLAST database directory.
    :param data_provider: The model organism database being processed.
    :return: List of paths for the BLAST database '.done' files.
    """
    blast_files = []
    for db_file in db_files:
        db_info = read_db_json(db_file)
        fasta = Path(extract_fasta_file(db_info.uri) + ".done")
        blast_files.append(
            Path(
                base_dir,
                data_provider,
                environment,
                db_info.genus,
                f"{db_info.genus}_{db_info.species}",
                fasta,
            )
        )

    return blast_files


def get_blastdb_obj(meta_dir: Path, fasta: str, data_provider: str, environment: str) -> BlastDBMetaData:
    """
    Constructs the proper path for the BLAST database metadata file, loads the JSON, and
    returns the metadata object.

    :param meta_dir: The metadata directory.
    :param fasta: FASTA file being processed.
    :param data_provider: The model organism database being processed.
    :return: The BLAST database metadata object.
    """
    return read_db_json(Path(meta_dir, data_provider, environment, fasta).with_suffix(".json"))


def file_md5_is_valid(fasta_file: Path, checksum: str) -> bool:
    """
    Checks if the FASTA file matches the MD5 checksum argument.

    Returns True if it matches and False otherwise.

    :param fasta_file: Path object for the FASTA file.
    :param checksum: MD5 checksum string.
    :return: boolean indicating if the file validates.
    """
    md5_hash = hashlib.md5()
    with fasta_file.open(mode="rb") as fh:
        # Read in small chunks to avoid memory overflow with large files.
        while chunk := fh.read(8192):
            md5_hash.update(chunk)
    return md5_hash.hexdigest() == checksum
