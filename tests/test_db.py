import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db
from app.config import TRAINING_PLAN, TRAINING_PLAN_SHORT
from app.exercises import CARDIO_EXERCISES, EXERCISE_ALIASES, PLAN_SECTIONS, SESSION_ONLY_EXERCISES

# Vor jedem Test patcht die Autouse-Fixture in conftest.py app.main.db.get_exercise_catalog
# (dasselbe db-Modulobjekt wie hier) auf die statischen Defaults, damit Tests, die über
# app.main laufen, das nicht einzeln mocken müssen. Für Tests, die hier die echte
# Implementierung prüfen wollen, muss die Original-Funktion daher schon beim Modul-Import
# (also vor jeder Fixture) gesichert werden.
_real_get_exercise_catalog = db.get_exercise_catalog


def test_merge_training_plan_ohne_override_liefert_config_defaults():
    long_plan, short_plan = db._merge_training_plan(None)
    assert long_plan == TRAINING_PLAN
    assert short_plan == TRAINING_PLAN_SHORT


def test_merge_training_plan_mit_vollstaendigem_override():
    raw = json.dumps({str(d): {"long": f"Tag {d} lang", "short": f"T{d}"} for d in range(7)})
    long_plan, short_plan = db._merge_training_plan(raw)
    assert long_plan[0] == "Tag 0 lang"
    assert short_plan[0] == "T0"
    assert long_plan[6] == "Tag 6 lang"
    assert short_plan[6] == "T6"


def test_merge_training_plan_mit_teilweisem_override_faellt_pro_tag_zurueck():
    raw = json.dumps({"0": {"long": "Montag neu", "short": "Mo neu"}})
    long_plan, short_plan = db._merge_training_plan(raw)
    assert long_plan[0] == "Montag neu"
    assert short_plan[0] == "Mo neu"
    assert long_plan[1] == TRAINING_PLAN[1]
    assert short_plan[1] == TRAINING_PLAN_SHORT[1]


def test_merge_training_plan_leere_kurzform_faellt_auf_langform_zurueck():
    raw = json.dumps({"2": {"long": "Mittwoch neu", "short": ""}})
    _, short_plan = db._merge_training_plan(raw)
    assert short_plan[2] == "Mittwoch neu"


def test_merge_training_plan_leere_langform_wird_ignoriert():
    raw = json.dumps({"3": {"long": "  ", "short": "Egal"}})
    long_plan, short_plan = db._merge_training_plan(raw)
    assert long_plan[3] == TRAINING_PLAN[3]
    assert short_plan[3] == TRAINING_PLAN_SHORT[3]


def test_merge_training_plan_kaputtes_json_faellt_komplett_zurueck():
    long_plan, short_plan = db._merge_training_plan("{nicht valides json")
    assert long_plan == TRAINING_PLAN
    assert short_plan == TRAINING_PLAN_SHORT


def test_merge_training_plan_liste_statt_dict_faellt_zurueck():
    long_plan, short_plan = db._merge_training_plan(json.dumps([1, 2, 3]))
    assert long_plan == TRAINING_PLAN
    assert short_plan == TRAINING_PLAN_SHORT


def test_get_training_plan_liest_ueber_get_state():
    raw = json.dumps({"0": {"long": "Custom", "short": "C"}})
    with patch("app.db.get_state", return_value=raw) as get_state:
        long_plan, short_plan = db.get_training_plan()
    get_state.assert_called_once_with(db.TRAINING_PLAN_STATE_KEY)
    assert long_plan[0] == "Custom"
    assert short_plan[0] == "C"


def test_set_training_plan_serialisiert_alle_tage():
    long_plan = {d: f"L{d}" for d in range(7)}
    short_plan = {d: f"S{d}" for d in range(7)}
    with patch("app.db.set_state") as set_state:
        db.set_training_plan(long_plan, short_plan)
    key, value = set_state.call_args.args
    assert key == db.TRAINING_PLAN_STATE_KEY
    payload = json.loads(value)
    assert len(payload) == 7
    assert payload["0"] == {"long": "L0", "short": "S0"}
    assert payload["6"] == {"long": "L6", "short": "S6"}


def test_reset_training_plan_loescht_state_key():
    with patch("app.db.delete_state") as delete_state:
        db.reset_training_plan()
    delete_state.assert_called_once_with(db.TRAINING_PLAN_STATE_KEY)


