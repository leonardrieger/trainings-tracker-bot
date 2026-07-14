import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("ALLOWED_TELEGRAM_USER_ID", "42")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_ohne_token_401():
    r = client.get("/dashboard")
    assert r.status_code == 401


def test_dashboard_mit_falschem_token_401(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    r = client.get("/dashboard?token=falsch")
    assert r.status_code == 401


def test_dashboard_mit_richtigem_token_200(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.list_exercises", return_value=["Bankdrücken"]), patch(
        "app.main.db.get_recent_activity", return_value=[]
    ):
        r = client.get("/dashboard?token=richtig")
    assert r.status_code == 200
    assert "Bankdrücken" in r.text


def test_dashboard_chart_ohne_token_401():
    r = client.get("/dashboard/chart.png?exercise=Bankdrücken")
    assert r.status_code == 401


def test_dashboard_chart_mit_token_aber_keine_daten_404(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.get_history", return_value=[]):
        r = client.get("/dashboard/chart.png?exercise=Bankdrücken&token=richtig")
    assert r.status_code == 404
