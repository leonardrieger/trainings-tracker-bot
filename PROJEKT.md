# Trainings-Tracker Telegram-Bot — Projektzusammenfassung

_Stand: 2026-07-14 (PWA-Dashboard + Chat-Feature)_

Persönlicher Fitness-Tracker: Trainingseinheiten werden per Telegram-Nachricht in
freier Sprache geloggt (z.B. „2 Sätze 8 Wiederholungen 80kg Bankdrücken"), landen in
einer Datenbank und werden auf einem Web-Dashboard visualisiert. Grundlage ist ein
persönlicher 12-Wochen-Plan (Kickboxen + Kraft + Ausdauer).

---

## Architektur

```
Telegram (Handy) --Webhook--> Render (FastAPI) --insert/query--> Supabase (Postgres)
                                    |
                                    +--> Groq LLM (Parsing, kostenlos) / Regex-Fallback
                                    +--> Telegram sendMessage/sendPhoto (Antwort/Chart)
                                    +--> Dashboard (HTML) + /cron/tick (Keep-Alive + Reminder)
```

**Technologie-Entscheidungen:**
- **Datenbank:** Supabase (kostenloses Postgres)
- **Hosting:** Render Free Web Service (schläft nach ~15 Min Inaktivität ein → erster
  Request danach dauert 10–30 s; wird durch externen Ping wach gehalten)
- **Parsing:** Groq LLM (`llama-3.3-70b-versatile`, kostenlos) mit automatischem
  Regex-Fallback, falls kein API-Key gesetzt ist oder der Call fehlschlägt
- **Sprache/Framework:** Python 3.12 (in `runtime.txt` gepinnt), FastAPI + Uvicorn
- **Keep-Alive & Erinnerungen:** externer Ping-Dienst (cron-job.org) ruft alle 10 Min
  `/cron/tick` auf — bewusst statt GitHub-Actions-Cron (das hätte das kostenlose
  Minutenkontingent gesprengt)

**Repo:** github.com/leonardrieger/trainings-tracker-bot (privat)

**Live-URLs:**
- App/Health: `https://trainings-tracker-bot.onrender.com/`
- Dashboard: `https://trainings-tracker-bot.onrender.com/dashboard?token=<DASHBOARD_TOKEN>`
- Cron-Tick: `https://trainings-tracker-bot.onrender.com/cron/tick?token=<CRON_SECRET>`

---

## Projektstruktur

```
app/
  main.py         FastAPI-App: Webhook, /cron/tick, /dashboard (+/log, /undo), PWA-Routen, Command-Routing
  parser.py       Regex-Parsing von Nachrichten -> ParsedWorkout
  llm_parser.py   Groq-LLM-Parsing mit Regex-Fallback
  chat.py         Freies Frage-Antwort-Chat via Groq (Kontext: Plan + letzte 50 Einträge)
  exercises.py    Übungsnamen + Aliase, PLAN_SECTIONS (Tag A/B/C…), SESSION_ONLY_EXERCISES
  db.py           Supabase-Wrapper (Insert/Query/State/Delete)
  telegram.py     sendMessage / sendPhoto
  chart.py        Matplotlib-Fortschritts-Charts (Dark-Palette)
  reminders.py    Reine Logik: Reminder, Wochenzähler, Klimmzug-Phasen, Deload, Wochenrückblick
  dashboard.py    HTML-Dashboard (Stat-Tiles, Wochenkalender, Eingabe-Formular, PWA-Meta-Tags)
  static/         PWA-Icons (icon-192.png, icon-512.png)
sql/schema.sql    Tabellen: workout_logs, body_weight_logs, bot_state
tests/            103 Tests (pytest)
.github/workflows/test.yml   CI: pytest bei jedem Push/PR
requirements.txt, runtime.txt, .env.example, README.md
```

---

## Datenmodell (Supabase)

- **`workout_logs`** — id, telegram_user_id, exercise, sets, reps, weight_kg,
  duration_min, distance_km, raw_text, logged_at
- **`body_weight_logs`** — id, telegram_user_id, weight_kg, raw_text, logged_at
- **`bot_state`** — key/value (last_reminder_date, last_weekly_summary_date,
  program_start_date)

---

## Bot-Befehle

| Befehl | Funktion |
|---|---|
| _freie Nachricht (Log)_ | Trainings-/Cardio-/Körpergewichts-Eintrag, z.B. „3x8 100kg Kniebeuge", „30 min 5 km Laufen", „Gewicht heute 84,2kg" |
| _freie Nachricht (Frage)_ | Wird nicht als Log erkannt -> geht als Chat-Frage an Groq, z.B. „Was steht heute an?", „Wie viele Trainingstage diese Woche?" (Kontext: Tagesplan + Wochenstand + letzte 50 Einträge) |
| `/start` | Begrüßung + eigene Telegram-User-ID |
| `/verlauf <übung>` | Letzte Einträge als Text (auch `/verlauf Gewicht`) |
| `/chart <übung>` | Fortschritts-Diagramm als Bild (auch `/chart Gewicht`) |
| `/programm [datum]` | Programmstart setzen (JJJJ-MM-TT) oder Status anzeigen |
| `/undo` | Zuletzt geloggten Eintrag löschen |

---

## Dashboard-Features

- **Installierbar als PWA:** `/manifest.webmanifest` + `/sw.js` (No-Op-Service-Worker,
  kein Offline-Caching) + `apple-touch-icon`/Meta-Tags für iOS. "Zum Startbildschirm
  hinzufügen" macht daraus eine App-artige Kachel auf dem Handy.
- **Eingabe-Formular** oben im Dashboard: gleiche Freitext-Pipeline wie Telegram
  (`POST /dashboard/log`), plus „Rückgängig"-Button (`POST /dashboard/undo`,
  PRG-Redirect mit Flash-Banner) — Einträge sind also nicht mehr nur per Telegram
  möglich.
