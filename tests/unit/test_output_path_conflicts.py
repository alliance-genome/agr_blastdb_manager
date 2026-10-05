"""
Two entries must not build to the same output path.

Nothing checked this. The second makeblastdb simply overwrote the first and
BOTH were reported as successes, so a run claimed databases it had not got.
WS285 does it four times: three C. elegans bioprojects share the blast_title
"C. elegans Genome Assembly", two C. remanei ones do the same, and two more
pairs collide on the protein sets -- nine entries resolving to four paths, so
five databases are lost without a word.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from create_blast_db import (  # noqa: E402
    database_output_dir,
    database_stem,
    find_output_path_conflicts,
)


def entry(title, uri, **kw):
    e = {
        "blast_title": title,
        "uri": uri,
        "genus": "Caenorhabditis",
        "species": "elegans",
        "seqtype": "nucl",
    }
    e.update(kw)
    return e


# --- the stem, which is where the surprise lives -----------------------------


def test_the_stem_is_truncated_at_the_first_dot():
    """Not a property anyone would design, but it is the deployed one: every
    database's files and its .names.json are named from it. Pinned here so a
    future change to it is a deliberate migration rather than an accident."""
    assert database_stem("c_elegans.PRJNA13758.WS298.genomic.fa.gz") == "c_elegansdb"
    assert database_stem("GCF_000002035.6_GRCz11_genomic.fna.gz") == "GCF_000002035db"
    # ...so these two distinct sources produce an identical stem
    assert database_stem("GCF_000002035.6_GRCz11_rna.fna.gz") == "GCF_000002035db"
    # and a name with one suffix behaves as you would expect
    assert database_stem("talen_fasta.fa.gz") == "talen_fastadb"


def test_the_stem_ignores_the_rest_of_the_uri():
    assert database_stem("https://example.org/a/b/talen_fasta.fa.gz") == "talen_fastadb"


# --- the directory -----------------------------------------------------------


def test_each_layout_rule_puts_a_database_somewhere_different():
    base = "../data/blast/WB/WS298/databases"
    assert database_output_dir("WS298", "WB", entry("A B", "x.fa.gz")) == (
        f"{base}/Caenorhabditis/elegans/A_B/"
    )
    assert database_output_dir(
        "WS298", "WB", entry("A B", "x.fa.gz", seqcol="Other")
    ) == f"{base}/Other/A_B/"
    assert database_output_dir(
        "WS298", "WB", entry("A B", "x.fa.gz", seqcol_type="Some Type")
    ) == f"{base}/Some_Type/A_B/"


def test_seqcol_type_wins_over_seqcol():
    """Both present is not a case any config has, but the builder picks
    seqcol_type, and the conflict check has to agree with the builder."""
    out = database_output_dir(
        "WS298", "WB", entry("T", "x.fa.gz", seqcol="Legacy", seqcol_type="New Type")
    )
    assert "New_Type" in out and "Legacy" not in out


# --- the check itself --------------------------------------------------------


def test_a_clean_config_has_no_conflicts():
    entries = [
        entry("C. elegans Genome Assembly", "c_elegans.PRJNA13758.WS298.genomic.fa.gz"),
        entry("C. elegans Protein Sequences", "c_elegans.PRJNA13758.WS298.protein.fa.gz"),
    ]
    assert find_output_path_conflicts(entries, "WB", "WS298") == {}


def test_the_real_ws285_shape_is_caught():
    """Same blast_title, different bioprojects: the stem truncates at the first
    dot, so all three land on one path."""
    entries = [
        entry("C. elegans Genome Assembly", "c_elegans.PRJEB28388.WS285.genomic.fa.gz"),
        entry("C. elegans Genome Assembly", "c_elegans.PRJNA13758.WS285.genomic.fa.gz"),
        entry("C. elegans Genome Assembly", "c_elegans.PRJNA275000.WS285.genomic.fa.gz"),
    ]
    conflicts = find_output_path_conflicts(entries, "WB", "WS285")
    assert len(conflicts) == 1
    (path, colliding), = conflicts.items()
    assert path.endswith("C_elegans_Genome_Assembly/c_elegansdb")
    assert len(colliding) == 3


def test_distinct_titles_do_not_collide_even_with_one_stem():
    """The stem alone is not the problem -- genomic and rna share a stem but
    sit in different directories, which is most of the deployed data."""
    entries = [
        entry("Z Genome", "GCF_000002035.6_GRCz11_genomic.fna.gz"),
        entry("Z RNA", "GCF_000002035.6_GRCz11_rna.fna.gz"),
    ]
    assert find_output_path_conflicts(entries, "ZFIN", "prod") == {}


def test_a_shared_title_with_distinct_stems_does_not_collide():
    """ZFIN's two "ZFIN TALEN Sequences" entries share a DIRECTORY but not a
    path, so they do not overwrite each other. That is a config problem for
    ZFIN rather than something this check can answer, and it must not be
    reported here as one."""
    entries = [
        entry("ZFIN TALEN Sequences", "talen_fasta.fa.gz",
              genus="Danio", species="rerio"),
        entry("ZFIN TALEN Sequences", "zfin_mrph.fa.gz",
              genus="Danio", species="rerio"),
    ]
    assert find_output_path_conflicts(entries, "ZFIN", "prod") == {}


def test_entries_without_a_uri_or_title_are_left_to_their_own_validation():
    entries = [
        entry("Has Everything", "a.fa.gz"),
        {"blast_title": "No URI"},
        {"uri": "b.fa.gz"},
    ]
    assert find_output_path_conflicts(entries, "WB", "WS298") == {}


def test_a_missing_genus_does_not_raise():
    """It would have raised KeyError out of the check and taken the whole run
    with it, before the entry got the chance to fail its own validation with a
    message that says what is actually wrong."""
    entries = [
        {"blast_title": "No Genus", "uri": "a.fa.gz"},
        {"blast_title": "No Genus", "uri": "a.fa.gz"},
    ]
    assert find_output_path_conflicts(entries, "WB", "WS298") == {}


def test_the_check_agrees_with_where_the_build_actually_writes():
    """The point of factoring the derivation out. If these ever disagree the
    check is worthless, which is the same failure the name indexer had when
    two code paths derived a defline differently."""
    e = entry("C. elegans Genome Assembly", "c_elegans.PRJNA13758.WS298.genomic.fa.gz")
    predicted = database_output_dir("WS298", "WB", e) + database_stem(e["uri"])
    assert predicted == (
        "../data/blast/WB/WS298/databases/Caenorhabditis/elegans/"
        "C_elegans_Genome_Assembly/c_elegansdb"
    )
