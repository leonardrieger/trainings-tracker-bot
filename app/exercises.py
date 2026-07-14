"""Kanonische Übungsnamen mit Alias-Keywords, abgeleitet aus dem 12-Wochen-Trainingsplan.

Reihenfolge ist relevant: längere/spezifischere Aliase stehen vor kürzeren,
damit z.B. "Schrägbankdrücken" nicht fälschlich als "Bankdrücken" erkannt wird.
"""

# canonical name -> list of lowercase alias substrings
EXERCISE_ALIASES: dict[str, list[str]] = {
    "Schrägbankdrücken": ["schrägbankdrücken", "schraegbankdruecken", "incline bench"],
    "Bankdrücken": ["bankdrücken", "bankdruecken", "bench press", "bench"],
    "Kniebeuge": ["kniebeuge", "kniebeugen", "squat", "squats"],
    "Bulgarian Split Squat": ["bulgarian split squat", "split squat", "bulgarian squat"],
    "Rumänisches Kreuzheben": [
        "rumänisches kreuzheben",
        "rumaenisches kreuzheben",
        "rdl",
        "romanian deadlift",
    ],
    "Kreuzheben": ["kreuzheben", "deadlift"],
    "Schulterdrücken": [
        "schulterdrücken",
        "schulterdruecken",
        "shoulder press",
        "overhead press",
        "ohp",
    ],
    "Wadenheben": ["wadenheben", "calf raise", "calf raises"],
    "Hanging Leg Raises": ["hanging leg raise", "leg raise", "leg raises"],
    "Klimmzüge": ["klimmzüge", "klimmzug", "klimmzuege", "pull up", "pull-up", "pullup"],
    "Negative Klimmzüge": ["negative klimmzüge", "negative klimmzuege", "negative pull up"],
    "Langhantelrudern": ["langhantelrudern", "barbell row", "langhantel rudern"],
    "Einarmiges KH-Rudern": [
        "einarmiges kh-rudern",
        "einarmiges rudern",
        "one arm row",
        "einarmiges kurzhantelrudern",
    ],
    "Latzug": ["latzug", "lat pulldown", "pulldown"],
    "Face Pulls": ["face pull", "face pulls"],
    "Bizeps-Curls": ["bizeps-curls", "bizeps curls", "bicep curls", "bizepscurls"],
    "Nacken-Curls": ["nacken-curls", "nacken curls", "neck curls", "nackencurls"],
    "Farmer's Walk": ["farmer's walk", "farmers walk", "farmer walk"],
    "Dips": ["dips", "dip"],
    "Overhead Press": ["overhead press"],
    "Pallof Press": ["pallof press", "pallof"],
    "Seitheben": ["seitheben", "lateral raise", "lateral raises"],
    "Sparring": ["sparring"],
    "Kickboxen": ["kickboxen", "kickbox"],
    "Laufen": ["laufen", "gelaufen", "joggen", "gejoggt", "lauf", "running", "jog"],
}

CARDIO_EXERCISES = {"Laufen", "Sparring", "Kickboxen"}


def match_exercise(text: str) -> str | None:
    """Findet die längste (spezifischste) passende Übung im Text."""
    lowered = text.lower()
    best_match: str | None = None
    best_len = 0
    for canonical, aliases in EXERCISE_ALIASES.items():
        for alias in aliases:
            if alias in lowered and len(alias) > best_len:
                best_match = canonical
                best_len = len(alias)
    return best_match
