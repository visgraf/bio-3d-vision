"""Scaffold guards. Infrastructure — these pin the repository's shape, not any
result about vision.

Two of the rules in CLAUDE.md are stated as enforced. This is where they are
enforced, so that "CI enforces that" is a true sentence rather than an intention:

* nothing in the library or in experiments may import from ``spikes/``;
* nothing in the repository may reach into the reference checkouts.
"""

import ast
import pathlib

import pytest

pytestmark = pytest.mark.infrastructure

REPO = pathlib.Path(__file__).resolve().parents[1]

# Built by concatenation rather than written literally, so that the scan below
# can cover *this* file too instead of having to exempt its own needle.
REFERENCE_DIR = "." + "reference"

# Directories whose code must stay free of both. `experiments` does not exist
# yet; it is listed so the guard starts working the moment it does.
GOVERNED = ("src", "tests", "experiments")


def _python_files(*roots: str) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for root in roots:
        base = REPO / root
        if base.is_dir():
            out.extend(sorted(base.rglob("*.py")))
    return out


def test_package_imports() -> None:
    """The library imports and is empty, which is the accurate state."""
    import bio3dvision

    assert bio3dvision.__all__ == []


def test_governed_trees_do_not_import_spikes() -> None:
    """A spike's only permitted output is a decision or a deletion.

    Neither of those is "the library grew a dependency on it". Parsed rather than
    grepped, so a mention in a docstring or a comment does not trip it and a real
    import cannot hide behind formatting.
    """
    offenders: list[str] = []
    for path in _python_files(*GOVERNED):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name == "spikes" or name.startswith("spikes."):
                    offenders.append(f"{path.relative_to(REPO)}:{node.lineno} imports {name}")
    assert not offenders, "spikes/ must not be importable by the library:\n" + "\n".join(offenders)


def test_nothing_reaches_into_the_reference_checkouts() -> None:
    """The references are read by people, never by code.

    They are pinned clones of other repositories, they are git-ignored, and they
    are not present in CI. Any code path that reads one passes locally and fails
    everywhere else, which is the worst available failure mode.
    """
    offenders: list[str] = []
    for path in _python_files(*GOVERNED):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if REFERENCE_DIR in line and "REFERENCE_DIR" not in line:
                offenders.append(f"{path.relative_to(REPO)}:{lineno}")
    assert not offenders, "code must not reference the pinned clones:\n" + "\n".join(offenders)


def test_no_per_layer_packages() -> None:
    """Flat by decision (fc-002). Structure is added when something needs it.

    A guard rather than a comment because the predecessor's layout was reasonable
    at every individual step and unbalanced in aggregate: 42.1% of its library
    was stimulus infrastructure against 9.1% for scaling, control and policy
    combined. Delete this test when a real need for structure arrives — and
    record the reason, because that is what fc-002 asks.
    """
    package = REPO / "src" / "bio3dvision"
    subpackages = [p.name for p in package.iterdir() if p.is_dir() and (p / "__init__.py").exists()]
    assert not subpackages, f"flat by decision; found subpackages: {subpackages}"
