"""
test_utils_properties.py

Property-based tests (Hypothesis) for the FASTA header handling in utils:
needs_parse_seqids, edit_fasta, and the defline parsing behind the name index
(index_entries, sgd_symbol, build_name_index).

Example-based tests for the same functions live in test_utils.py; these check
invariants over generated headers and sequences instead of a few fixed files.
"""

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.utils import (
    NAME_INDEX_SUFFIX,
    build_name_index,
    edit_fasta,
    index_entries,
    needs_parse_seqids,
    sgd_symbol,
)

# Every test writes a small file per example; keep runs quick.
settings.register_profile("utils_properties", max_examples=150, deadline=None)
settings.load_profile("utils_properties")

# NCBI database tags recognised by needs_parse_seqids ("lcl|", "gb|", ...).
NCBI_PREFIXES = [
    "lcl",
    "ref",
    "gb",
    "emb",
    "dbj",
    "pir",
    "prf",
    "sp",
    "pdb",
    "pat",
    "bbs",
    "gnl",
    "gi",
]
MODS = ["FB", "SGD", "WB", "XB", "RGD", None]

# Identifiers and descriptions as MODs write them, minus "|" so a header built
# from them is never an NCBI-style seqid unless a test adds one on purpose.
ID_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-:"
seq_ids = st.text(alphabet=ID_CHARS, min_size=1, max_size=20)
descriptions = st.text(alphabet=ID_CHARS + " =[],;()/", min_size=0, max_size=40).map(
    str.rstrip
)
residues = st.text(alphabet="ACGTNacgtnRYKM*-", min_size=1, max_size=60)


@st.composite
def plain_headers(draw):
    """A '>' header with no '|' anywhere."""
    header = ">" + draw(seq_ids)
    desc = draw(descriptions)
    return f"{header} {desc}" if desc else header


@st.composite
def fasta_records(draw, header_strategy=plain_headers()):
    """A list of (header, [sequence lines]) records."""
    return draw(
        st.lists(
            st.tuples(header_strategy, st.lists(residues, min_size=1, max_size=4)),
            min_size=1,
            max_size=6,
        )
    )


def render(records) -> str:
    lines = []
    for header, seq_lines in records:
        lines.append(header)
        lines.extend(seq_lines)
    return "\n".join(lines) + "\n"


def write_fasta(directory: str, text: str) -> str:
    path = Path(directory) / "input.fa"
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- needs_parse_seqids -----------------------------------------------------


@given(records=fasta_records(), prefix=st.sampled_from(NCBI_PREFIXES))
def test_zfin_never_uses_parse_seqids(records, prefix):
    """ZFIN is excluded outright, even when its headers look like NCBI seqids."""
    records = records + [(f">{prefix}|X1", ["ACGT"])]
    with tempfile.TemporaryDirectory() as d:
        assert needs_parse_seqids(write_fasta(d, render(records)), "ZFIN") is False


@given(records=fasta_records(), mod=st.sampled_from(MODS))
def test_headers_without_pipes_do_not_need_parse_seqids(records, mod):
    with tempfile.TemporaryDirectory() as d:
        assert needs_parse_seqids(write_fasta(d, render(records)), mod) is False


@given(
    records=fasta_records(),
    prefix=st.sampled_from(NCBI_PREFIXES),
    seq_id=seq_ids,
    position=st.integers(min_value=0),
    mod=st.sampled_from(MODS),
)
def test_one_ncbi_style_header_is_enough(records, prefix, seq_id, position, mod):
    """A single NCBI-tagged header anywhere in the file turns the flag on."""
    records = list(records)
    records.insert(position % (len(records) + 1), (f">{prefix}|{seq_id}", ["ACGT"]))
    with tempfile.TemporaryDirectory() as d:
        assert needs_parse_seqids(write_fasta(d, render(records)), mod) is True


@given(records=fasta_records(), parts=st.lists(seq_ids, min_size=3, max_size=5))
def test_any_header_with_two_pipes_needs_parse_seqids(records, parts):
    records = records + [(">" + "|".join(parts), ["ACGT"])]
    with tempfile.TemporaryDirectory() as d:
        assert needs_parse_seqids(write_fasta(d, render(records)), "FB") is True


@given(records=fasta_records(), prefix=st.sampled_from(NCBI_PREFIXES), seq_id=seq_ids)
def test_pipes_in_sequence_lines_are_ignored(records, prefix, seq_id):
    """Only header lines are inspected; a '|' in a non-header line is not a seqid."""
    records = [(h, seq + [f"{prefix}|{seq_id}|x"]) for h, seq in records]
    with tempfile.TemporaryDirectory() as d:
        assert needs_parse_seqids(write_fasta(d, render(records)), "FB") is False


# --- edit_fasta -------------------------------------------------------------

