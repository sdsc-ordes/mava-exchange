"""
Guards for files the test suite does not otherwise execute.

The ontology, the SHACL shapes and the prose docs are all shipped artifacts,
but nothing imports them, so a syntax error in any of them passes every other
test and only surfaces when a docs build or an RDF consumer breaks. These are
cheap structural checks, not semantic ones.
"""

import ast
import re
from pathlib import Path

import pytest
import rdflib

from mava_exchange import rdf as rdf_module

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = REPO_ROOT / "spec"
DOCS_DIR = REPO_ROOT / "docs"

PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


# ─────────────────────────────────────────────
# RDF artifacts
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name", ["mava.ttl", "mava.shacl.ttl"])
def test_turtle_file_parses(name):
    """A missing ';' silently breaks the whole file for every consumer."""
    path = SPEC_DIR / name
    graph = rdflib.Graph()
    graph.parse(path, format="turtle")
    assert len(graph) > 0, f"{name} parsed but is empty"


def test_ontology_declares_every_property_used_by_the_exporter():
    """Terms the RDF exporter emits must exist in the ontology."""
    graph = rdflib.Graph()
    graph.parse(SPEC_DIR / "mava.ttl", format="turtle")
    declared = {str(s) for s in graph.subjects()}

    source = Path(rdf_module.__file__).read_text()
    used = {f"http://example.org/mava/ontology#{m}"
            for m in re.findall(r"\bMAVA\.(\w+)", source)}

    missing = sorted(used - declared)
    assert not missing, f"emitted but not declared in mava.ttl: {missing}"


# ─────────────────────────────────────────────
# Documentation code samples
# ─────────────────────────────────────────────

def _python_blocks():
    for path in sorted(DOCS_DIR.rglob("*.md")):
        for index, block in enumerate(PYTHON_BLOCK.findall(path.read_text())):
            yield pytest.param(block, id=f"{path.relative_to(REPO_ROOT)}:block{index}")


@pytest.mark.parametrize(("block"), list(_python_blocks()))
def test_docs_python_block_parses(block):
    """Sphinx renders fenced code verbatim, so broken samples ship silently."""
    ast.parse(block)


def test_docs_contain_python_blocks():
    """Guard the guard: a bad glob would make the check above vacuous."""
    assert len(list(_python_blocks())) > 10
