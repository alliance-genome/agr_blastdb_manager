"""
Tests for the gene-name index each BLAST database carries.

SequenceServer resolves `?name=<gene symbol>` against these, so what the index
contains decides whether a curator typing "Dll" gets a sequence or nothing.
Until the per-MOD grammars were added it understood only NCBI's bracket tags,
which is why the lookup worked on SGD and silently failed everywhere else.

The point of these tests is not that each pattern matches its own MOD -- that is
easy -- but that none of them claims another MOD's text. All four are tried
against every defline, because the indexer does not know which MOD produced the
file it is reading.
"""

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from utils import index_entries  # noqa: E402


def index(accession, defline):
    return index_entries([(accession, defline)])


# One real defline per MOD, taken from the deployed databases.
WB_PROTEIN = "wormpep=CE32785 gene=WBGene00007064 locus=rga-9 status=Confirmed"
FB_PROTEIN = "FBpp0070468 type=polypeptide; name=w-PA; parent=FBgn0003996,FBtr0070491;"
FB_TRANSCRIPT = "FBtr0070490 type=mRNA; loc=X:complement(join(1..2)); name=w-RA; parent=FBgn0003996;"
ZFIN_TRANSCRIPT = "itsn1|OTTDARP00000003617 BUSM1-173A8.1-002 zebrafish"
SGD_MAIN = "YFL039C ACT1 SGDID:S000001855, Chr VI from 54377-53260, reverse complement"
SGD_FUNGAL = "[gene=ACT1] [locus_tag=YFL039C] [db_xref=SGD:S000001855,GeneID:850504]"


def test_accession_is_always_indexed():
    """A lookup by accession must work even where no symbol can be derived."""
    assert index("FBpp1", "FBpp1 type=polypeptide;")["fbpp1"] == "FBpp1"


@pytest.mark.parametrize(
    "label,accession,defline,symbol",
    [
        ("WormBase protein", "CE32785", WB_PROTEIN, "rga-9"),
        ("FlyBase protein", "FBpp0070468", FB_PROTEIN, "w"),
        ("FlyBase transcript", "FBtr0070490", FB_TRANSCRIPT, "w"),
        ("ZFIN transcript", "OTTDART1", ZFIN_TRANSCRIPT, "itsn1"),
        ("SGD main", "YFL039C", SGD_MAIN, "act1"),
        ("SGD fungal", "NC_001138.5_cds_NP_1", SGD_FUNGAL, "act1"),
    ],
)
def test_each_mod_symbol_is_indexed(label, accession, defline, symbol):
    assert index(accession, defline)[symbol] == accession, label


def test_symbols_are_lowercased_so_lookup_is_case_insensitive():
    """?name=act1 and ?name=ACT1 must reach the same record."""
    assert "act1" in index("YFL039C", SGD_MAIN)


# --- the part that actually matters: no grammar claims another MOD's text ----


def test_wormbase_indexes_the_locus_not_the_gene_identifier():
    """
    WormBase puts an identifier in gene= and the symbol in locus=. Indexing
    gene= would fill the index with WBGene ids nobody searches for.
    """
    keys = index("CE32785", WB_PROTEIN)
    assert "rga-9" in keys
    assert "wbgene00007064" not in keys


def test_zfin_pattern_leaves_clone_names_alone():
    """
    ZFIN's symbol leads the defline, but so do clone names in other datasets.
    The pattern is anchored on a lowercase first letter to tell them apart;
    an uppercase lead must yield the accession only.
    """
    keys = index("X", "CH211-107M8.1-002|OTTDARP0001 something")
    assert "ch211-107m8.1-002" not in keys
    assert sorted(keys) == ["x"]


def test_flybase_pattern_needs_the_isoform_suffix():
    """
    name= is the isoform (w-PA), and the symbol is the part before the -PA. A
    name= without that suffix is not an isoform and must not be indexed as one.
    """
    assert "w" not in index("FBpp1", "FBpp1 type=polypeptide; name=w;")


def test_flybase_defline_without_a_name_tag_yields_only_the_accession():
    assert sorted(index("FBpp1", "FBpp1 type=polypeptide; loc=X:join(1..2);")) == ["fbpp1"]


def test_a_genome_assembly_defline_yields_no_symbol():
    """
    RGD and ZFIN ship deflines that name no gene at all -- a chromosome
    description, a GenBank clone id. These must index the accession and nothing
    else, rather than a grammar inventing a symbol out of prose.
    """
    rgd = index(
        "NC_086019.1",
        "NC_086019.1 Rattus norvegicus strain BN/NHsdMcwi chromosome 1, GRCr8, whole genome shotgun sequence",
    )
    assert sorted(rgd) == ["nc_086019.1"]

    zfin = index("BL_ORD_ID:0", "gb|AA605703.1|AA605703 fa17f11.s1 Ekker early gastrulation zebrafish embryo")
    assert "aa605703.1" not in zfin


def test_first_record_wins_for_a_repeated_symbol():
    """
    A symbol can occur in several records; the index maps it to one accession.
    setdefault means the first wins, which keeps a rebuild deterministic for a
    given input order.
    """
    entries = [
        ("FBpp0000001", "FBpp0000001 type=polypeptide; name=w-PA; parent=FBgn1;"),
        ("FBpp0000002", "FBpp0000002 type=polypeptide; name=w-PB; parent=FBgn1;"),
    ]
    assert index_entries(entries)["w"] == "FBpp0000001"


def test_empty_accession_is_skipped():
    assert index_entries([("", WB_PROTEIN)]) == {}
