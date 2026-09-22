"""
Tests for the gene-name index written alongside each BLAST database.

The index lets SequenceServer resolve ?name=YFL039C deep links with a single
file read instead of scanning deflines across every database.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utils import build_name_index, index_entries, sgd_symbol  # noqa: E402

# Real deflines from the two SGD datasets, which name sequences differently.
NCBI_STYLE = (
    ">NC_001138.5_cds_NP_116614.1_1760 [gene=ACT1] [locus_tag=YFL039C] "
    "[protein=actin] [protein_id=NP_116614.1]"
)
SGD_STYLE = ">YFL039C ACT1 SGDID:S000001855, Chr VI from 54377-53260"
SGD_STYLE_NO_SYMBOL = ">YAL069W YAL069W SGDID:S000002143, Chr I from 335-649"


def test_indexes_gene_and_locus_tags():
    index = index_entries([("NC_001138.5_cds_NP_116614.1_1760", NCBI_STYLE)])
    assert index["act1"] == "NC_001138.5_cds_NP_116614.1_1760"
    assert index["yfl039c"] == "NC_001138.5_cds_NP_116614.1_1760"


def test_indexes_the_accession_itself():
    """SGD's main set has no tags: the systematic name IS the accession."""
    index = index_entries([("YFL039C", SGD_STYLE)])
    assert index["yfl039c"] == "YFL039C"


def test_indexes_sgd_gene_symbol():
    """SGD deflines carry the symbol before SGDID:, with no [gene=] tag."""
    index = index_entries([("YFL039C", SGD_STYLE)])
    assert index["act1"] == "YFL039C"


def test_names_are_lowercased_for_case_insensitive_lookup():
    index = index_entries([("YFL039C", SGD_STYLE)])
    assert set(index) == {"yfl039c", "act1"}


def test_first_defline_wins_on_duplicate_names():
    index = index_entries([("FIRST", ">FIRST DUP SGDID:S1"), ("SECOND", ">SECOND DUP SGDID:S2")])
    assert index["dup"] == "FIRST"


def test_sgd_symbol_requires_the_sgdid_marker():
    """Other MODs' deflines must not be mined for a symbol."""
    assert sgd_symbol(SGD_STYLE) == "ACT1"
    assert sgd_symbol(SGD_STYLE_NO_SYMBOL) == "YAL069W"
    assert sgd_symbol(NCBI_STYLE) is None
    assert sgd_symbol(">FBgn0000008 type=gene; loc=2R:complement(22136968..22172834);") is None
    assert sgd_symbol(">II length=15279345") is None


def test_build_writes_index_next_to_the_database(tmp_path):
    fasta = tmp_path / "in.fa"
    fasta.write_text(f"{NCBI_STYLE}\nATGGATTCT\n{SGD_STYLE}\nATGTCT\n")

    count = build_name_index(str(fasta), str(tmp_path / "somedb"))

    written = tmp_path / "somedb.names.json"
    assert written.exists()
    index = json.loads(written.read_text())
    assert count == len(index)
    assert index["yfl039c"] == "NC_001138.5_cds_NP_116614.1_1760"


def test_build_writes_an_empty_index_when_there_are_no_names(tmp_path):
    """An empty index means 'no names here', which is not the same as no index:
    it lets the server skip the database instead of falling back to a scan."""
    fasta = tmp_path / "empty.fa"
    fasta.write_text("ATGGATTCT\n")

    assert build_name_index(str(fasta), str(tmp_path / "somedb")) == 0
    assert json.loads((tmp_path / "somedb.names.json").read_text()) == {}


def test_build_survives_a_missing_fasta(tmp_path):
    assert build_name_index(str(tmp_path / "nope.fa"), str(tmp_path / "somedb")) == 0
    assert not (tmp_path / "somedb.names.json").exists()
