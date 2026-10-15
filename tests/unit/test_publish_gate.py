"""
A partial build must not publish a manifest for databases it did not build,
and a build that cannot fit must not start.

Both conditions were missing. `copy_config_file` republishes the build INPUT
as environment.json, and it ran whenever `successful > 0`, so a run where one
entry of nine built wrote a manifest promising all nine; that is how the
Alliance deployment declared nine reference genomes while serving one for two
years. Nothing checked free space either: a full disk produced seven ENOSPC
failures mid-run, each leaving a partial database behind.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import create_blast_db as cbd  # noqa: E402


def write_config(tmp_path, titles):
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


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """
    process_json_entries with everything below it stubbed.

    check_only is False here, unlike test_pipeline_exit_code.py, because both
    gates under test are skipped in a check-only run.
    """
    monkeypatch.chdir(tmp_path)
    Path("../logs").mkdir(parents=True, exist_ok=True)

    state = {"copied": [], "browser_maps": [], "cleaned": 0, "built": []}

    monkeypatch.setattr(cbd, "slack_message", lambda *a, **kw: None)
    monkeypatch.setattr(
        cbd, "copy_config_file",
        lambda src, dest, logger: state["copied"].append(str(src)) or True,
    )
    monkeypatch.setattr(
        cbd, "update_genome_browser_map",
        lambda *a, **kw: state["browser_maps"].append(a[0]["blast_title"]) or True,
    )
    monkeypatch.setattr(
        cbd, "cleanup_fasta_files",
        lambda *a, **kw: state.update(cleaned=state["cleaned"] + 1),
    )
    # No network: every source is 1 GB unless a test says otherwise.
    monkeypatch.setattr(cbd, "remote_content_length", lambda uri, timeout=20: 10**9)

    def run(titles, outcomes, **kwargs):
        config = write_config(tmp_path, titles)

        def fake_process_entry(entry, *a, **kw):
            title = entry["blast_title"]
            state["built"].append(title)
            return outcomes[title]

        monkeypatch.setattr(cbd, "process_entry", fake_process_entry)
        cbd.FAILURE_DETAILS.clear()
        cbd.PROCESSED_DATABASES.clear()
        return cbd.process_json_entries(
            str(config), "FB2026_03", "FB", kwargs.pop("db_list", None),
            check_only=False, store_files=False, cleanup=False, **kwargs,
        )

    return run, state, monkeypatch


class TestPublishGate:
    def test_a_clean_run_publishes(self, harness):
        run, state, _ = harness
        assert run(["a", "b"], {"a": True, "b": True}, skip_space_check=True) == 0
        assert len(state["copied"]) == 1
        assert cbd.PROCESSED_DATABASES == [("FB", "FB2026_03")]

    def test_a_partial_run_does_not_publish(self, harness):
        """The condition this replaces was `successful > 0`, which is true
        here: one of three built."""
        run, state, _ = harness
        failed = run(["a", "b", "c"], {"a": True, "b": False, "c": False},
                     skip_space_check=True)
        assert failed == 2
        assert state["copied"] == []
        assert cbd.PROCESSED_DATABASES == []

    def test_a_partial_run_writes_no_genome_browser_map_either(self, harness):
        run, state, _ = harness
        run(["a", "b"], {"a": True, "b": False}, skip_space_check=True)
        assert state["browser_maps"] == []

    def test_force_publish_accepts_a_partial_build(self, harness):
        """Accepting a partial build is a decision, so it has to be typed."""
        run, state, _ = harness
        failed = run(["a", "b"], {"a": True, "b": False},
                     skip_space_check=True, force_publish=True)
        assert failed == 1
        assert len(state["copied"]) == 1
        assert cbd.PROCESSED_DATABASES == [("FB", "FB2026_03")]

    def test_a_narrowed_run_still_publishes(self, harness):
        """An entry skipped by --db-list is not a failure, so a run of one
        requested database is a clean run."""
        run, state, _ = harness
        failed = run(["a", "b", "c"], {"a": True, "b": True, "c": True},
                     db_list=["b"], skip_space_check=True)
        assert failed == 0
        assert state["built"] == ["b"]
        assert len(state["copied"]) == 1

    def test_a_run_where_nothing_built_publishes_nothing(self, harness):
        run, state, _ = harness
        assert run(["a"], {"a": False}, skip_space_check=True) == 1
        assert state["copied"] == []


class TestDiskEstimate:
    def test_the_estimate_is_the_kept_total_plus_one_transient_peak(self):
        """Peak disk is not the sum of everything: run_makeblastdb unlinks the
        unzipped FASTA and the .gz as each entry finishes, so one entry's
        intermediates exist at a time while the databases accumulate."""
        entries = [{"uri": "https://e.invalid/a.gz"}, {"uri": "https://e.invalid/b.gz"}]
        sizes = {"https://e.invalid/a.gz": 100, "https://e.invalid/b.gz": 300}
        original = cbd.remote_content_length
        cbd.remote_content_length = lambda uri, timeout=20: sizes[uri]
        try:
            required, keep, peak = cbd.estimate_disk_required(entries)
        finally:
            cbd.remote_content_length = original

        assert keep == 400                      # BUILT_FACTOR 1.0 x sum
        assert peak == int(300 * (1 + 3.1 + 1.0))  # largest, three ways
        assert required == keep + peak

    def test_a_source_of_unknown_size_contributes_nothing(self):
        original = cbd.remote_content_length
        cbd.remote_content_length = lambda uri, timeout=20: 0
        try:
            assert cbd.estimate_disk_required([{"uri": "x"}]) == (0, 0, 0)
        finally:
            cbd.remote_content_length = original

    def test_a_non_http_uri_is_not_fetched(self):
        assert cbd.remote_content_length("ftp://ftp.invalid/x.gz") == 0
        assert cbd.remote_content_length("") == 0


class TestSpaceCheck:
    def test_a_run_that_cannot_fit_does_not_start(self, harness):
        run, state, monkeypatch = harness
        # 1 GB of free space against two 1 GB sources.
        monkeypatch.setattr(cbd.shutil, "disk_usage",
                            lambda p: type("U", (), {"free": 10**9})())
        failed = run(["a", "b"], {"a": True, "b": True})

        # Every entry counts as failed: none of them ran.
        assert failed == 2
        assert state["built"] == []
        assert state["copied"] == []
        assert any(d["stage"] == "disk space check" for d in cbd.FAILURE_DETAILS)

    def test_a_run_that_fits_starts(self, harness):
        run, state, monkeypatch = harness
        monkeypatch.setattr(cbd.shutil, "disk_usage",
                            lambda p: type("U", (), {"free": 10**12})())
        assert run(["a", "b"], {"a": True, "b": True}) == 0
        assert state["built"] == ["a", "b"]

    def test_skip_space_check_starts_anyway(self, harness):
        run, state, monkeypatch = harness
        monkeypatch.setattr(cbd.shutil, "disk_usage",
                            lambda p: type("U", (), {"free": 1})())
        assert run(["a"], {"a": True}, skip_space_check=True) == 0
        assert state["built"] == ["a"]

    def test_sources_of_unknown_size_do_not_block_a_build(self, harness):
        """A server that hides Content-Length must not be able to stop a
        build; the check goes quiet instead."""
        run, state, monkeypatch = harness
        monkeypatch.setattr(cbd, "remote_content_length", lambda uri, timeout=20: 0)
        monkeypatch.setattr(cbd.shutil, "disk_usage",
                            lambda p: type("U", (), {"free": 1})())
        assert run(["a"], {"a": True}) == 0
        assert state["built"] == ["a"]

    def test_the_message_names_what_is_free_and_what_is_needed(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cbd, "remote_content_length", lambda uri, timeout=20: 10**9)
        monkeypatch.setattr(cbd.shutil, "disk_usage",
                            lambda p: type("U", (), {"free": 2 * 10**9})())
        message = cbd.check_disk_space([{"uri": "https://e.invalid/a.gz"}], tmp_path)
        assert message is not None
        assert "2.0 GB free" in message
        assert "--skip-space-check" in message