def test_delete_state_ruft_supabase_delete_auf():
    mock_client = MagicMock()
    with patch("app.db.get_client", return_value=mock_client):
        db.delete_state("training_plan")
    mock_client.table.assert_called_once_with(db.STATE_TABLE)
    mock_client.table.return_value.delete.return_value.eq.assert_called_once_with("key", "training_plan")


def _mock_last_sets_rows(rows: list[dict]) -> MagicMock:
    mock_client = MagicMock()
    chain = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value
    chain.execute.return_value.data = rows
    return mock_client


def test_get_last_sets_dedupliziert_nach_uebung_und_behaelt_neuesten():
    rows = [
        {"exercise": "Bankdrücken", "raw_text": "3x8 80kg Bankdrücken", "logged_at": "2026-07-14T10:00:00"},
        {"exercise": "Kniebeuge", "raw_text": "3x8 100kg Kniebeuge", "logged_at": "2026-07-13T10:00:00"},
        {"exercise": "Bankdrücken", "raw_text": "3x8 75kg Bankdrücken", "logged_at": "2026-07-10T10:00:00"},
        {"exercise": "Unbekannt", "raw_text": "asdf", "logged_at": "2026-07-09T10:00:00"},
    ]
    with patch("app.db.get_client", return_value=_mock_last_sets_rows(rows)):
        result = db.get_last_sets(42, limit=4)
    assert [r["exercise"] for r in result] == ["Bankdrücken", "Kniebeuge"]
    assert result[0]["raw_text"] == "3x8 80kg Bankdrücken"


def test_get_last_sets_respektiert_limit():
    rows = [
        {"exercise": f"Ex{i}", "raw_text": f"r{i}", "logged_at": f"2026-07-{i:02d}T10:00:00"}
        for i in range(1, 10)
    ]
    with patch("app.db.get_client", return_value=_mock_last_sets_rows(rows)):
        result = db.get_last_sets(42, limit=3)
    assert len(result) == 3


def _mock_max_weight_rows(rows: list[dict]) -> MagicMock:
    mock_client = MagicMock()
    chain = (
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value
        .order.return_value.limit.return_value
    )
    chain.execute.return_value.data = rows
    return mock_client


def test_get_max_weight_liefert_hoechsten_wert():
    with patch("app.db.get_client", return_value=_mock_max_weight_rows([{"weight_kg": 100}])):
        result = db.get_max_weight(42, "Bankdrücken")
    assert result == 100


def test_get_max_weight_ohne_eintraege_liefert_none():
    with patch("app.db.get_client", return_value=_mock_max_weight_rows([])):
        result = db.get_max_weight(42, "Bankdrücken")
    assert result is None


def test_update_workout_log_setzt_alle_felder():
    mock_client = MagicMock()
    with patch("app.db.get_client", return_value=mock_client):
        db.update_workout_log(
            42, 7, exercise="Bankdrücken", sets=3, reps=8, weight_kg=82.5,
            duration_min=None, distance_km=None,
        )
    mock_client.table.assert_called_once_with(db.TABLE)
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert payload == {
        "exercise": "Bankdrücken", "sets": 3, "reps": 8, "weight_kg": 82.5,
        "duration_min": None, "distance_km": None,
    }
    mock_client.table.return_value.update.return_value.eq.assert_called_once_with("telegram_user_id", 42)


def test_update_body_weight_log_nutzt_gewichts_tabelle():
    mock_client = MagicMock()
    with patch("app.db.get_client", return_value=mock_client):
        db.update_body_weight_log(42, 5, 83.2)
    mock_client.table.assert_called_once_with(db.BODY_WEIGHT_TABLE)
    assert mock_client.table.return_value.update.call_args.args[0] == {"weight_kg": 83.2}


def _mock_entry_rows(rows: list[dict]) -> MagicMock:
    mock_client = MagicMock()
    chain = mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value.data = rows
    return mock_client


def test_delete_log_entry_liefert_geloeschte_zeile():
    row = {"id": 7, "exercise": "Kniebeuge", "logged_at": "2026-07-13T07:30:00"}
    mock_client = _mock_entry_rows([row])
    with patch("app.db.get_client", return_value=mock_client):
        result = db.delete_log_entry(42, "workout", 7)
    assert result == {"type": "workout", **row}
    mock_client.table.assert_called_with(db.TABLE)
    mock_client.table.return_value.delete.assert_called_once()


