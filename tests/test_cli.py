"""Tests for the CLI entry points (inspect_cmd, validate_cmd)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mava_exchange.cli import inspect_cmd, validate_cmd


# ─────────────────────────────────────────────
# validate_cmd
# ─────────────────────────────────────────────


def test_validate_cmd_valid_package(single_video_pkg, capsys):
    with patch("sys.argv", ["mediapkg-validate", str(single_video_pkg)]):
        with pytest.raises(SystemExit) as exc:
            validate_cmd()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "VALID" in out


def test_validate_cmd_strict_flag(single_video_pkg, capsys):
    with patch("sys.argv", ["mediapkg-validate", str(single_video_pkg), "--strict"]):
        with pytest.raises(SystemExit) as exc:
            validate_cmd()
    assert exc.value.code == 0


def test_validate_cmd_invalid_package(tmp_path, capsys):
    bad = tmp_path / "bad.mediapkg"
    bad.write_bytes(b"not a zip")
    with patch("sys.argv", ["mediapkg-validate", str(bad)]):
        with pytest.raises(SystemExit) as exc:
            validate_cmd()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "INVALID" in out


# ─────────────────────────────────────────────
# inspect_cmd
# ─────────────────────────────────────────────


def test_inspect_cmd_summary(single_video_pkg, capsys):
    with patch("sys.argv", ["mediapkg-inspect", str(single_video_pkg)]):
        inspect_cmd()
    out = capsys.readouterr().out
    assert "Tracks:" in out
    assert "Videos:" in out


def test_inspect_cmd_track_detail(single_video_pkg, capsys):
    with patch("sys.argv", [
        "mediapkg-inspect", str(single_video_pkg),
        "--track", "emotions",
        "--video", "v001",
        "--head", "3",
    ]):
        inspect_cmd()
    out = capsys.readouterr().out
    assert "emotions" in out
    assert "Rows:" in out


def test_inspect_cmd_corpus(corpus_pkg, capsys):
    with patch("sys.argv", ["mediapkg-inspect", str(corpus_pkg)]):
        inspect_cmd()
    out = capsys.readouterr().out
    assert "TOTAL" in out
