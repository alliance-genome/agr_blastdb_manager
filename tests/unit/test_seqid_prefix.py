"""
Sequence ids have to be unique across databases searched together.

When a search spans several BLAST databases that use the same ids, BLAST
reports each id ONCE and drops the rest. The alignments never reach the output
and nothing says so. Four of the nine Alliance reference genomes name their
chromosomes 1..n, so a nine-genome tblastn for human ACTB returned 131 hits
with neither mouse nor rat among them, while mouse alone returns 20 at evalue
0.0. 23 of that deployment's 36 same-type pairs collide.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from create_blast_db import (  # noqa: E402
    SEQID_PREFIX_SEPARATOR,
    VALID_SEQID_PREFIX,
    prefix_fasta_ids,
)


class Logger:
    def __init__(self):
        self.errors = []
        self.infos = []

    def error(self, m):
        self.errors.append(m)

    def info(self, m):
        self.infos.append(m)

    def warning(self, m):
        pass


def fasta(tmp_path, text):
    p = tmp_path / "in.fa"
    p.write_text(text)
    return p


def test_the_id_is_prefixed_and_the_rest_of_the_defline_is_not(tmp_path):
    p = fasta(tmp_path, ">1 Homo sapiens chromosome 1, GRCh38.p14\nACGT\n")

    assert prefix_fasta_ids(str(p), "GRCh38", Logger()) == 1
    assert p.read_text() == ">GRCh38_1 Homo sapiens chromosome 1, GRCh38.p14\nACGT\n"


def test_a_defline_with_no_description_still_works(tmp_path):
    p = fasta(tmp_path, ">1\nACGT\n>MT\nTTTT\n")

    assert prefix_fasta_ids(str(p), "GRCm39", Logger()) == 2
    assert p.read_text() == ">GRCm39_1\nACGT\n>GRCm39_MT\nTTTT\n"


def test_sequence_lines_are_untouched(tmp_path):
    body = "ACGTACGTAC\nGTACGTACGT\n"
    p = fasta(tmp_path, f">1 chr one\n{body}")

    prefix_fasta_ids(str(p), "X", Logger())
    assert body in p.read_text()


def test_it_makes_two_genomes_distinguishable(tmp_path):
    """The point of the whole exercise: human chr1 and mouse chr1 are both
    called "1" and are the same id to BLAST."""
    (tmp_path / "h").mkdir()
    (tmp_path / "m").mkdir()
    h = tmp_path / "h" / "a.fa"
    h.write_text(">1 human\nAAAA\n")
    m = tmp_path / "m" / "a.fa"
    m.write_text(">1 mouse\nTTTT\n")

    prefix_fasta_ids(str(h), "GRCh38", Logger())
    prefix_fasta_ids(str(m), "GRCm39", Logger())

    hid = h.read_text().splitlines()[0].split()[0]
    mid = m.read_text().splitlines()[0].split()[0]
    assert hid != mid
    assert (hid, mid) == (">GRCh38_1", ">GRCm39_1")


def test_running_it_twice_does_not_double_the_prefix(tmp_path):
    """--store-files keeps the downloaded FASTA, so a rebuild can see a file
    that has already been through this. GRCh38_GRCh38_1 would be its own kind
    of wrong."""
    p = fasta(tmp_path, ">1 chr one\nACGT\n")
    log = Logger()

    assert prefix_fasta_ids(str(p), "GRCh38", log) == 1
    assert prefix_fasta_ids(str(p), "GRCh38", log) == 0
    assert p.read_text().startswith(">GRCh38_1 ")
    assert any("already carried" in m for m in log.infos)


@pytest.mark.parametrize("prefix", ["GRCh38", "GRCm39", "mRatBN7.2", "CB4856", "R64", "a1"])
def test_usable_prefixes(prefix):
    assert VALID_SEQID_PREFIX.match(prefix)


@pytest.mark.parametrize("prefix", [
    "GRCh38:p14",   # ':' is how an accession's coordinates are split
    "gnl|db",       # '|' is BLAST's seqid type separator
    "_leading",     # must start with a letter or digit
    "has space",
    "",
])
def test_unusable_prefixes_are_refused_rather_than_sanitised(tmp_path, prefix):
    p = fasta(tmp_path, ">1 chr one\nACGT\n")
    before = p.read_text()
    log = Logger()

    assert prefix_fasta_ids(str(p), prefix, log) is None
    assert p.read_text() == before, "the FASTA must be left alone"
    assert log.errors


def test_a_colon_prefix_is_refused_because_it_would_break_retrieval():
    """SequenceServer splits an accession on ':' to take coordinates
    (Database.retrieve), so a colon in an id makes every sequence in that
    database unretrievable -- the download and view buttons would both fail."""
    assert not VALID_SEQID_PREFIX.match("GRCh38:p14")


def test_the_separator_is_not_a_colon_or_a_pipe():
    assert SEQID_PREFIX_SEPARATOR not in (":", "|")


def test_a_missing_file_is_reported_not_raised(tmp_path):
    log = Logger()
    assert prefix_fasta_ids(str(tmp_path / "nope.fa"), "GRCh38", log) is None
    assert log.errors
