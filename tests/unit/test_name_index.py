"""
Tests for the gene-name index written alongside each BLAST database.

The index lets SequenceServer resolve ?name=YFL039C deep links with a single
file read instead of scanning deflines across every database.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utils import (  # noqa: E402
    build_name_index,
    flybase_aliases,
    index_entries,
    sgd_symbol,
)

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


# --- gene aliases ------------------------------------------------------------
#
# What these cover is a reported bug, not a hypothetical. A curator searched
# FlyBase for "white" and was told no such gene existed, because FlyBase
# deflines carry "name=w-RA" and the string "white" appears nowhere in any of
# their databases. The symbol is all the defline has; the name has to be joined
# in from FlyBase's own synonym table.

# A real FlyBase polypeptide defline, trimmed. parent= is the join key.
FB_STYLE = (
    ">FBpp0070468 type=polypeptide; loc=X:complement(2790575..2796621); "
    "name=w-PA; parent=FBgn0003996,FBtr0070479; MD5=abc; length=687;"
)

# Two rows of fb_synonym_fb_2026_03.tsv, as published: id, organism, symbol,
# fullname, fullname synonyms, symbol synonyms. The last two are pipe-separated.
FB_SYNONYM_ROWS = (
    "##primary_FBid\torganism_abbreviation\tcurrent_symbol\tcurrent_fullname\t"
    "fullname_synonym(s)\tsymbol_synonym(s)\n"
    "FBgn0003996\tDmel\tw\twhite\tWhite|mini-white\tCG2759|DMWHITE|mw\n"
    "FBgn0000490\tDmel\tDl\tDelta\t\tCG3619\n"
)


def _synonym_file(tmp_path, gzipped=False):
    if not gzipped:
        path = tmp_path / "syn.tsv"
        path.write_text(FB_SYNONYM_ROWS)
        return path
    import gzip

    path = tmp_path / "syn.tsv.gz"
    with gzip.open(path, "wt") as fh:
        fh.write(FB_SYNONYM_ROWS)
    return path


def test_flybase_aliases_reads_every_name_column(tmp_path):
    aliases = flybase_aliases(_synonym_file(tmp_path))
    assert set(aliases["FBgn0003996"]) == {
        "w", "white", "White", "mini-white", "CG2759", "DMWHITE", "mw",
    }
    # An empty synonym column must not contribute an empty name.
    assert set(aliases["FBgn0000490"]) == {"Dl", "Delta", "CG3619"}
    assert "" not in aliases["FBgn0000490"]


def test_flybase_aliases_reads_the_file_as_published(tmp_path):
    """It is published gzipped; both forms have to work."""
    assert flybase_aliases(_synonym_file(tmp_path, gzipped=True)) == flybase_aliases(
        _synonym_file(tmp_path)
    )


def test_the_full_gene_name_becomes_searchable():
    """The reported bug: "white" found nothing, because only "w" is indexed."""
    entries = [("FBpp0070468", FB_STYLE)]

    without = index_entries(entries)
    assert without["w"] == "FBpp0070468"       # the symbol was always there
    assert "white" not in without              # ...and the name never was

    with_aliases = index_entries(entries, {"FBgn0003996": ["w", "white", "mini-white"]})
    assert with_aliases["white"] == "FBpp0070468"
    assert with_aliases["mini-white"] == "FBpp0070468"
    assert with_aliases["w"] == "FBpp0070468"


def test_a_name_cannot_reach_another_genes_records():
    """The join is by gene id, so an alias table covering the whole of FlyBase
    is safe to pass to every database: only the parent gene's names apply."""
    index = index_entries(
        [("FBpp0070468", FB_STYLE)],
        {"FBgn0000490": ["Delta"], "FBgn0003996": ["white"]},
    )
    assert index["white"] == "FBpp0070468"
    assert "delta" not in index


def test_a_defline_with_no_parent_is_left_alone():
    """SGD and WormBase deflines have no parent=; passing aliases must be a
    no-op for them rather than an error."""
    assert index_entries([("YFL039C", SGD_STYLE)], {"FBgn0003996": ["white"]}) == (
        index_entries([("YFL039C", SGD_STYLE)])
    )