- **Wochenkalender** (Mo–So) mit echten Wochentagen + Kurzplan, heutiger Tag
  hervorgehoben, bereits getrackte Tage mit ✓
- **Stat-Tiles:** Programmwoche (X/12), aktuelles Gewicht, Zielgewicht (87–89 kg),
  Trainingstage, letzte Aktivität
- **Deload-Banner** in Wochen 6–8
- **Körpergewichts-Chart** mit Zielband (87–89 kg)
- Übungen gruppiert nach **Tag A / Tag B / Tag C / Kickboxen & Sparring / Ausdauer**;
  getrackte Übungen als Chart-Karte, ungetrackte kompakt als Textzeile
- Kickboxen/Sparring als Zähler-Karte (keine Zahlen zu tracken)
- Tabelle der letzten 20 Aktivitäten
- Design nach validierter Dark-Palette (dataviz-Skill)

---

## Automatische Nachrichten (via /cron/tick)

- **Morgens 7:00 (Europe/Berlin):** Trainings-Erinnerung mit heutigem Plan,
  Wochennummer, mittwochs Klimmzug-Phasen-Hinweis (Wochen 1–4/5–8/9–12), in Deload-Wochen
  ein Deload-Hinweis
- **Sonntags 20:00:** Wochenrückblick (Trainingstage von 6 geplant, Gewichtsänderung)

---

## Umgebungsvariablen (Render + lokale .env)

| Variable | Zweck |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot-Token von @BotFather |
| `SUPABASE_URL` | Supabase Projekt-URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role-Key (geheim!) |
| `GROQ_API_KEY` | Groq-API-Key (optional; ohne → Regex-Fallback) |
| `ALLOWED_TELEGRAM_USER_ID` | Eigene Telegram-User-ID (nur diese wird verarbeitet) |
| `CRON_SECRET` | Schützt `/cron/tick` |
| `DASHBOARD_TOKEN` | Schützt `/dashboard` |
| `TELEGRAM_WEBHOOK_SECRET` | Schützt `/webhook` (Telegram secret_token Header) |

