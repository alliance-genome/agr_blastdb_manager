"""
test_ui_flow.py

Drive BlastUITester (tests/ui/test_ui.py) against a local stand-in for the
SequenceServer search page, so the Playwright flow -- select a database, paste
a sequence, submit, wait for #view, screenshot -- is exercised without a BLAST
server or network access.

Needs a Playwright browser: `uv run playwright install chromium`, or set
PLAYWRIGHT_CHANNEL=chrome to use an installed Google Chrome. Skipped otherwise.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import Error as PlaywrightError  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from tests.ui.test_ui import BlastUITester  # noqa: E402

CHANNEL = os.environ.get("PLAYWRIGHT_CHANNEL") or None

# Same element ids and names as the SequenceServer search form the real tests
# target: database checkboxes by id, textarea name=sequence, #method submits,
# and results render into #view.
SEARCH_PAGE = b"""<!doctype html>
<html><body>
  <textarea id="sequence" name="sequence"></textarea>
  <input type="checkbox" id="Drosophila_anchor">
  <input type="checkbox" id="Apis_anchor">
  <button id="method" type="button">BLAST</button>
  <script>
    document.getElementById("method").addEventListener("click", () => {
      const picked = document.querySelector("input[type=checkbox]:checked");
      const seq = document.getElementById("sequence").value;
      if (!picked || !seq) return;
      setTimeout(() => {
        const view = document.createElement("div");
        view.id = "view";
        view.textContent = "hits for " + picked.id + ": " + seq.length + " bp";
        document.body.appendChild(view);
      }, 200);
    });
  </script>
</body></html>
"""


class SearchPageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(SEARCH_PAGE)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def browser_available():
    try:
        with sync_playwright() as p:
            p.chromium.launch(channel=CHANNEL).close()
    except PlaywrightError as e:
        pytest.skip(f"No Playwright browser available: {e}")


@pytest.fixture
def base_url(browser_available):
    server = ThreadingHTTPServer(("127.0.0.1", 0), SearchPageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/blast"
    server.shutdown()
    server.server_close()


def make_tester(base_url):
    return BlastUITester(
        base_url=base_url, browser_channel=CHANNEL, wait_timeout=5, result_timeout=10
    )


def test_run_test_screenshots_each_database(base_url, tmp_path):
    tester = make_tester(base_url)
    tester.run_test(
        "FB", ["Drosophila_anchor", "Apis_anchor"], "FB2025_03", "ACGT", tmp_path
    )

    assert (tmp_path / "FB" / "Drosophila_anchor.png").stat().st_size > 0
    assert (tmp_path / "FB" / "Apis_anchor.png").stat().st_size > 0
    assert tester.browser is None, "browser should be closed after the run"


def test_comprehensive_counts_success_and_missing_database(base_url, tmp_path):
    tester = make_tester(base_url)
    results = tester.run_comprehensive_test(
        "FB", ["Drosophila_anchor", "Missing_anchor"], "FB2025_03", "ACGT", tmp_path
    )

    assert results["total_tests"] == 2
    assert results["successful"] == 1
    assert results["failed"] == 1

    ok, missing = results["details"]
    assert ok["success"] and not ok["errors"]
    assert not missing["success"]
    assert "Database checkbox Missing_anchor not found" in missing["errors"]

    shots = {p.name for p in (tmp_path / "FB" / "comprehensive").iterdir()}
    assert any(name.endswith("Drosophila_anchor_06_results.png") for name in shots)