def test_build_name_index_carries_aliases_through(tmp_path):
    """The gap this closes: build_name_index is what the pipeline calls, so a
    rebuild that did not pass aliases would silently drop every full name."""
    fasta = tmp_path / "in.fa"
    fasta.write_text(f"{FB_STYLE}\nMGSTKA\n")

    build_name_index(
        str(fasta), str(tmp_path / "somedb"), aliases={"FBgn0003996": ["white"]}
    )
    index = json.loads((tmp_path / "somedb.names.json").read_text())
    assert index["white"] == "FBpp0070468"


def test_gene_aliases_derives_the_published_filename(monkeypatch, tmp_path):
    """FB2026_03 -> fb_synonym_fb_2026_03.tsv.gz, which is the file actually
    published under releases/current/precomputed_files/synonyms/. Getting this
    spelling wrong is a silent miss: the build warns and carries on with
    symbols only."""
    import utils

    utils._GENE_ALIAS_CACHE.clear()
    monkeypatch.chdir(tmp_path)
    Path("../data").mkdir(parents=True, exist_ok=True)

    asked = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            import gzip

            return gzip.compress(FB_SYNONYM_ROWS.encode())

    def fake_urlopen(url, timeout=None):
        asked.append(url)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    aliases = utils.gene_aliases("FB", "FB2026_03")
    assert asked == [
        (
            "https://s3ftp.flybase.org/releases/current/precomputed_files/"
            "synonyms/fb_synonym_fb_2026_03.tsv.gz"
        )
    ]
    assert "white" in aliases["FBgn0003996"]

    # Parsed once per run: FlyBase's table is a million rows and a FlyBase
    # build writes 1,560 indexes.
    utils.gene_aliases("FB", "FB2026_03")
    assert len(asked) == 1


def test_gene_aliases_is_empty_for_a_mod_with_no_published_table():
    """ZFIN and RGD publish nothing of the kind, and must not be reached for."""
    import utils

    utils._GENE_ALIAS_CACHE.clear()
    assert utils.gene_aliases("ZFIN", "ZFIN2026_01") == {}


def test_gene_aliases_reuses_an_already_downloaded_table(monkeypatch, tmp_path):
    """It caches to ../data beside the FASTAs, the same place the pipeline puts
    everything else it downloads, so a re-run does not re-fetch it."""
    import utils

    utils._GENE_ALIAS_CACHE.clear()
    run_dir = tmp_path / "src"
    run_dir.mkdir()
    (tmp_path / "data").mkdir()
    import gzip

    with gzip.open(tmp_path / "data" / "fb_synonym_fb_2026_03.tsv.gz", "wt") as fh:
        fh.write(FB_SYNONYM_ROWS)
    monkeypatch.chdir(run_dir)

    def boom(url, timeout=None):
        raise AssertionError(f"re-downloaded {url} despite a cached copy")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert "white" in utils.gene_aliases("FB", "FB2026_03")["FBgn0003996"]


def test_gene_aliases_survives_the_download_failing(monkeypatch, tmp_path):
    """A search convenience must never fail a build."""
    import utils

    utils._GENE_ALIAS_CACHE.clear()
    run_dir = tmp_path / "src"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    def boom(url, timeout=None):
        raise OSError("no route to host")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert utils.gene_aliases("FB", "FB2026_03") == {}


def test_gene_aliases_warns_on_an_unparseable_release(monkeypatch, tmp_path):
    """An environment name it cannot turn into a filename must warn rather than
    guess a URL: the symptom of a silent miss is a search box that has quietly
    lost every full gene name."""
    import utils

    utils._GENE_ALIAS_CACHE.clear()
    monkeypatch.chdir(tmp_path)

    warnings = []

    class Logger:
        def warning(self, message):
            warnings.append(message)

        def info(self, message):
            pass

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=None: (_ for _ in ()).throw(
            AssertionError(f"asked for {url}")
        ),
    )
    assert utils.gene_aliases("FB", "latest", Logger()) == {}
    assert any("latest" in w for w in warnings)


