import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db
from app.config import TRAINING_PLAN, TRAINING_PLAN_SHORT


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
