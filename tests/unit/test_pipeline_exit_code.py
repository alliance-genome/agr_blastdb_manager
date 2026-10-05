"""
The pipeline has to report failure through its exit status.

It did not. `process_json_entries` returned `successful > 0` -- true of a run
where one database out of two hundred built -- both callers discarded it, and
`create_dbs` printed "PIPELINE COMPLETED SUCCESSFULLY" and exited 0 regardless.
A build that cannot fail cannot be run from cron or CI, and it is how ALLIANCE
shipped a partial set in 2024 without anyone noticing.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import create_blast_db as cbd  # noqa: E402


def write_config(tmp_path, titles):
    """A config with one entry per title, shaped as the pipeline expects."""
    path = tmp_path / "databases.FB.FB2026_03.json"
    path.write_text(
        json.dumps(
            {
                "metaData": {"release": "FB2026_03"},
                "data": [
                    {
                        "blast_title": t,
                        "uri": f"https://example.invalid/{t}.fa.gz",
                        "genus": "Drosophila",
                        "species": "melanogaster",
                        "seqtype": "nucl",
                        "md5sum": "0" * 32,
                    }
                    for t in titles
                ],
            }
        )
    )
    return path


def run(tmp_path, monkeypatch, titles, outcomes, db_list=None):
    """
    Drive process_json_entries with process_entry stubbed, so the counting is
    what is under test rather than makeblastdb.
    """
    monkeypatch.chdir(tmp_path)
    Path("../logs").mkdir(parents=True, exist_ok=True)
    config = write_config(tmp_path, titles)

    calls = []

    def fake_process_entry(entry, mod_code, environment, *a, **kw):
        title = entry["blast_title"]
        calls.append(title)
        outcome = outcomes[title]
        if outcome == "raise":
            raise RuntimeError(f"boom in {title}")
        return outcome

    monkeypatch.setattr(cbd, "process_entry", fake_process_entry)
    monkeypatch.setattr(cbd, "slack_message", lambda *a, **kw: None)
    cbd.FAILURE_DETAILS.clear()

    failed = cbd.process_json_entries(
        str(config), "FB2026_03", "FB", db_list,
        check_only=True, store_files=False, cleanup=False,
    )
    return failed, calls


def test_a_clean_run_reports_no_failures(tmp_path, monkeypatch):
    failed, calls = run(tmp_path, monkeypatch, ["a", "b"], {"a": True, "b": True})
    assert failed == 0
    assert calls == ["a", "b"]


def test_one_failure_among_many_is_reported(tmp_path, monkeypatch):
    """The old contract returned True here, because something succeeded."""
    failed, _ = run(
        tmp_path, monkeypatch,
        ["a", "b", "c"], {"a": True, "b": False, "c": True},
    )
    assert failed == 1


def test_every_entry_failing_is_reported(tmp_path, monkeypatch):
    failed, _ = run(tmp_path, monkeypatch, ["a", "b"], {"a": False, "b": False})
    assert failed == 2


def test_an_exception_counts_as_a_failure_and_is_recorded(tmp_path, monkeypatch):
    """An exception escaping process_entry reached none of its FAILURE_DETAILS
    sites, so it was absent from the summary as well as from the count."""
    failed, _ = run(
        tmp_path, monkeypatch, ["a", "b"], {"a": "raise", "b": True}
    )
    assert failed == 1
    assert any(d["entry"] == "a" for d in cbd.FAILURE_DETAILS)


def test_a_skipped_entry_is_not_a_failure(tmp_path, monkeypatch):
    """`processed - successful` counted these, because `processed` is
    incremented before the --db-list skip: a narrow run reported failures it
    had not had."""
    failed, calls = run(
        tmp_path, monkeypatch,
        ["a", "b", "c"], {"a": True, "b": True, "c": True},
        db_list=["b"],
    )
    assert calls == ["b"]
    assert failed == 0


def test_a_missing_mod_code_is_a_failure_not_a_no_op(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = write_config(tmp_path, ["a"])
    monkeypatch.setattr(cbd, "get_mod_from_json", lambda _f: None)
    assert cbd.process_json_entries(str(config), "FB2026_03", None, None,
                                    check_only=True, cleanup=False) == 1


def test_an_unreadable_config_is_a_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cbd.process_json_entries(str(tmp_path / "nope.json"), "FB2026_03", "FB",
                                    None, check_only=True, cleanup=False) == 1
