"""
test_audit_fixes.py — Tests covering all issues found and fixed in the final audit.

Covers:
1. Language consistency — all three languages for nudge card UI strings
2. KPI consistency — wallet vs leaderboard, participation rate calculation
3. Flex capacity — non-zero after optimize (pending nudges count)
4. Point preservation — optimize does NOT reset household points
5. Data provenance — every displayed metric has a documented source
6. Duplicate reward protection
7. Household isolation — one household's data does not affect another
8. Demo database isolation
"""
import pytest
from frontend.ui_strings import t, LANG_CODES, _STRINGS


# ── 1. Language consistency ───────────────────────────────────────────────────

class TestLanguageConsistency:
    """Verify that all three languages produce non-empty, distinct strings."""

    @pytest.mark.parametrize("key", [
        "nudge_pending_badge",
        "nudge_accepted_badge",
        "nudge_skipped_badge",
        "nudge_usually_label",
        "nudge_recommended_label",
        "nudge_shift_load_label",
        "nudge_est_savings_label",
        "nudge_earn_points_label",
        "nudge_btn_accept",
        "nudge_btn_skip",
        "resident_page_title",
        "resident_page_subtitle",
        "resident_wallet_heading",
        "resident_smart_actions_heading",
        "resident_no_nudges_msg",
        "sidebar_scenario_explorer_heading",
        "sidebar_scenario_explorer_desc",
    ])
    def test_all_three_languages_non_empty(self, key):
        """Every translatable UI key must return a non-empty string in all 3 languages."""
        for lang in LANG_CODES:
            result = t(key, lang)
            assert result, f"t('{key}', '{lang}') returned empty string"
            assert not result.startswith("["), f"t('{key}', '{lang}') returned missing-key marker: {result}"

    def test_english_does_not_contain_devanagari(self):
        """When English is selected, no Devanagari characters should appear."""
        devanagari_range = ("\u0900", "\u097F")
        for key in _STRINGS:
            en_text = t(key, "en")
            for ch in en_text:
                assert not (devanagari_range[0] <= ch <= devanagari_range[1]), \
                    f"English string for key '{key}' contains Devanagari: '{en_text}'"

    def test_english_does_not_contain_telugu(self):
        """When English is selected, no Telugu characters should appear."""
        telugu_range = ("\u0C00", "\u0C7F")
        for key in _STRINGS:
            en_text = t(key, "en")
            for ch in en_text:
                assert not (telugu_range[0] <= ch <= telugu_range[1]), \
                    f"English string for key '{key}' contains Telugu: '{en_text}'"

    def test_hindi_contains_devanagari(self):
        """Hindi translations must contain Devanagari script."""
        devanagari_keys = [
            "nudge_pending_badge", "nudge_accepted_badge", "nudge_usually_label",
            "resident_page_title", "sidebar_scenario_explorer_desc",
        ]
        for key in devanagari_keys:
            hi_text = t(key, "hi")
            has_dev = any("\u0900" <= ch <= "\u097F" for ch in hi_text)
            assert has_dev, f"Hindi text for '{key}' lacks Devanagari: '{hi_text}'"

    def test_telugu_contains_telugu_script(self):
        """Telugu translations must contain Telugu script."""
        telugu_keys = [
            "nudge_pending_badge", "nudge_accepted_badge", "nudge_usually_label",
            "resident_page_title", "sidebar_scenario_explorer_desc",
        ]
        for key in telugu_keys:
            te_text = t(key, "te")
            has_tel = any("\u0C00" <= ch <= "\u0C7F" for ch in te_text)
            assert has_tel, f"Telugu text for '{key}' lacks Telugu script: '{te_text}'"

    def test_unknown_lang_falls_back_to_english(self):
        """An unsupported language code must return the English string, not a missing-key marker."""
        en_text = t("nudge_pending_badge", "en")
        fr_text = t("nudge_pending_badge", "fr")
        assert fr_text == en_text
        assert not fr_text.startswith("[")

    def test_missing_key_returns_marker(self):
        """A completely unknown key returns a clearly-visible marker, not empty string."""
        result = t("this_key_does_not_exist", "en")
        assert result == "[this_key_does_not_exist]"

    def test_nudge_text_three_languages_backend(self):
        """Backend nudge_text() produces correct script in all three languages."""
        from backend.translations import nudge_text, APPLIANCE_NAMES
        for appliance in APPLIANCE_NAMES:
            en = nudge_text(appliance, 76, 44, 10, 3.0, lang="en")
            hi = nudge_text(appliance, 76, 44, 10, 3.0, lang="hi")
            te = nudge_text(appliance, 76, 44, 10, 3.0, lang="te")
            assert en
            assert any("\u0900" <= ch <= "\u097F" for ch in hi), \
                f"Hindi nudge for '{appliance}' lacks Devanagari: '{hi}'"
            assert any("\u0C00" <= ch <= "\u0C7F" for ch in te), \
                f"Telugu nudge for '{appliance}' lacks Telugu script: '{te}'"


