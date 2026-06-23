"""Tests for strip_notebook_output.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from the scripts directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from strip_notebook_output import (
    cell_has_output,
    check_notebooks,
    estimate_output_size,
    get_staged_notebooks,
    load_notebook,
    strip_notebook,
)


@pytest.fixture
def notebook_with_output(tmp_path: Path) -> Path:
    """Create a sample notebook with cell output."""
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "name": "stdout",
                        "output_type": "stream",
                        "text": ["Hello, world!\n"],
                    }
                ],
                "source": ["print('Hello, world!')"],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Title"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["x = 42"],
            },
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = tmp_path / "test.ipynb"
    path.write_text(json.dumps(nb), encoding="utf-8")
    return path


@pytest.fixture
def notebook_without_output(tmp_path: Path) -> Path:
    """Create a sample notebook without cell output."""
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["x = 1"],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Clean notebook"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = tmp_path / "clean.ipynb"
    path.write_text(json.dumps(nb), encoding="utf-8")
    return path


@pytest.fixture
def notebook_with_rich_output(tmp_path: Path) -> Path:
    """Create a notebook with display_data and execute_result outputs."""
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 5,
                "metadata": {},
                "outputs": [
                    {
                        "output_type": "execute_result",
                        "data": {
                            "text/plain": ["42"],
                            "text/html": ["<b>42</b>"],
                        },
                        "metadata": {},
                        "execution_count": 5,
                    }
                ],
                "source": ["40 + 2"],
            },
            {
                "cell_type": "code",
                "execution_count": 6,
                "metadata": {},
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {
                            "image/png": ["iVBORw0KGgoAAAANSUhEUg=="],
                        },
                        "metadata": {},
                    }
                ],
                "source": ["plt.plot([1,2,3])"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = tmp_path / "rich.ipynb"
    path.write_text(json.dumps(nb), encoding="utf-8")
    return path


class TestCellHasOutput:
    def test_code_cell_with_output_returns_true(self) -> None:
        cell = {"cell_type": "code", "outputs": [{"output_type": "stream"}], "execution_count": 1}
        assert cell_has_output(cell) is True

    def test_code_cell_with_only_execution_count_returns_true(self) -> None:
        cell = {"cell_type": "code", "outputs": [], "execution_count": 3}
        assert cell_has_output(cell) is True

    def test_code_cell_without_output_returns_false(self) -> None:
        cell = {"cell_type": "code", "outputs": [], "execution_count": None}
        assert cell_has_output(cell) is False

    def test_markdown_cell_returns_false(self) -> None:
        cell = {"cell_type": "markdown", "source": ["# Hi"]}
        assert cell_has_output(cell) is False

    def test_code_cell_no_outputs_key_returns_false(self) -> None:
        cell = {"cell_type": "code", "execution_count": None}
        assert cell_has_output(cell) is False


class TestEstimateOutputSize:
    def test_stream_output_size(self) -> None:
        cell = {
            "outputs": [{"output_type": "stream", "text": ["line1\n", "line2\n"]}]
        }
        assert estimate_output_size(cell) == 12

    def test_display_data_size(self) -> None:
        cell = {
            "outputs": [
                {"output_type": "display_data", "data": {"text/plain": ["hello"]}}
            ]
        }
        assert estimate_output_size(cell) == 5

    def test_empty_outputs(self) -> None:
        cell = {"outputs": []}
        assert estimate_output_size(cell) == 0


class TestCheckNotebooks:
    def test_detects_output(self, notebook_with_output: Path) -> None:
        findings = check_notebooks([notebook_with_output])
        assert len(findings) == 1
        assert findings[0]["cells_with_output"] == 1
        assert findings[0]["details"][0]["cell_index"] == 0
        assert "stream" in findings[0]["details"][0]["output_types"]

    def test_clean_notebook_no_findings(self, notebook_without_output: Path) -> None:
        findings = check_notebooks([notebook_without_output])
        assert findings == []

    def test_rich_output_detected(self, notebook_with_rich_output: Path) -> None:
        findings = check_notebooks([notebook_with_rich_output])
        assert len(findings) == 1
        assert findings[0]["cells_with_output"] == 2

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        findings = check_notebooks([tmp_path / "nope.ipynb"])
        assert findings == []


class TestStripNotebook:
    def test_strips_output(self, notebook_with_output: Path) -> None:
        result = strip_notebook(notebook_with_output)
        assert result["cells_cleaned"] == 1

        # Verify file on disk is clean
        nb = json.loads(notebook_with_output.read_text())
        code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        for cell in code_cells:
            assert cell["outputs"] == []
            assert cell["execution_count"] is None

    def test_strips_rich_output(self, notebook_with_rich_output: Path) -> None:
        result = strip_notebook(notebook_with_rich_output)
        assert result["cells_cleaned"] == 2

        nb = json.loads(notebook_with_rich_output.read_text())
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                assert cell["outputs"] == []
                assert cell["execution_count"] is None

    def test_clean_notebook_unchanged(self, notebook_without_output: Path) -> None:
        original = notebook_without_output.read_text()
        result = strip_notebook(notebook_without_output)
        assert result["cells_cleaned"] == 0
        # File should not be rewritten when nothing changed
        assert notebook_without_output.read_text() == original

    def test_preserves_source(self, notebook_with_output: Path) -> None:
        result = strip_notebook(notebook_with_output)
        nb = json.loads(notebook_with_output.read_text())
        assert nb["cells"][0]["source"] == ["print('Hello, world!')"]

    def test_preserves_markdown_cells(self, notebook_with_output: Path) -> None:
        strip_notebook(notebook_with_output)
        nb = json.loads(notebook_with_output.read_text())
        md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
        assert len(md_cells) == 1
        assert md_cells[0]["source"] == ["# Title"]


class TestLoadNotebook:
    def test_loads_valid_notebook(self, notebook_with_output: Path) -> None:
        nb = load_notebook(notebook_with_output)
        assert nb is not None
        assert "cells" in nb

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.ipynb"
        bad.write_text("not json at all", encoding="utf-8")
        assert load_notebook(bad) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert load_notebook(tmp_path / "missing.ipynb") is None


class TestGetStagedNotebooks:
    def test_returns_only_ipynb_files(self) -> None:
        mock_output = "src/app.py\nnotebooks/analysis.ipynb\nREADME.md\nwork.ipynb\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_output, stderr=""
            )
            result = get_staged_notebooks()
        assert result == ["notebooks/analysis.ipynb", "work.ipynb"]

    def test_returns_empty_on_no_staged(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = get_staged_notebooks()
        assert result == []

    def test_returns_empty_on_git_error(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = get_staged_notebooks()
        assert result == []

    def test_returns_empty_when_git_not_found(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = get_staged_notebooks()
        assert result == []