def test_delete_log_entry_unbekannte_id_liefert_none_und_loescht_nicht():
    mock_client = _mock_entry_rows([])
    with patch("app.db.get_client", return_value=mock_client):
        result = db.delete_log_entry(42, "workout", 999)
    assert result is None
    mock_client.table.return_value.delete.assert_not_called()


def test_delete_log_entry_bodyweight_nutzt_gewichts_tabelle():
    row = {"id": 3, "weight_kg": 84.0, "logged_at": "2026-07-13T08:00:00"}
    mock_client = _mock_entry_rows([row])
    with patch("app.db.get_client", return_value=mock_client):
        result = db.delete_log_entry(42, "bodyweight", 3)
    assert result == {"type": "bodyweight", **row}
    mock_client.table.assert_called_with(db.BODY_WEIGHT_TABLE)


def test_get_exercise_records_aggregiert_bestwerte():
    rows = [
        {"sets": 3, "reps": 8, "weight_kg": 80},
        {"sets": 2, "reps": 10, "weight_kg": 75},
        {"sets": None, "reps": 12, "weight_kg": None},  # gewichtslos -> zählt für max_reps
        {"sets": 3, "reps": None, "weight_kg": 85},  # unvollständig -> kein Volumen
    ]
    mock_client = _mock_entry_rows(rows)
    with patch("app.db.get_client", return_value=mock_client):
        records = db.get_exercise_records(42, "Klimmzüge")
    assert records == {"max_weight": 85, "max_reps": 12, "max_volume": 1920}


def test_get_exercise_records_ohne_eintraege_alles_none():
    mock_client = _mock_entry_rows([])
    with patch("app.db.get_client", return_value=mock_client):
        records = db.get_exercise_records(42, "Klimmzüge")
    assert records == {"max_weight": None, "max_reps": None, "max_volume": None}


def test_get_all_logs_nutzen_hohes_limit_gegen_supabase_cap():
    mock_client = MagicMock()
    chain = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
    chain.limit.return_value.execute.return_value.data = []
    with patch("app.db.get_client", return_value=mock_client):
        db.get_all_workout_logs(42)
        db.get_all_body_weight_logs(42)
    for call in chain.limit.call_args_list:
        assert call.args[0] == 10000


def test_default_exercise_rows_enthaelt_alle_uebungen():
    rows = db._default_exercise_rows()
    assert {r["name"] for r in rows} == set(EXERCISE_ALIASES)


def test_default_exercise_rows_kreuzheben_ohne_sektion():
    # "Kreuzheben" (reines Deadlift) taucht in keiner PLAN_SECTIONS-Gruppe auf -
    # dieser Fall existierte schon vor der DB-Migration und muss erhalten bleiben.
    rows = {r["name"]: r for r in db._default_exercise_rows()}
    assert rows["Kreuzheben"]["section"] is None


def test_default_exercise_rows_bankdruecken_hat_tag_a_und_aliase():
    rows = {r["name"]: r for r in db._default_exercise_rows()}
    assert rows["Bankdrücken"]["section"] == "Tag A – Beine & Druck"
    assert rows["Bankdrücken"]["aliases"] == EXERCISE_ALIASES["Bankdrücken"]
    assert rows["Kickboxen"]["is_cardio"] is True
    assert rows["Kickboxen"]["is_session_only"] is True


def test_row_to_catalog_rekonstruiert_legacy_formen():
    rows = db._default_exercise_rows()
    aliases, cardio, session_only, plan_sections = db._row_to_catalog(rows)
    assert aliases == EXERCISE_ALIASES
    assert cardio == CARDIO_EXERCISES
    assert session_only == SESSION_ONLY_EXERCISES
    assert plan_sections == PLAN_SECTIONS


def test_row_to_catalog_ohne_sektion_fehlt_in_plan_sections():
    rows = [
        {"name": "Ohne Tag", "aliases": ["ohne tag"], "section": None, "is_cardio": False,
         "is_session_only": False, "sort_order": 0},
    ]
    _, _, _, plan_sections = db._row_to_catalog(rows)
    covered = {name for _, names in plan_sections for name in names}
    assert "Ohne Tag" not in covered


