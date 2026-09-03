"""Run frontend behavioral regressions without browser or external API access."""

from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for frontend runtime tests")
def test_frontend_integration_runtime() -> None:
    result = subprocess.run(
        [shutil.which("node"), "--test", "tests/frontend/integration_refresh.test.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_current_result_and_medical_guidance_are_not_hidden_with_future_results() -> None:
    class ParentIds(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []
            self.parents = {}

        def handle_starttag(self, tag, attrs):
            element_id = dict(attrs).get("id")
            if element_id:
                assert element_id not in self.parents, f"Duplicate HTML id: {element_id}"
                self.parents[element_id] = [item[1] for item in self.stack]
            if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
                self.stack.append((tag, element_id))

        def handle_endtag(self, tag):
            assert self.stack and self.stack[-1][0] == tag, f"Unbalanced HTML closing tag: {tag}"
            self.stack.pop()

    parser = ParentIds()
    parser.feed((ROOT / "src/frontend/index.html").read_text(encoding="utf-8"))
    assert not parser.stack
    for element_id in ["risk-confirm-card", "medical-guidance-detail"]:
        assert "future-prediction-result" not in parser.parents[element_id]
    assert "future-prediction-result" in parser.parents["risk-forecast-panel"]
