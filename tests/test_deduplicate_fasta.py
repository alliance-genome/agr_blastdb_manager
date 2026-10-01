"""
Tests for deduplicate_fasta.

The function exists because makeblastdb refuses duplicate sequence ids under
-parse_seqids, and FlyBase's dmel-transcript 6.69 export emits 4153 of them.
What matters is not that it removes duplicates but that it removes only the
ones it can remove without choosing: an identical repeat, or a repeat whose
other copy is not sequence data at all. Anything else must be left for a human,
because silently picking one of two plausible records is how a deployment ends
up serving data nobody has checked.
"""

import logging
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def _load():
    """
    Load just the helper.

    create_blast_db imports a click app and a .env reader, neither of which a
    unit test should need, so the function is exec'd out of the module source
    rather than imported.
    """
    source = (SRC / "create_blast_db.py").read_text()
    start = source.index("# Residues a FASTA")
    end = source.index("def run_makeblastdb")
    namespace = {}
    exec(  # noqa: S102 - reading our own source, not user input
        "from pathlib import Path\nfrom typing import Dict, Optional\n"
        + source[start:end],
        namespace,
    )
    return namespace["deduplicate_fasta"]


deduplicate_fasta = _load()
LOGGER = logging.getLogger("test_deduplicate_fasta")


def write(tmp_path, text):
    path = tmp_path / "seqs.fasta"
    path.write_text(text)
    return str(path)


def ids(path):
    return [
        line[1:].split()[0]
        for line in Path(path).read_text().splitlines()
        if line.startswith(">")
    ]


def test_clean_file_is_not_touched(tmp_path):
    """The common case must cost one read and change nothing."""
    path = write(tmp_path, ">a one\nACGT\n>b two\nTTTT\n")
    before = Path(path).read_text()

    assert deduplicate_fasta(path, "nucl", LOGGER) is None
    assert Path(path).read_text() == before


def test_identical_repeats_collapse(tmp_path):
    path = write(tmp_path, ">a one\nACGT\n>b two\nTTTT\n>a one\nACGT\n>c three\nGGGG\n")

    result = deduplicate_fasta(path, "nucl", LOGGER)

    assert result["removed"] == 1
    assert result["corrupt"] == 0
    assert result["unresolved"] == 0
    assert ids(path) == ["a", "b", "c"]


def test_first_occurrence_is_the_one_kept(tmp_path):
    """Order is preserved, so a file stays diffable against its source."""
    path = write(tmp_path, ">a one\nACGT\n>b two\nTTTT\n>a one\nACGT\n")

    deduplicate_fasta(path, "nucl", LOGGER)

    assert Path(path).read_text() == ">a one\nACGT\n>b two\nTTTT\n"


def test_corrupt_copy_is_dropped_in_favour_of_the_valid_one(tmp_path):
    """
    FlyBase's actual defect, reduced: FBtr0077872 appears twice, once as its
    71 bp tRNA and once as that sequence with a line of `ls -l` output
    concatenated onto it. The corrupt copy is identifiable without guessing
    because it is not nucleotide sequence.
    """
    path = write(
        tmp_path,
        ">t tRNA\nACGTACGT-rw-r--r-- 1 argosadm fbadmin 61946 /bio/ftp/x.fasta.gz\n"
        ">t tRNA\nACGTACGT\n",
    )

    result = deduplicate_fasta(path, "nucl", LOGGER)

    assert result["removed"] == 1
    assert result["corrupt"] == 1
    assert Path(path).read_text() == ">t tRNA\nACGTACGT\n"


def test_two_plausible_records_are_refused(tmp_path):
    """
    Both copies are valid sequence, so there is no principled way to choose.
    The file must be left alone and makeblastdb allowed to reject it.
    """
    path = write(tmp_path, ">a one\nACGT\n>a one\nTTTT\n")
    before = Path(path).read_text()

    result = deduplicate_fasta(path, "nucl", LOGGER)

    assert result["unresolved"] == 1
    assert result["removed"] == 0
    assert Path(path).read_text() == before


def test_protein_alphabet_is_not_judged_by_nucleotide_rules(tmp_path):
    """
    A protein sequence is full of letters that are invalid as nucleotides, so
    the validity check has to follow the declared seqtype or it would call
    every protein record corrupt.
    """
    path = write(tmp_path, ">p prot\nMEHEKDPGWQYLRR\n>p prot\nMEHEKDPGWQYLRR\n")

    result = deduplicate_fasta(path, "prot", LOGGER)

    assert result["removed"] == 1
    assert result["corrupt"] == 0
    assert ids(path) == ["p"]


def test_unknown_seqtype_does_not_guess_at_validity(tmp_path):
    """
    With no alphabet to judge by, differing copies are unresolved rather than
    being ranked by a rule that does not apply.
    """
    path = write(tmp_path, ">a one\nACGT\n>a one\nZZZZ\n")

    result = deduplicate_fasta(path, "something-else", LOGGER)

    assert result["unresolved"] == 1
    assert result["removed"] == 0


def test_multiline_records_survive_intact(tmp_path):
    """Wrapped FASTA is the norm; the rewrite must not reflow or truncate it."""
    path = write(
        tmp_path,
        ">a one\nACGT\nACGT\nAC\n>b two\nTTTT\n>a one\nACGT\nACGT\nAC\n",
    )

    deduplicate_fasta(path, "nucl", LOGGER)

    assert Path(path).read_text() == ">a one\nACGT\nACGT\nAC\n>b two\nTTTT\n"


def test_id_is_the_first_whitespace_delimited_token(tmp_path):
    """
    Two records sharing a full defline are duplicates; two that merely share a
    description are not. makeblastdb keys on the id, so this must too.
    """
    path = write(tmp_path, ">a shared description\nACGT\n>b shared description\nTTTT\n")

    assert deduplicate_fasta(path, "nucl", LOGGER) is None


@pytest.mark.parametrize("residue", ["N", "n", "-", "*", "R", "Y"])
def test_iupac_codes_and_gaps_count_as_sequence(tmp_path, residue):
    """
    Ambiguity codes and gaps are ordinary content. Treating them as corruption
    would make the function discard the wrong copy of a real duplicate.
    """
    path = write(tmp_path, f">a one\nACGT{residue}\n>a one\nACGT\n")

    result = deduplicate_fasta(path, "nucl", LOGGER)

    assert result["unresolved"] == 1, f"{residue!r} should be valid nucleotide content"
