# Mitmachen

Danke fürs Interesse! Dies ist ein persönliches Hobby-Projekt — der Umfang bleibt
bewusst überschaubar und auf Einzelnutzung ausgelegt. Pull Requests und Issues sind
trotzdem willkommen, besonders Bugfixes, Tests und Verbesserungen an Doku und
Parsing.

## Entwicklungsumgebung

```bash
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

Die App läuft auch **ohne** externe Dienste, solange du keine DB-/LLM-Funktionen
aufrufst — die Tests brauchen weder Supabase noch einen Groq-Key.

## Tests

```bash
pytest
```

Bitte lass die komplette Suite grün und ergänze Tests für neues Verhalten. Die
CI ([.github/workflows/test.yml](.github/workflows/test.yml)) führt `pytest` bei jedem
Push und PR aus.

## Eigenen Trainingsplan nutzen

Zum Anpassen auf ein anderes Programm reicht in der Regel:

- [`app/config.py`](app/config.py) — Wochenplan, Programmlänge, Zielgewicht,
  Deload-Fenster, Erinnerungs-Zeiten.
- [`app/exercises.py`](app/exercises.py) — Übungsnamen, Aliase und die Zuordnung zu
  Plan-Sektionen.

## Grober Aufbau

Ein kurzer Überblick über Architektur und Module steht in
[`PROJEKT.md`](PROJEKT.md); die Ersteinrichtung einer eigenen Instanz in
[`README.md`](README.md).

## Stil

- Bestehende Konventionen und den Ton der umliegenden Kommentare übernehmen.
- Keine Geheimnisse committen — alles Sensible gehört in die lokale `.env`
  (per `.gitignore` ausgeschlossen) bzw. in die Environment-Variablen des Hostings.
