from functools import cache
from Bio import Entrez


@cache
def get_taxonomy_id(genus: str, species: str) -> int | None:
    """
    Get NCBI taxonomy ID for a given genus and species.
    :param genus: Genus name.
    :param species: Species name.
    :return: NCBI taxonomy ID.
    """
    try:
        handle = Entrez.esearch(db="taxonomy", term=f"{genus} {species}[SCIN]")
        record = Entrez.read(handle)
        num_results = int(record["Count"])
        if num_results == 1:
            return int(record["IdList"][0])
        elif num_results > 1:
            raise ValueError(f"{num_results} results found for {genus} {species}")
    except IOError as ioe:
        print(ioe)
    finally:
        handle.close()
    return None
