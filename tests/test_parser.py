import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parser import parse_message


def test_user_beispiel_bankdruecken():
    r = parse_message("Gerade habe ich 2 Sets 8 Wiederholungen 80kg Bankdrücken gemacht")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 2
    assert r.reps == 8
    assert r.weight_kg == 80
    assert r.recognized is True
    assert not r.is_cardio


def test_kniebeuge_plan_format():
    r = parse_message("Kniebeuge 4 Sätze 5 Wiederholungen 100kg")
    assert r.exercise == "Kniebeuge"
    assert r.sets == 4
    assert r.reps == 5
    assert r.weight_kg == 100


def test_kompaktform_ohne_woerter():
    r = parse_message("Bankdrücken 3x8 80kg")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 3
    assert r.reps == 8
    assert r.weight_kg == 80


def test_schraegbankdruecken_nicht_als_bankdruecken():
    r = parse_message("Schrägbankdrücken 3 Sätze 10 Wiederholungen 60kg")
    assert r.exercise == "Schrägbankdrücken"


def test_klimmzuege_ohne_gewicht():
    r = parse_message("5 Sätze Klimmzüge, 5 Wiederholungen")
    assert r.exercise == "Klimmzüge"
    assert r.sets == 5
    assert r.reps == 5
    assert r.weight_kg is None
    assert r.recognized is True


def test_kommagewicht():
    r = parse_message("Kreuzheben 3 Sätze 8 Wiederholungen 92,5kg")
    assert r.exercise == "Kreuzheben"
    assert r.weight_kg == 92.5


def test_cardio_laufen_distanz_und_dauer():
    r = parse_message("30 min 5 km Laufen, Zone 2")
    assert r.exercise == "Laufen"
    assert r.is_cardio is True
    assert r.duration_min == 30
    assert r.distance_km == 5
    assert r.recognized is True


def test_cardio_ohne_explizites_laufen_wort():
    r = parse_message("Bin heute 25 Minuten gelaufen")
    assert r.exercise == "Laufen"
    assert r.is_cardio is True
    assert r.duration_min == 25


def test_unbekannte_uebung_wird_nicht_erkannt():
    r = parse_message("Heute war ein guter Tag")
    assert r.exercise is None
    assert r.recognized is False
    assert r.raw_text == "Heute war ein guter Tag"


def test_uebung_ohne_zahlen_nicht_recognized():
    r = parse_message("Bankdrücken war heute schwer")
    assert r.exercise == "Bankdrücken"
    assert r.recognized is False


def test_confirmation_text_kraft():
    r = parse_message("Gerade habe ich 2 Sets 8 Wiederholungen 80kg Bankdrücken gemacht")
    assert r.confirmation_text() == "✅ Bankdrücken – 2 Sätze × 8 Wdh. @ 80kg"


def test_confirmation_text_cardio():
    r = parse_message("30 min 5 km Laufen")
    assert r.confirmation_text() == "✅ Laufen – 5 km – 30 min"


def test_koerpergewicht_wird_erkannt():
    r = parse_message("Gewicht heute 84,2kg")
    assert r.record_type == "bodyweight"
    assert r.weight_kg == 84.2
    assert r.exercise is None


def test_parse_message_mit_injiziertem_katalog():
    custom_aliases = {"Meine Übung": ["meine übung", "custom exercise"]}
    r = parse_message("3x8 50kg Custom Exercise", aliases=custom_aliases, cardio_exercises=set())
    assert r.exercise == "Meine Übung"
    assert r.sets == 3
    assert r.reps == 8
    assert r.weight_kg == 50


def test_parse_message_mit_injiziertem_katalog_erkennt_statics_nicht():
    # Ohne den Custom-Katalog wäre "Bankdrücken" ein bekannter Alias - mit einem
    # injizierten Katalog, der ihn nicht enthält, darf er nicht mehr matchen.
    custom_aliases = {"Meine Übung": ["meine übung"]}
    r = parse_message("3x8 80kg Bankdrücken", aliases=custom_aliases, cardio_exercises=set())
    assert r.exercise is None
    assert r.recognized is False


def test_koerpergewicht_alternative_formulierung():
    r = parse_message("wiege gerade 83kg")
    assert r.record_type == "bodyweight"
    assert r.weight_kg == 83


def test_koerpergewicht_confirmation_text():
    r = parse_message("Gewicht heute 84,2kg")
    assert r.confirmation_text() == "⚖️ Körpergewicht: 84.2 kg notiert"


def test_normales_training_bleibt_record_type_workout():
    r = parse_message("2 Sets 8 Wiederholungen 80kg Bankdrücken")
    assert r.record_type == "workout"