# ── 2. KPI consistency ────────────────────────────────────────────────────────

class TestKPIConsistency:
    """Verify wallet/leaderboard/participation/flex-capacity consistency."""

    def test_optimize_does_not_reset_household_points(self, fresh_client):
        """CRITICAL: Running optimize must NOT zero out household points."""
        fresh_client.post("/optimize")
        # Accept a nudge → points added
        households = fresh_client.get("/households").json()
        target_nudge = None
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending:
                target_nudge = pending[0]
                break
        assert target_nudge is not None
        r1 = fresh_client.post(f"/nudges/{target_nudge['id']}/respond", json={"accept": True}).json()
        assert r1["points_added"] > 0
        pts_after_accept = r1["household_points"]

        # Now re-run optimize — points must survive
        fresh_client.post("/optimize")
        hh_id = target_nudge["household_id"]
        hh_data = [h for h in fresh_client.get("/households").json() if h["id"] == hh_id]
        assert hh_data, f"Household {hh_id} not found"
        pts_after_reoptimize = hh_data[0]["points"]
        assert pts_after_reoptimize == pts_after_accept, (
            f"Optimize zeroed household points: expected {pts_after_accept}, "
            f"got {pts_after_reoptimize}"
        )

    def test_leaderboard_reflects_accepted_nudges(self, fresh_client):
        """Leaderboard points must reflect accepted nudges, not zeros."""
        fresh_client.post("/optimize")
        households = fresh_client.get("/households").json()
        target_nudge = None
        target_hh_id = None
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending:
                target_nudge = pending[0]
                target_hh_id = hh["id"]
                break

        assert target_nudge is not None
        r = fresh_client.post(f"/nudges/{target_nudge['id']}/respond", json={"accept": True}).json()
        expected_pts = r["household_points"]
        assert expected_pts > 0

        board = fresh_client.get("/leaderboard").json()["leaderboard"]
        hh_board = [row for row in board if str(row["household_id"]) == str(target_hh_id)]
        assert hh_board, f"Household {target_hh_id} not on leaderboard"
        assert hh_board[0]["points"] == expected_pts, (
            f"Leaderboard points ({hh_board[0]['points']}) != wallet ({expected_pts})"
        )

    def test_participation_rate_consistent_with_active_homes(self, fresh_client):
        """participants field must be consistent with total_households for rate calculation."""
        fresh_client.post("/optimize")
        kpis = fresh_client.get("/kpis").json()
        participants = kpis["participants"]
        total = kpis["total_households"]
        assert total > 0, "total_households must be positive"
        assert 0 <= participants <= total, (
            f"participants ({participants}) out of range [0, {total}]"
        )
        # Before any nudges are accepted: participants must be 0
        assert participants == 0, (
            f"Fresh optimize with no accepts: expected participants=0, got {participants}"
        )

    def test_participation_rate_updates_after_acceptance(self, fresh_client):
        """After accepting a nudge, participants count must increase."""
        fresh_client.post("/optimize")
        kpis_before = fresh_client.get("/kpis").json()
        assert kpis_before["participants"] == 0

        households = fresh_client.get("/households").json()
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending:
                fresh_client.post(f"/nudges/{pending[0]['id']}/respond", json={"accept": True})
                break

        kpis_after = fresh_client.get("/kpis").json()
        assert kpis_after["participants"] == 1, (
            f"Expected 1 participant after one acceptance, got {kpis_after['participants']}"
        )

    def test_flex_capacity_nonzero_after_optimize(self, fresh_client):
        """Flex capacity must be non-zero after optimize (pending nudges represent available DR)."""
        fresh_client.post("/optimize")
        flex = fresh_client.get("/flex-capacity").json()
        assert flex["available_kw"] > 0, (
            "Flex capacity reported as 0 kW after optimize — pending nudges should count"
        )
        assert flex["households_available"] > 0

    def test_flex_capacity_decreases_when_nudges_accepted(self, fresh_client):
        """Accepting nudges should reduce (or equal) flex capacity."""
        fresh_client.post("/optimize")
        flex_before = fresh_client.get("/flex-capacity").json()["available_kw"]

        households = fresh_client.get("/households").json()
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending:
                fresh_client.post(f"/nudges/{pending[0]['id']}/respond", json={"accept": True})
                break

        flex_after = fresh_client.get("/flex-capacity").json()["available_kw"]
        assert flex_after <= flex_before, (
            f"Flex capacity increased after acceptance: {flex_before} → {flex_after}"
        )

    def test_kpi_co2_formula(self, client):
        """CO2 must equal kwh_shifted * CO2_PER_KWH (default 0.71 kg/kWh)."""
        client.post("/optimize")
        kpis = client.get("/kpis").json()
        expected_co2 = round(kpis["kwh_shifted"] * 0.71, 2)
        assert abs(kpis["co2_kg"] - expected_co2) < 0.01, (
            f"CO2 formula mismatch: co2_kg={kpis['co2_kg']}, "
            f"expected {expected_co2} = kwh_shifted ({kpis['kwh_shifted']}) × 0.71"
        )

    def test_kpi_peak_reduction_formula(self, client):
        """peak_reduction_pct must be computed from actual before/after peaks."""
        client.post("/optimize")
        kpis = client.get("/kpis").json()
        pb, pa = kpis["peak_before_kw"], kpis["peak_after_kw"]
        if pb > 0:
            expected_pct = round(100 * (pb - pa) / pb, 1)
            assert abs(kpis["peak_reduction_pct"] - expected_pct) < 0.1, (
                f"peak_reduction_pct formula: got {kpis['peak_reduction_pct']}, "
                f"expected {expected_pct}"
            )


