import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.exercises import CARDIO_EXERCISES, EXERCISE_ALIASES, PLAN_SECTIONS, SESSION_ONLY_EXERCISES

_DEFAULT_CATALOG = (EXERCISE_ALIASES, CARDIO_EXERCISES, SESSION_ONLY_EXERCISES, PLAN_SECTIONS)


@pytest.fixture(autouse=True)
def _default_exercise_catalog():
    """Übungs-Katalog-Aufrufe fallen standardmäßig auf die statischen Defaults zurück,
    damit bestehende Tests nicht jeder einzeln db.get_exercise_catalog mocken müssen.
    Ein Test mit eigenem Katalog kann diesen Patch mit einem eigenen `patch(...)`
    innerhalb des Testkörpers überschreiben."""
    with patch("app.main.db.get_exercise_catalog", return_value=_DEFAULT_CATALOG):
        yield