# --- display spellings -------------------------------------------------------
#
# Index keys are lower-cased so a lookup can be case-insensitive. That is right
# for lookups and wrong for display: the search box listed FlyBase's Dll as
# "dll" and CG2759 as "cg2759". The spellings are collected alongside, into a
# companion file, so the index itself keeps both its shape and its size -- it
# is read in full on every gene search, 928 MB of it on FlyBase.


def test_display_records_the_spelling_that_was_indexed():
    display = {}
    index = index_entries([("FBpp0070468", FB_STYLE)], None, display)

    # The lookup key is unchanged...
    assert index["w"] == "FBpp0070468"
    # ...and the accession's own capitalisation is recoverable.
    assert display["fbpp0070468"] == "FBpp0070468"


def test_display_omits_names_that_are_already_lower_case():
    """It only has to carry the difference. "w" is spelt "w"."""
    display = {}
    index_entries([("FBpp0070468", FB_STYLE)], None, display)
    assert "w" not in display


def test_display_covers_aliases_too(tmp_path):
    """The aliases are where most of the capitalisation is: CG numbers and
    capitalised full names came in with FlyBase's synonym table."""
    display = {}
    index_entries(
        [("FBpp0070468", FB_STYLE)],
        flybase_aliases(_synonym_file(tmp_path)),
        display,
    )
    assert display["cg2759"] == "CG2759"
    assert display["dmwhite"] == "DMWHITE"

    # FlyBase lists this gene's name as "white" and also carries "White" as a
    # synonym. The spelling kept is the one that reached the index first, which
    # is the current name -- so there is no entry at all, the key being the
    # spelling. The box therefore shows "white", not "White".
    assert "white" not in display


def test_display_agrees_with_the_name_that_won():
    """First name wins in the index, so the spelling kept must be that one --
    not whichever came last."""
    first = ">A1 type=polypeptide; name=Abc-PA; parent=FBgn1;"
    second = ">A2 type=polypeptide; name=ABC-PA; parent=FBgn2;"
    display = {}
    index = index_entries([("A1", first), ("A2", second)], None, display)

    assert index["abc"] == "A1"
    assert display["abc"] == "Abc"


def test_display_is_optional_and_changes_nothing():
    """Passing no dict has to leave the index byte-identical, so that a caller
    that does not want spellings pays nothing."""
    assert index_entries([("FBpp0070468", FB_STYLE)]) == index_entries(
        [("FBpp0070468", FB_STYLE)], None, {}
    )


def test_build_writes_the_companion_file(tmp_path):
    fasta = tmp_path / "in.fa"
    fasta.write_text(f"{FB_STYLE}\nMGSTKA\n")

    build_name_index(str(fasta), str(tmp_path / "somedb"))

    written = tmp_path / "somedb.names.display.json"
    assert written.exists()
    assert json.loads(written.read_text())["fbpp0070468"] == "FBpp0070468"


def test_build_writes_no_companion_file_when_every_name_is_lower_case(tmp_path):
    """No file means "the key is the spelling", which is true and costs a read
    rather than a parse."""
    fasta = tmp_path / "in.fa"
    fasta.write_text(">yfl039c act1 SGDID:S000001855, Chr VI\nATGTCT\n")

    build_name_index(str(fasta), str(tmp_path / "somedb"))
    assert not (tmp_path / "somedb.names.display.json").exists()


def test_a_rebuild_removes_a_stale_companion_file(tmp_path):
    """Otherwise it would go on labelling names the new index no longer holds."""
    stale = tmp_path / "somedb.names.display.json"
    stale.write_text('{"gone":"GONE"}')

    fasta = tmp_path / "in.fa"
    fasta.write_text(">yfl039c act1 SGDID:S000001855, Chr VI\nATGTCT\n")
    build_name_index(str(fasta), str(tmp_path / "somedb"))

    assert not stale.exists()
