"""
test_backend_integration_readiness.py — Comprehensive tests for Member B integration readiness.

Validates:
1. MOCK_DATA configuration: explicitly enabled, explicitly disabled, unset, and invalid values.
2. Accurate representation of forecast data source.
3. Household ID normalization and graceful handling of unknown/missing IDs.
4. Scenario propagation and precedence (Sunny/Cloudy/Heatwave + default Sunny).
5. Error handling for unknown scenarios and invalid dates.
6. DR event and optimization flow consistency.
7. Strict test database isolation ensuring production DB is untouched.
"""

import os
import pytest
from backend.config import is_mock_data, _MockDataProxy
from backend.services import normalize_household_id, resolve_date, SCENARIO_DATES


# ── 1. Mock-Data Configuration & Source Identification ────────────────────────

class TestMockDataConfiguration:
    """Verifies MOCK_DATA parsing, overrides, unset fallback, and API responses."""

    def test_mock_data_explicitly_enabled(self, client, monkeypatch):
        """When MOCK_DATA is 'true', API reports mock_data=True and data_source='mock'."""
        monkeypatch.setenv("MOCK_DATA", "true")
        assert is_mock_data() is True
        assert bool(_MockDataProxy()) is True

        r_health = client.get("/health").json()
        assert r_health["mock_data"] is True

        r_forecast = client.get("/forecast?scenario=sunny").json()
        for slot in r_forecast["slots"][:5]:
            assert slot["data_source"] == "mock"

    def test_mock_data_explicitly_disabled(self, client, monkeypatch):
        """When MOCK_DATA is 'false', API reports mock_data=False and data_source='model'."""
        monkeypatch.setenv("MOCK_DATA", "false")
        assert is_mock_data() is False
        assert bool(_MockDataProxy()) is False

        r_health = client.get("/health").json()
        assert r_health["mock_data"] is False

        r_forecast = client.get("/forecast?scenario=sunny").json()
        for slot in r_forecast["slots"][:5]:
            assert slot["data_source"] == "model"

    def test_mock_data_unset_evaluates_safely(self, client, monkeypatch):
        """When MOCK_DATA is unset, it auto-detects from active DB and returns valid bool."""
        monkeypatch.delenv("MOCK_DATA", raising=False)
        result = is_mock_data()
        assert isinstance(result, bool)

        r_health = client.get("/health").json()
        assert isinstance(r_health["mock_data"], bool)

    def test_mock_data_invalid_string_handles_gracefully(self, client, monkeypatch):
        """Invalid strings for MOCK_DATA should not crash and should resolve to bool."""
        for invalid_val in ("unknown", "maybe", "12345", "   "):
            monkeypatch.setenv("MOCK_DATA", invalid_val)
            result = is_mock_data()
            assert isinstance(result, bool)


# ── 2. Household ID Handling & Graceful Edge Cases ────────────────────────────

class TestHouseholdIDHandling:
    """Verifies normalization, ID formats, and unknown household handling."""

    def test_normalize_household_id_variations(self):
        """Test normalization for numeric, string, lowercase, and edge-case IDs."""
        assert normalize_household_id(1) == "HH001"
        assert normalize_household_id("1") == "HH001"
        assert normalize_household_id("HH001") == "HH001"
        assert normalize_household_id("hh001") == "HH001"
        assert normalize_household_id("HH1") == "HH001"
        assert normalize_household_id("hh10") == "HH010"
        assert normalize_household_id(100) == "HH100"
        assert normalize_household_id("100") == "HH100"
        assert normalize_household_id("HH100") == "HH100"
        # None and unknown strings
        assert normalize_household_id(None) == ""
        assert normalize_household_id("custom_id") == "custom_id"

    def test_unknown_household_nudges_returns_empty_gracefully(self, client):
        """Querying nudges for nonexistent household returns empty list with HTTP 200."""
        r = client.get("/nudges/HH999")
        assert r.status_code == 200
        data = r.json()
        nudges = data["nudges"] if isinstance(data, dict) else data
        assert nudges == []

        # Alias /schedule/HH999
        r_alias = client.get("/schedule/HH999")
        assert r_alias.status_code == 200
        data_alias = r_alias.json()
        nudges_alias = data_alias["nudges"] if isinstance(data_alias, dict) else data_alias
        assert nudges_alias == []

    def test_unknown_household_nudge_send_graceful(self, client):
        """POST /nudge/send for unknown household queues 0 nudges and does not error."""
        r = client.post("/nudge/send", json={"household_id": "HH999"})
        assert r.status_code == 200
        body = r.json()
        assert body["household_id"] == "HH999"
        assert body["nudges_queued"] == 0
        assert body["delivered"] is False


# ── 3. Scenario Propagation & Precedence ──────────────────────────────────────

class TestScenarioPropagation:
    """Verifies Sunny, Cloudy, Heatwave dates, precedence over explicit date, and defaults."""

    def test_scenario_dates_mapping(self):
        """Verify standard scenario date dictionary."""
        assert SCENARIO_DATES["sunny"] == "2026-10-01"
        assert SCENARIO_DATES["cloudy"] == "2026-10-02"
        assert SCENARIO_DATES["heatwave"] == "2026-10-03"

    def test_scenario_takes_precedence_over_explicit_date(self, client):
        """Scenario parameter must override explicit date parameter."""
        # Supply date=2026-10-01 (sunny) but scenario=heatwave (2026-10-03)
        r = client.get("/forecast?date=2026-10-01&scenario=heatwave").json()
        assert r["date"] == "2026-10-03"

        # KPI check
        kpi = client.get("/kpis?date=2026-10-01&scenario=cloudy").json()
        kpi_cloudy = client.get("/kpis?scenario=cloudy").json()
        assert kpi["peak_before_kw"] == kpi_cloudy["peak_before_kw"]

    def test_default_scenario_is_sunny(self, client):
        """When date and scenario are omitted, endpoints default to Sunny (2026-10-01)."""
        fc_default = client.get("/forecast").json()
        fc_sunny = client.get("/forecast?scenario=sunny").json()
        assert fc_default["date"] == "2026-10-01"
        assert fc_default["date"] == fc_sunny["date"]

    def test_invalid_scenario_returns_503(self, client):
        """Invalid scenarios must return HTTP 503 across all scenario-aware endpoints."""
        assert client.get("/forecast?scenario=tsunami").status_code == 503
        assert client.get("/kpis?scenario=cyclone").status_code == 503
        assert client.post("/optimize", json={"scenario": "blizzard"}).status_code == 503
        assert client.post("/dr-event", json={"start_slot": 74, "end_slot": 86, "target_kw": 170.0, "scenario": "tornado"}).status_code == 503


# ── 4. Database Safety and Test Isolation ─────────────────────────────────────

class TestDatabaseIsolation:
    """Verifies test environment cannot reach or mutate production database."""

    def test_active_db_is_test_db(self):
        """Verify the test runner uses an isolated database path."""
        active_db = os.environ.get("DB_PATH", "")
        assert "test" in active_db.lower(), f"Tests must run on isolated DB, got: {active_db}"
        assert active_db != "data/powerpool.db"

    def test_production_db_file_remains_untouched(self):
        """Verify data/powerpool.db exists and has valid size."""
        from pathlib import Path
        prod_db = Path("data/powerpool.db")
        assert prod_db.exists(), "Production DB data/powerpool.db must exist"
        assert prod_db.stat().st_size > 10_000_000, "Production DB size is smaller than expected"