# ── 3. Household isolation ────────────────────────────────────────────────────

class TestHouseholdIsolation:
    """Verify that accepting nudges for one household does not affect another."""

    def test_accepting_nudge_does_not_affect_other_household(self, fresh_client):
        fresh_client.post("/optimize")
        households = fresh_client.get("/households").json()

        hh_a_id = hh_a_nudge = hh_b_id = None
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending and hh_a_id is None:
                hh_a_id = hh["id"]
                hh_a_nudge = pending[0]
            elif hh_a_id and hh_b_id is None and hh["id"] != hh_a_id:
                hh_b_id = hh["id"]
                break

        if hh_a_id is None or hh_b_id is None:
            pytest.skip("Need at least 2 households with nudges")

        pts_b_before = next(h["points"] for h in households if h["id"] == hh_b_id)

        # Accept for household A
        fresh_client.post(f"/nudges/{hh_a_nudge['id']}/respond", json={"accept": True})

        # Household B points must be unchanged
        hh_b_after = [h for h in fresh_client.get("/households").json() if h["id"] == hh_b_id]
        pts_b_after = hh_b_after[0]["points"]
        assert pts_b_after == pts_b_before, (
            f"HH B points changed after HH A action: {pts_b_before} → {pts_b_after}"
        )


# ── 4. Duplicate reward protection ───────────────────────────────────────────

