"""
backend/tests/test_phase4_demo.py — Tests for Phase 4.1 Demo Runner and Data Isolation.
"""

import os
from pathlib import Path
from scripts.run_demo import run_demo, DEMO_DB_PATH


def test_demo_runner_executes_successfully():
    """Verify run_demo executes all 12 steps cleanly and returns True."""
    success = run_demo(interactive=False, target_scenario="sunny")
    assert success is True


def test_demo_runner_heatwave_scenario():
    """Verify run_demo executes with heatwave scenario."""
    success = run_demo(interactive=False, target_scenario="heatwave")
    assert success is True


def test_demo_runner_data_isolation():
    """Verify demo runner cleans up its isolated database and does not leave residual files."""
    run_demo(interactive=False, target_scenario="sunny")
    assert not DEMO_DB_PATH.exists(), f"Demo database {DEMO_DB_PATH} was not cleaned up!"