_Die echten Werte liegen in der lokalen `.env` (gitignored) und in den Render-Env-Vars._

---

## Wichtige Fixes/Erkenntnisse während der Entwicklung

- **Render wählte anfangs Python 3.14** → matplotlib hatte dafür keine fertigen Wheels,
  Build hing beim Kompilieren. Gelöst durch `runtime.txt` mit `python-3.12.10`.
- **Supabase-Bibliothek 2.9.1** kannte das neue Key-Format (`sb_secret_…`) nicht
  („Invalid API key"). Upgrade auf `supabase==2.31.0`.
- **Alias-Kollision:** „Overhead Press" wurde fälschlich als „Schulterdrücken" erkannt
  (überlappende Aliase). Sauber getrennt.
- **Session-Übungen** (Kickboxen/Sparring) ohne Zahlen zeigten „NonexNone @ Nonekg" →
  jetzt „✓ absolviert" / Zähler-Karte.
- **Variable-Shadowing:** lokale Variable `date` überschattete den `date`-Import und ließ
  `/programm` mit `UnboundLocalError` abstürzen. Behoben.
- **Sicherheit:** Webhook vertraute ursprünglich nur auf `from.id` im Body (fälschbar) →
  jetzt zusätzlich Telegram `secret_token`-Header-Prüfung.
- **Nicht erkannter Text landete als Datenmüll:** vor dem Chat-Feature wurde jede
  nicht erkannte Nachricht trotzdem als Workout-Log mit `exercise="Unbekannt"`
  gespeichert. Behoben durch Routing über `ParsedWorkout.recognized` — unerkannter
  Text geht jetzt an den Chat statt in die Datenbank.
- **LLM verwechselte Tagesplan mit bereits Absolviertem:** der Chat-Kontext enthielt
  ursprünglich nur „Heute: Kickboxen" ohne Kennzeichnung, ob das der *Plan* oder
  *bereits Getrackte* ist — das Modell antwortete dadurch fälschlich, ein geplanter
  Trainingstag sei schon erledigt. Behoben durch explizit getrennte, beschriftete
  Abschnitte („TRAININGSPLAN FÜR HEUTE" vs. „BEREITS GETRACKTE EINTRÄGE") im Prompt.

---

## OFFENE PUNKTE / TODO

### Muss noch erledigt werden (durch dich)
1. **`TELEGRAM_WEBHOOK_SECRET` in Render eintragen** — der Wert steht in der lokalen
   `.env`. Erst danach ist die Webhook-Absicherung scharf geschaltet. (Der Webhook
   selbst wurde bereits mit `secret_token` neu gesetzt.)
2. **Secrets rotieren (empfohlen):** `TELEGRAM_BOT_TOKEN` und `GROQ_API_KEY` waren im
   Entwicklungs-Chat im Klartext sichtbar. Neu generieren:
   - Bot: @BotFather → `/mybots` → Bot wählen → API Token → Revoke
   - Groq: console.groq.com → API Keys → neuen Key erstellen
   - Danach lokale `.env` **und** Render-Env-Vars aktualisieren.

### Mögliche nächste Features (noch nicht umgesetzt)
- **PR-/Rekord-Erkennung:** Bot meldet „🎉 Neuer Rekord!" bei neuem Bestgewicht pro Übung
- **CSV-Export** vom Dashboard (Daten-Backup / eigene Auswertung)
- **Multi-Turn-Chat-Gedächtnis:** aktuell ist jede Chat-Frage ein eigenständiger
  Groq-Call ohne vorherige Konversation

---

## Lokale Entwicklung

```bash
# venv liegt bereits unter venv/
venv\Scripts\activate            # Windows
pip install -r requirements.txt
pytest                           # 82 Tests
uvicorn app.main:app --reload    # lokaler Server
```

Schema-Änderungen: Inhalt von `sql/schema.sql` im Supabase-Dashboard → SQL Editor
ausführen (keine CLI nötig).