class TestDuplicateRewardProtection:
    def test_double_accept_does_not_double_award(self, fresh_client):
        fresh_client.post("/optimize")
        households = fresh_client.get("/households").json()
        target_nudge = None
        for hh in households:
            nd = fresh_client.get(f"/nudges/{hh['id']}").json()
            pending = [n for n in nd.get("nudges", []) if n["status"] == "pending"]
            if pending:
                target_nudge = pending[0]
                break

        assert target_nudge is not None
        nid = target_nudge["id"]

        r1 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True}).json()
        assert r1["points_added"] > 0
        total1 = r1["household_points"]

        r2 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True}).json()
        assert r2["points_added"] == 0, "Second accept awarded points again!"
        assert r2["household_points"] == total1


# ── 5. Data provenance ────────────────────────────────────────────────────────

class TestDataProvenance:
    def test_forecast_exposes_data_source_field(self, client):
        """Every forecast slot must carry a data_source field ('mock' or 'model')."""
        slots = client.get("/forecast").json()["slots"]
        for slot in slots:
            assert "data_source" in slot, "Forecast slot missing data_source field"
            assert slot["data_source"] in ("mock", "model"), \
                f"Invalid data_source value: {slot['data_source']}"

    def test_health_exposes_mock_data_flag(self, client):
        """Health endpoint must expose mock_data flag for provenance disclosure."""
        health = client.get("/health").json()
        assert "mock_data" in health
        assert isinstance(health["mock_data"], bool)

    def test_three_scenarios_use_distinct_dates(self, client):
        """Each scenario must map to a distinct forecast date."""
        sunny = client.get("/forecast?scenario=sunny").json()["date"]
        cloudy = client.get("/forecast?scenario=cloudy").json()["date"]
        heatwave = client.get("/forecast?scenario=heatwave").json()["date"]
        assert sunny != cloudy != heatwave
        assert sunny != heatwave

    def test_scenario_data_is_physically_distinct(self, client):
        """Sunny, cloudy, heatwave forecasts must use different demand/solar curves."""
        s = client.get("/forecast?scenario=sunny").json()["slots"]
        c = client.get("/forecast?scenario=cloudy").json()["slots"]
        h = client.get("/forecast?scenario=heatwave").json()["slots"]
        # Solar differs between sunny and cloudy
        solar_s = max(slot["solar_kw"] for slot in s)
        solar_c = max(slot["solar_kw"] for slot in c)
        assert solar_s > solar_c, "Sunny solar must exceed cloudy solar"
        # Demand differs between cloudy and heatwave
        demand_h = max(slot["demand_kw"] for slot in h)
        demand_c = max(slot["demand_kw"] for slot in c)
        assert demand_h > demand_c, "Heatwave demand must exceed cloudy demand"


# ── 6. Demo database isolation ───────────────────────────────────────────────

class TestDemoDatabaseIsolation:
    def test_demo_db_does_not_touch_test_db(self):
        """Demo runner uses its own isolated DB and cleans up after itself."""
        import os
        from pathlib import Path
        from scripts.run_demo import run_demo, DEMO_DB_PATH

        test_db = os.environ.get("DB_PATH", "data/test_powerpool.db")
        prod_db = "data/powerpool.db"

        # Verify demo runner doesn't exist at start
        if DEMO_DB_PATH.exists():
            DEMO_DB_PATH.unlink()

        result = run_demo(interactive=False, target_scenario="sunny")
        assert result is True

        # Demo DB should be cleaned up
        assert not DEMO_DB_PATH.exists(), "Demo DB was not cleaned up"

        # Test DB and production DB must not be demo DB path
        assert str(DEMO_DB_PATH) != test_db
        assert str(DEMO_DB_PATH) != prod_db
