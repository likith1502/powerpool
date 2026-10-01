"""Regression tests for deployment/safety fixes (Oct 2026 audit)."""
import importlib
from pathlib import Path
import yaml


def test_compose_volume_does_not_shadow_source():
    c = yaml.safe_load(Path("docker-compose.yml").read_text())
    be = c["services"]["backend"]
    assert not any(v.split(":")[1].split()[0] == "/app/data" for v in be["volumes"])
    env = dict(e.split("=", 1) for e in be["environment"])
    assert env["DB_PATH"].startswith("/app/db/")
    assert env["ENABLE_DEMO_ENDPOINTS"] == "false"
    assert env["SEED_HOUSEHOLDS"] == "80"


def test_startup_seed_uses_live_config_not_stress_profile():
    src = Path("backend/main.py").read_text()
    assert "seed(n_households=100)" not in src
    from backend import config
    assert config.SEED_HOUSEHOLDS == 80


def test_demo_endpoints_blocked_when_disabled(client, monkeypatch):
    from backend import main
    monkeypatch.setattr(main, "ENABLE_DEMO_ENDPOINTS", False)
    assert client.post("/demo/reseed").status_code == 403
    assert client.post("/demo/simulate-responses").status_code == 403
