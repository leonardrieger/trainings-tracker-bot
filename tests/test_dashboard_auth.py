import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("ALLOWED_TELEGRAM_USER_ID", "42")

from fastapi.testclient import TestClient

from app.config import TRAINING_PLAN, TRAINING_PLAN_SHORT
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
    ), patch(
        "app.main.db.get_training_plan", return_value=(TRAINING_PLAN, TRAINING_PLAN_SHORT)
    ), patch("app.main.db.get_weight_change_in_range", return_value=None), patch(
        "app.main.db.get_last_sets", return_value=[]
    ):
        r = client.get("/dashboard?token=richtig")
    assert r.status_code == 200
    assert "Bankdrücken" in r.text
    assert "Tag A" in r.text
    assert "Noch keine Gewichtsdaten" in r.text


def test_dashboard_bei_db_fehler_freundliche_fehlerseite_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.get_exercise_summary", side_effect=Exception("supabase down")):
        r = client.get("/dashboard?token=richtig")
    assert r.status_code == 503
    assert "Kurzer Hänger" in r.text


def test_dashboard_chart_ohne_token_401():
    r = client.get("/dashboard/chart.png?exercise=Bankdrücken")
    assert r.status_code == 401


def test_dashboard_chart_mit_token_aber_keine_daten_404(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.get_history", return_value=[]):
        r = client.get("/dashboard/chart.png?exercise=Bankdrücken&token=richtig")
    assert r.status_code == 404


def test_dashboard_chart_bei_db_fehler_503_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.get_history", side_effect=Exception("supabase down")):
        r = client.get("/dashboard/chart.png?exercise=Bankdrücken&token=richtig")
    assert r.status_code == 503


def test_dashboard_log_ohne_token_401():
    r = client.post("/dashboard/log", data={"text": "3x8 80kg Bankdrücken"})
    assert r.status_code == 401


def test_dashboard_log_erkannter_eintrag_wird_gespeichert(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.insert_log") as insert, patch(
        "app.main.db.get_max_weight", return_value=None
    ):
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


def test_dashboard_log_bei_db_fehler_redirect_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.insert_log", side_effect=Exception("supabase down")), patch(
        "app.main.db.get_max_weight", return_value=None
    ):
        r = client.post(
            "/dashboard/log?token=richtig",
            data={"text": "3x8 80kg Bankdrücken"},
            follow_redirects=False,
        )
    assert r.status_code == 303
    assert "H%C3%A4nger" in r.headers["location"] or "Hänger" in r.headers["location"]


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


def test_dashboard_undo_bei_db_fehler_redirect_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.delete_last_entry", side_effect=Exception("supabase down")):
        r = client.post("/dashboard/undo?token=richtig", follow_redirects=False)
    assert r.status_code == 303
    assert "H%C3%A4nger" in r.headers["location"] or "Hänger" in r.headers["location"]


def _plan_form_data(**overrides) -> dict:
    data = {}
    for d in range(7):
        data[f"long_{d}"] = f"Langform {d}"
        data[f"short_{d}"] = f"Kurz{d}"
    data.update(overrides)
    return data


def test_dashboard_plan_ohne_token_401():
    r = client.post("/dashboard/plan", data=_plan_form_data())
    assert r.status_code == 401


def test_dashboard_plan_speichert_gueltigen_plan(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.set_training_plan") as set_plan:
        r = client.post(
            "/dashboard/plan?token=richtig", data=_plan_form_data(), follow_redirects=False
        )
    assert r.status_code == 303
    set_plan.assert_called_once()
    long_plan, short_plan = set_plan.call_args.args
    assert long_plan[0] == "Langform 0"
    assert short_plan[3] == "Kurz3"
    assert "view=plan" in r.headers["location"]
    assert "gespeichert" in r.headers["location"]


def test_dashboard_plan_leerer_langform_text_wird_abgelehnt(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.set_training_plan") as set_plan:
        r = client.post(
            "/dashboard/plan?token=richtig",
            data=_plan_form_data(long_3="   "),
            follow_redirects=False,
        )
    assert r.status_code == 303
    set_plan.assert_not_called()
    assert "view=plan" in r.headers["location"]


def test_dashboard_plan_leere_kurzform_faellt_auf_langform_zurueck(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.set_training_plan") as set_plan:
        client.post(
            "/dashboard/plan?token=richtig",
            data=_plan_form_data(short_5=""),
            follow_redirects=False,
        )
    _, short_plan = set_plan.call_args.args
    assert short_plan[5] == "Langform 5"


def test_dashboard_plan_bei_db_fehler_redirect_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.set_training_plan", side_effect=Exception("supabase down")):
        r = client.post(
            "/dashboard/plan?token=richtig", data=_plan_form_data(), follow_redirects=False
        )
    assert r.status_code == 303
    assert "view=plan" in r.headers["location"]
    assert "H%C3%A4nger" in r.headers["location"] or "Hänger" in r.headers["location"]


def test_dashboard_plan_reset_ohne_token_401():
    r = client.post("/dashboard/plan/reset")
    assert r.status_code == 401


def test_dashboard_plan_reset_setzt_zurueck(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.reset_training_plan") as reset_plan:
        r = client.post("/dashboard/plan/reset?token=richtig", follow_redirects=False)
    assert r.status_code == 303
    reset_plan.assert_called_once()
    assert "view=plan" in r.headers["location"]


def test_dashboard_plan_reset_bei_db_fehler_redirect_statt_500(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "richtig")
    with patch("app.main.db.reset_training_plan", side_effect=Exception("supabase down")):
        r = client.post("/dashboard/plan/reset?token=richtig", follow_redirects=False)
    assert r.status_code == 303
    assert "view=plan" in r.headers["location"]
    assert "H%C3%A4nger" in r.headers["location"] or "Hänger" in r.headers["location"]


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
