"""
The pipeline used to delete things it did not exclusively own.

Two places, both from the October audit, both able to destroy a database that
was serving fine:

  * copy_to_production rmtree'd the whole live databases directory for a
    MOD/release and copied the staging tree back. The staging tree holds only
    what the current run built, so a narrow or mostly-failed run removed every
    other database of that release.

  * run_makeblastdb rmtree'd its output directory on failure. The directory is
    derived from genus/species/blast_title, and two entries sharing a
    blast_title share it -- so one entry's failure deleted another's finished
    database.

Both tests below are about what SURVIVES, which is the part that was wrong.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import create_blast_db as cbd  # noqa: E402
from utils import copy_to_production  # noqa: E402


class Logger:
    def __init__(self):
        self.messages = []

    def info(self, m):
        self.messages.append(("info", m))

    def warning(self, m):
        self.messages.append(("warning", m))

    def error(self, m):
        self.messages.append(("error", m))


def make_db(directory, stem, extra=("nin", "nhr", "nsq")):
    directory.mkdir(parents=True, exist_ok=True)
    for ext in extra:
        (directory / f"{stem}.{ext}").write_text(f"{stem}.{ext}")


# --- run_makeblastdb's failure cleanup ---------------------------------------


def test_a_failure_leaves_a_sibling_database_alone(tmp_path):
    """The reported shape: two config entries share one output directory, and
    the second one's failure must not take the first one's database."""
    out = tmp_path / "ZFIN_TALEN_Sequences"
    make_db(out, "talendb")
    make_db(out, "zfin_mrphdb")

    cbd.remove_partial_database(str(out), "zfin_mrphdb", Logger())

    survivors = sorted(p.name for p in out.iterdir())
    assert survivors == ["talendb.nhr", "talendb.nin", "talendb.nsq"]
    assert out.exists()


def test_a_failed_rebuild_does_not_destroy_the_previous_build(tmp_path):
    """Even with no sibling: rmtree'ing the directory turned a transient
    failure into no database at all, where leaving the old one serving is
    strictly better. Only the partial files of THIS stem go."""
    out = tmp_path / "D_melanogaster_Transcripts_6_69"
    make_db(out, "dmel-transcriptdb")
    (out / "dmel-transcriptdb.names.json").write_text("{}")
    before = sorted(p.name for p in out.iterdir())

    # A rebuild writing the same stem fails. Its own partials go; but this is
    # the same stem, so the directory legitimately empties.
    cbd.remove_partial_database(str(out), "dmel-transcriptdb", Logger())
    assert not out.exists(), "a directory holding only this stem is cleaned up"

    # Whereas a DIFFERENT stem failing leaves the serving database intact.
    make_db(out, "dmel-transcriptdb")
    (out / "dmel-transcriptdb.names.json").write_text("{}")
    cbd.remove_partial_database(str(out), "some-other-db", Logger())
    assert sorted(p.name for p in out.iterdir()) == before


def test_cleanup_is_quiet_when_there_is_nothing_there(tmp_path):
    cbd.remove_partial_database(str(tmp_path / "never-made"), "db", Logger())  # no raise


# --- copy_to_production ------------------------------------------------------


def install(tmp_path, monkeypatch, live_dbs, staged_dbs):
    """Drive the real copy_to_production against a redirected deploy root."""
    import utils

    staging = tmp_path / "staging" / "databases"
    root = tmp_path / "prod"
    monkeypatch.setattr(utils, "BLAST_DEPLOY_ROOT", root)
    live = root / "FB" / "FB2026_03" / "databases"

    for name, stem in live_dbs:
        make_db(live / name, stem)
    for name, stem in staged_dbs:
        make_db(staging / name, stem)

    ok = copy_to_production(str(staging), "FB", "FB2026_03", Logger())
    return ok, live


def test_installing_one_database_keeps_the_others(tmp_path, monkeypatch):
    """The whole defect in miniature. Production serves three; this run built a
    fourth. All four must be there afterwards -- it used to be only the one."""
    ok, live = install(
        tmp_path, monkeypatch,
        live_dbs=[("Genome_Assembly", "assemblydb"),
                  ("Proteins", "translationdb"),
                  ("Transposons", "transposondb")],
        staged_dbs=[("Transcripts", "transcriptdb")],
    )
    assert ok
    assert sorted(p.name for p in live.iterdir()) == [
        "Genome_Assembly", "Proteins", "Transcripts", "Transposons",
    ]
    # and the untouched ones still have their files
    assert (live / "Proteins" / "translationdb.nin").exists()


def test_rebuilding_one_database_does_not_disturb_its_sibling(tmp_path, monkeypatch):
    """The replace case, as opposed to the add case above: the database being
    rebuilt already exists in production, and the one beside it still must
    not be touched."""
    ok, live = install(
        tmp_path, monkeypatch,
        live_dbs=[("Transcripts", "transcriptdb"), ("Proteins", "translationdb")],
        staged_dbs=[("Transcripts", "transcriptdb")],
    )
    assert ok
    assert sorted(p.name for p in live.iterdir()) == ["Proteins", "Transcripts"]
    assert (live / "Proteins" / "translationdb.nin").read_text() == "translationdb.nin"


def test_a_stale_file_inside_a_replaced_database_is_cleared(tmp_path, monkeypatch):
    import utils

    staging = tmp_path / "staging" / "databases"
    root = tmp_path / "prod"
    monkeypatch.setattr(utils, "BLAST_DEPLOY_ROOT", root)
    live = root / "FB" / "FB2026_03" / "databases"

    make_db(live / "Transcripts", "transcriptdb")
    (live / "Transcripts" / "leftover.nin").write_text("from an older build")
    make_db(staging / "Transcripts", "transcriptdb")

    assert copy_to_production(str(staging), "FB", "FB2026_03", Logger())
    assert not (live / "Transcripts" / "leftover.nin").exists()


def test_a_missing_staging_tree_is_refused(tmp_path, monkeypatch):
    import utils

    monkeypatch.setattr(utils, "BLAST_DEPLOY_ROOT", tmp_path / "prod")
    assert copy_to_production(str(tmp_path / "nope"), "FB", "FB2026_03", Logger()) is False


# --- run_makeblastdb end to end ----------------------------------------------
#
# The two tests above call remove_partial_database directly. This one drives
# the real run_makeblastdb through a genuine makeblastdb failure, which is the
# path that used to rmtree the output directory. An earlier attempt to show
# this through the CLI proved nothing: the download failed first, so neither
# cleanup ever ran.


@pytest.mark.skipif(
    not __import__("shutil").which("makeblastdb"), reason="makeblastdb not on PATH"
)
def test_a_real_makeblastdb_failure_spares_the_sibling(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("../data").mkdir(parents=True, exist_ok=True)
    Path("../logs").mkdir(parents=True, exist_ok=True)

    # Not FASTA, so makeblastdb rejects it after the file is in place.
    Path("../data/garbage.fa").write_text("this is not a FASTA file at all\n")

    out = tmp_path / "Shared_Title"
    make_db(out, "siblingdb")
    before = sorted(p.name for p in out.iterdir())

    entry = {
        "uri": "https://example.invalid/garbage.fa",
        "blast_title": "Shared Title",
        "seqtype": "nucl",
        "taxon_id": "NCBITaxon:7227",
        "genus": "Drosophila",
        "species": "melanogaster",
    }

    ok = cbd.run_makeblastdb(entry, str(out), Logger(), "FB", "FB2026_03")

    assert ok is False, "makeblastdb should have rejected a non-FASTA input"
    assert out.exists(), "the output directory was destroyed"
    assert sorted(p.name for p in out.iterdir()) == before, (
        "the sibling database did not survive a failed build"
    )
