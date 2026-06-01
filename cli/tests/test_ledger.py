"""Unit tests for keel_cli.ledger access and id allocation."""

import json

import pytest

from keel_cli.ledger import load_ledger, next_id, require_ledger


class TestLoadLedger:
    def test_absent_returns_empty(self, tmp_path):
        assert load_ledger(tmp_path) == []

    def test_present_returns_entries(self, tmp_path):
        (tmp_path / "ledger.json").write_text(json.dumps([{"id": "001-x"}]), encoding="utf-8")
        assert load_ledger(tmp_path) == [{"id": "001-x"}]


class TestRequireLedger:
    def test_absent_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            require_ledger(tmp_path)
        assert exc.value.code == 1

    def test_present_returns_entries(self, tmp_path):
        (tmp_path / "ledger.json").write_text(json.dumps([{"id": "001-x"}]), encoding="utf-8")
        assert require_ledger(tmp_path) == [{"id": "001-x"}]


class TestNextId:
    def test_empty_ledger_starts_at_one(self):
        assert next_id([], "slug") == "001-slug"

    def test_increments_max_numeric_prefix(self):
        ledger = [{"id": "001-a"}, {"id": "003-c"}, {"id": "002-b"}]
        assert next_id(ledger, "d") == "004-d"

    def test_skips_non_numeric_and_empty_ids(self):
        # Malformed/empty ids must not crash and must not be counted.
        ledger = [{"id": ""}, {"id": "inception"}, {"id": "002-b"}, {}]
        assert next_id(ledger, "d") == "003-d"

    def test_no_numeric_ids_resets_to_one(self):
        # When no numeric ids exist, allocation resets to 001 (the collision
        # the decide command guards against before writing).
        ledger = [{"id": "inception"}]
        assert next_id(ledger, "d") == "001-d"