config_entries = st.fixed_dictionaries(
    {"genus": seq_ids, "species": seq_ids, "version": seq_ids},
    optional={"seqcol": seq_ids},
)


def expected_suffix(entry: dict) -> str:
    if "seqcol" in entry:
        return f" {entry['seqcol']} {entry['genus']} {entry['species']}"
    return f" {entry['genus']} {entry['species']} {entry['version']}"


@given(records=fasta_records(), entry=config_entries)
def test_edit_fasta_only_appends_to_headers(records, entry):
    """Headers gain the configured suffix; sequence lines are left byte-for-byte."""
    original = render(records)
    with tempfile.TemporaryDirectory() as d:
        path = write_fasta(d, original)
        assert edit_fasta(path, entry) is True
        edited = Path(path).read_text(encoding="utf-8")

    before = original.splitlines()
    after = edited.splitlines()
    assert len(after) == len(before)
    for old, new in zip(before, after):
        if old.startswith(">"):
            assert new == old.strip() + expected_suffix(entry)
        else:
            assert new == old


@given(records=fasta_records(), entry=config_entries)
def test_edit_fasta_keeps_first_token_of_each_header(records, entry):
    """The seqid makeblastdb reads (first token after '>') is never changed."""
    with tempfile.TemporaryDirectory() as d:
        path = write_fasta(d, render(records))
        edit_fasta(path, entry)
        edited = Path(path).read_text(encoding="utf-8")

    ids_before = [h[1:].split()[0] for h, _ in records]
    ids_after = [
        line[1:].split()[0] for line in edited.splitlines() if line.startswith(">")
    ]
    assert ids_after == ids_before


# --- name index: index_entries / sgd_symbol / build_name_index --------------

gene_tags = st.lists(
    st.tuples(st.sampled_from(["gene", "locus_tag"]), seq_ids), max_size=3
)


@st.composite
def tagged_entries(draw):
    """(accession, defline) pairs shaped like NCBI-derived FASTA headers."""
    entries = []
    for _ in range(draw(st.integers(min_value=0, max_value=6))):
        accession = draw(seq_ids)
        tags = " ".join(f"[{k}={v}]" for k, v in draw(gene_tags))
        entries.append((accession, f">{accession} {tags}".rstrip() + "\n"))
    return entries


@given(entries=tagged_entries())
def test_index_values_are_input_accessions(entries):
    index = index_entries(entries)
    accessions = {acc for acc, _ in entries}
    assert set(index.values()) <= accessions


@given(entries=tagged_entries())
def test_index_keys_are_lower_case(entries):
    assert all(key == key.lower() for key in index_entries(entries))


@given(entries=tagged_entries())
def test_every_accession_is_findable(entries):
    """Each accession resolves case-insensitively to some accession of that name.

    First wins, so an accession an earlier tag already claimed may resolve to
    the earlier record; it must still be present.
    """
    index = index_entries(entries)
    for accession, _ in entries:
        assert accession.lower() in index


@given(entries=tagged_entries())
def test_first_entry_accession_maps_to_itself(entries):
    if entries:
        accession = entries[0][0]
        assert index_entries(entries)[accession.lower()] == accession


@given(entries=tagged_entries())
def test_repeating_entries_changes_nothing(entries):
    """First wins, so appending the same deflines again is a no-op."""
    assert index_entries(entries + entries) == index_entries(entries)


@given(entries=tagged_entries())
def test_empty_accessions_are_skipped(entries):
    with_blank = [("", "> [gene=SHOULDNOTAPPEAR]\n")] + entries
    assert index_entries(with_blank) == index_entries(entries)


@given(text=descriptions)
def test_sgd_symbol_needs_sgdid_marker(text):
    if "SGDID:" not in text:
        assert sgd_symbol(text) is None


@given(
    systematic=seq_ids,
    symbol=seq_ids,
    sgdid=st.from_regex(r"S[0-9]{9}", fullmatch=True),
    rest=descriptions,
)
def test_sgd_symbol_is_token_before_sgdid(systematic, symbol, sgdid, rest):
    defline = f">{systematic} {symbol} SGDID:{sgdid}, {rest}"
    assert sgd_symbol(defline) == symbol


@given(records=fasta_records())
def test_build_name_index_matches_index_entries(records):
    """The on-disk index is exactly index_entries over the file's deflines."""
    with tempfile.TemporaryDirectory() as d:
        path = write_fasta(d, render(records))
        db_path = str(Path(d) / "db")
        count = build_name_index(path, db_path)
        written = json.loads(Path(db_path + NAME_INDEX_SUFFIX).read_text())

    expected = index_entries((h[1:].split()[0], h + "\n") for h, _ in records)
    assert written == expected
    assert count == len(expected)
