"""Test infrastructure: catch tests that pollute the source tree.

A test that writes into the repo (e.g. by passing the project root or `Path()`
as an `output_dir`) shows up as untracked files in `git status` and confuses
downstream tooling. This autouse fixture snapshots the repo root before each
test and fails the test if a new non-hidden entry appeared after.

`tmp_path` is the only correct place for test file output.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Entries the test infra is allowed to create at the repo root.
_ALLOWED_NEW_AT_ROOT = {
    ".pytest_cache",
    "htmlcov",
    ".coverage",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    ".cache",
}


def _snapshot_repo_root() -> set[str]:
    if not REPO_ROOT.exists():
        return set()
    return {p.name for p in REPO_ROOT.iterdir()}


@pytest.fixture(autouse=True)
def _fail_on_repo_root_writes():
    """After each test, fail if a new entry appeared at the repo root."""
    before = _snapshot_repo_root()
    yield
    after = _snapshot_repo_root()
    leaked = (after - before) - _ALLOWED_NEW_AT_ROOT
    leaked = {n for n in leaked if not n.startswith(".")}
    if not leaked:
        return
    # Clean up so subsequent tests don't see the residue.
    for name in leaked:
        target = REPO_ROOT / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            try:
                target.unlink()
            except OSError:
                pass
    pytest.fail(
        f"Test wrote artifacts to the repo root: {sorted(leaked)}. "
        "Use the `tmp_path` fixture for any file/dir output."
    )