def test_seed_exercises_if_empty_seedet_wenn_leer():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.db.get_client", return_value=mock_client):
        db._seed_exercises_if_empty()
    mock_client.table.return_value.insert.assert_called_once()
    inserted_rows = mock_client.table.return_value.insert.call_args.args[0]
    assert len(inserted_rows) == len(EXERCISE_ALIASES)


def test_seed_exercises_if_empty_tut_nichts_wenn_schon_befuellt():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [{"id": 1}]
    with patch("app.db.get_client", return_value=mock_client):
        db._seed_exercises_if_empty()
    mock_client.table.return_value.insert.assert_not_called()


def test_get_exercise_catalog_leere_tabelle_liefert_defaults():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = []
    with patch("app.db.get_client", return_value=mock_client):
        aliases, cardio, session_only, plan_sections = _real_get_exercise_catalog()
    assert aliases == EXERCISE_ALIASES
    assert cardio == CARDIO_EXERCISES
    assert session_only == SESSION_ONLY_EXERCISES
    assert plan_sections == PLAN_SECTIONS


def test_get_exercise_catalog_mit_daten_rekonstruiert():
    custom_rows = [
        {"name": "Custom", "aliases": ["custom"], "section": None, "is_cardio": False,
         "is_session_only": False, "sort_order": 0},
    ]
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = custom_rows
    with patch("app.db.get_client", return_value=mock_client):
        aliases, *_ = _real_get_exercise_catalog()
    assert aliases == {"Custom": ["custom"]}


def _mock_client_by_table(**tables: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: tables[name]
    return mock_client


def test_add_exercise_seedet_zuerst_und_inserted_dann():
    exercises_table = MagicMock()
    exercises_table.select.return_value.execute.return_value.data = []  # _next_exercise_sort_order
    mock_client = _mock_client_by_table(**{db.EXERCISES_TABLE: exercises_table})
    with patch("app.db._seed_exercises_if_empty") as seed, patch("app.db.get_client", return_value=mock_client):
        db.add_exercise("Neue Übung", ["neue übung"], "Tag A – Beine & Druck", False, False)
    seed.assert_called_once()
    exercises_table.insert.assert_called_once()
    inserted = exercises_table.insert.call_args.args[0]
    assert inserted["name"] == "Neue Übung"
    assert inserted["section"] == "Tag A – Beine & Druck"


def test_update_exercise_kaskadiert_workout_logs_vor_katalog_bei_umbenennung():
    workout_table = MagicMock()
    exercises_table = MagicMock()
    mock_client = _mock_client_by_table(**{db.TABLE: workout_table, db.EXERCISES_TABLE: exercises_table})
    with patch("app.db._seed_exercises_if_empty"), patch("app.db.get_client", return_value=mock_client):
        db.update_exercise(42, "Bankdrücken", "Bankdrücken Neu", ["bankdrücken neu"], "Tag A – Beine & Druck", False, False)
    workout_table.update.assert_called_once_with({"exercise": "Bankdrücken Neu"})
    workout_table.update.return_value.eq.assert_any_call("telegram_user_id", 42)
    exercises_table.update.assert_called_once()
    updated = exercises_table.update.call_args.args[0]
    assert updated["name"] == "Bankdrücken Neu"


def test_update_exercise_ohne_umbenennung_kaskadiert_nicht():
    workout_table = MagicMock()
    exercises_table = MagicMock()
    mock_client = _mock_client_by_table(**{db.TABLE: workout_table, db.EXERCISES_TABLE: exercises_table})
    with patch("app.db._seed_exercises_if_empty"), patch("app.db.get_client", return_value=mock_client):
        db.update_exercise(42, "Bankdrücken", "Bankdrücken", ["bankdrücken"], None, False, False)
    workout_table.update.assert_not_called()
    exercises_table.update.assert_called_once()


def test_delete_exercise_ruehrt_workout_logs_nicht_an():
    workout_table = MagicMock()
    exercises_table = MagicMock()
    mock_client = _mock_client_by_table(**{db.TABLE: workout_table, db.EXERCISES_TABLE: exercises_table})
    with patch("app.db._seed_exercises_if_empty"), patch("app.db.get_client", return_value=mock_client):
        db.delete_exercise("Bankdrücken")
    workout_table.delete.assert_not_called()
    exercises_table.delete.assert_called_once()
