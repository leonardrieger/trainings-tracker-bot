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
    summary = {"Bankdrücken": {"count": 2, "last": "2026-07-14T07:00:00"}}
    with patch("app.main.db.get_exercise_summary", return_value=summary), patch(
        "app.main.db.get_recent_activity", return_value=[]
    ), patch("app.main.db.get_body_weight_history", return_value=[]), patch(
        "app.main.db.get_training_days_count", return_value=3
    ), patch("app.main.db.get_program_start_date", return_value=None), patch(
        "app.main.db.get_workout_dates_in_range", return_value=set()
    ):
        r = client.get("/dashboard?token=richtig")
    assert r.status_code == 200
    assert "Bankdrücken" in r.text
    assert "Tag A" in r.text
    assert "Noch keine Gewichtsdaten" in r.text


def test_dashboard_chart_ohne_token_401():
    r = client.get("/dashboard/chart.png?exercise=Bankdrücken")
    assert r.status_code == 401


def test_dashboard_chart_mit_token_aber_keine_daten_404(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.get_history", return_value=[]):
        r = client.get("/dashboard/chart.png?exercise=Bankdrücken&token=richtig")
    assert r.status_code == 404


def test_dashboard_log_ohne_token_401():
    r = client.post("/dashboard/log", data={"text": "3x8 80kg Bankdrücken"})
    assert r.status_code == 401


def test_dashboard_log_erkannter_eintrag_wird_gespeichert(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.insert_log") as insert:
        r = client.post(
            "/dashboard/log?token=richtig",
            data={"text": "3x8 80kg Bankdrücken"},
            follow_redirects=False,
        )
    assert r.status_code == 303
    insert.assert_called_once()
    assert "/dashboard?token=richtig&msg=" in r.headers["location"]


def test_dashboard_log_nicht_erkannter_text_speichert_nicht(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.insert_log") as insert:
        r = client.post(
            "/dashboard/log?token=richtig",
            data={"text": "Was steht heute an?"},
            follow_redirects=False,
        )
    assert r.status_code == 303
    insert.assert_not_called()
    assert "Nicht+erkannt" in r.headers["location"] or "Nicht%20erkannt" in r.headers["location"]


def test_dashboard_undo_ohne_token_401():
    r = client.post("/dashboard/undo")
    assert r.status_code == 401


def test_dashboard_undo_mit_token(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    deleted = {"type": "workout", "exercise": "Bankdrücken", "logged_at": "2026-07-14T10:00:00"}
    with patch("app.main.db.delete_last_entry", return_value=deleted) as delete:
        r = client.post("/dashboard/undo?token=richtig", follow_redirects=False)
    assert r.status_code == 303
    delete.assert_called_once()
    assert "Gel%C3%B6scht" in r.headers["location"] or "Gelöscht" in r.headers["location"]


def test_manifest_ohne_token_401():
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 401


def test_manifest_mit_token_200(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    r = client.get("/manifest.webmanifest?token=richtig")
    assert r.status_code == 200
    body = r.json()
    assert body["display"] == "standalone"
    assert body["start_url"] == "/dashboard?token=richtig"


def test_service_worker_erreichbar():
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "serviceWorker" not in r.text  # sw.js selbst registriert sich nicht
    assert "addEventListener" in r.text
