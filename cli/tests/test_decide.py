"""Tests for keel decide id allocation and detail-file collision safety."""

import json

from click.testing import CliRunner

from keel_cli.main import cli


def _decide(project, *args):
    return CliRunner().invoke(cli, ["--project", str(project), "decide", *args])


def test_first_decision_allocates_001(tmp_path):
    result = _decide(tmp_path, "friction", "first decision")
    assert result.exit_code == 0
    assert "001-first-decision" in result.output
    assert (tmp_path / ".keel/decisions/001-first-decision.json").exists()


def test_refuses_to_clobber_existing_detail_file(tmp_path):
    # Ledger has only a non-numeric id, so next_id resets to 001. A hand-edited
    # 001-*.json detail file must not be overwritten.
    keel_dir = tmp_path / ".keel"
    decisions_dir = keel_dir / "decisions"
    decisions_dir.mkdir(parents=True)
    (keel_dir / "ledger.json").write_text(json.dumps([{"id": "inception", "type": "inception"}]), encoding="utf-8")
    detail = decisions_dir / "001-first-decision.json"
    detail.write_text(json.dumps({"id": "001-first-decision", "details": {"hand": "edited"}}), encoding="utf-8")

    result = _decide(tmp_path, "friction", "first decision")
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.output
    # The hand-edited file is untouched.
    assert json.loads(detail.read_text())["details"] == {"hand": "edited"}
