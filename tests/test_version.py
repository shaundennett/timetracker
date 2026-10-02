import re
from pathlib import Path

import timetracker


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", timetracker.__version__)


def test_pyproject_reads_version_from_package():
    text = (Path(__file__).parent.parent / "pyproject.toml").read_text(
        encoding="utf-8")
    assert 'dynamic = ["version"]' in text
    assert 'attr = "timetracker.__version__"' in text
    # No second, hand-maintained copy of the number.
    assert not re.search(r'^version\s*=\s*"', text, re.M)
