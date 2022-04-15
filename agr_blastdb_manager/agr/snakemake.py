import sys
from pathlib import Path

from orjson import JSONEncodeError, JSONDecodeError

from agr_blastdb_manager.agr.metadata import AGRBlastDatabases, BlastDBMetaData


def write_db_metadata_files(mod: str, json_file: str, db_meta_dir: Path) -> list[Path]:
    """
    Parses a database metadata file with many databases into individual JSON files
    that are used as targets for snakemake to process.

    Returns a list of JSON file paths produced from the metadata file.

    :param mod:  The model organism database being processed (e.g. wormbase, flybase, etc.)
    :param json_file:  The database metadata file in JSON format.
    :param db_meta_dir:  The directory to place the parsed metadata files.
    :return: List of Path objects for the JSON metadata files produced.
    """
    try:
        # mod_dbs: dict = json.load(f)
        mod_blast_metadata: AGRBlastDatabases = AGRBlastDatabases.parse_file(json_file)
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

    metadata_files: list[Path] = []
    for db in mod_blast_metadata.data:
        try:
            # Set up and create the directory to store the metadata files.
            db_dir = Path(db_meta_dir, mod)
            db_dir.mkdir(parents=True, exist_ok=True)

            # Get the fasta filename from the URI
            db_uri = db.URI
            # Everything after the last '/'
            fasta_file = extract_fasta_file(db_uri)
            # Create metadata Path object with the suffix replaced with '.json'
            metadata_file = Path(db_dir, fasta_file).with_suffix(".json")
            # Write the DB metadata to the JSON file.
            with metadata_file.open(mode="w", encoding="utf-8") as fp:
                fp.write(db.json())
                metadata_files.append(metadata_file)
        except JSONEncodeError as jee:
            print(
                f"Error while encoding JSON file {metadata_file}:\n{jee}",
                file=sys.stderr,
            )

        except IOError as ioe:
            print(f"Error while writing to {metadata_file}: {ioe}")
    return metadata_files


def extract_fasta_file(uri: str) -> str | None:
    """
    Returns all characters after the last slash '/'.

    :param uri:  The URI string to process.
    :return: Returns any characters after the last character or None if no slash is present.
    """
    return uri[uri.rindex("/") + 1 :] if "/" in uri else None


def read_db_json(db_file: Path | str) -> BlastDBMetaData:
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


def expected_blast_files(db_files: list[Path], base_dir: Path, mod: str) -> list[Path]:
    blast_files = []
    for db_file in db_files:
        db_info = read_db_json(db_file)
        fasta = Path(extract_fasta_file(db_info.URI) + ".done")
        blast_files.append(
            Path(base_dir, mod, f"{db_info.genus}_{db_info.species}", fasta)
        )

    return blast_files


def get_blastdb_obj(meta_dir: Path, fasta: str, mod: str) -> BlastDBMetaData:
    return read_db_json(Path(meta_dir, mod, fasta).with_suffix(".json"))
