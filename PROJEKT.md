# Trainings-Tracker Telegram-Bot — Projektzusammenfassung

_Stand: 2026-07-14 (öffentliches Repo, Dashboard-Redesign, Chat mit Gedächtnis)_

Persönlicher Fitness-Tracker: Trainingseinheiten werden per Telegram-Nachricht in
freier Sprache geloggt (z.B. „2 Sätze 8 Wiederholungen 80kg Bankdrücken"), landen in
einer Datenbank und werden auf einem installierbaren Web-Dashboard visualisiert.
Zusätzlich kann man dem Bot per Telegram frei Fragen stellen („Was steht heute an?").
Grundlage ist ein persönlicher 12-Wochen-Plan (Kickboxen + Kraft + Ausdauer), der in
`app/config.py` zentral konfiguriert ist. Das Repo ist öffentlich (MIT-Lizenz) und
zum Forken/Selbst-Hosten gedacht.

---

## Architektur

```
Telegram (Handy) --Webhook--> Render (FastAPI) --insert/query--> Supabase (Postgres)
                                    |
                                    +--> Groq LLM (Parsing + Chat, kostenlos) / Regex-Fallback
                                    +--> Telegram sendMessage/sendPhoto (Antwort/Chart)
                                    +--> Dashboard (HTML, PWA) + /cron/tick (Keep-Alive + Reminder)
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

**Repo:** github.com/leonardrieger/trainings-tracker-bot — **öffentlich, MIT-Lizenz**

**Endpunkte** (unter der eigenen Render-URL, hier `<render-url>`):
- App/Health: `https://<render-url>.onrender.com/`
- Dashboard: `https://<render-url>.onrender.com/dashboard?token=<DASHBOARD_TOKEN>`
- Cron-Tick: `https://<render-url>.onrender.com/cron/tick?token=<CRON_SECRET>`

---

## Projektstruktur

```
app/
  config.py       Persönliche Programm-Config: Wochenplan, Programmlänge, Zielgewicht, Deload-Fenster
  main.py         FastAPI-App: Webhook, /cron/tick, /dashboard (+/log, /undo), PWA-Routen, Command-Routing
  parser.py       Regex-Parsing von Nachrichten -> ParsedWorkout
  llm_parser.py   Groq-LLM-Parsing mit Regex-Fallback
  chat.py         Freies Frage-Antwort-Chat via Groq, mit Multi-Turn-Gedächtnis (letzte 3 Paare, 60min Idle-Reset)
  exercises.py    Übungsnamen + Aliase, PLAN_SECTIONS (Tag A/B/C…), SESSION_ONLY_EXERCISES
  db.py           Supabase-Wrapper (Insert/Query/State/Delete)
  telegram.py     sendMessage / sendPhoto
  chart.py        Matplotlib-Fortschritts-Charts (ruhige, minimalistische Dark-Palette, Metrik-Fallback)
  reminders.py    Reine Logik: Reminder, Wochenzähler, Klimmzug-Phasen, Deload, Wochenrückblick
  dashboard.py    App-artiges Dashboard (Tab-Navigation Heute/Fortschritt/Verlauf, Eingabe-Formular, PWA-Meta-Tags)
  static/         PWA-Icons (icon-192.png, icon-512.png)
sql/schema.sql    Tabellen: workout_logs, body_weight_logs, bot_state
docs/             Beispiel-Chart fürs README
tests/            120 Tests (pytest)
.github/workflows/test.yml   CI: pytest bei jedem Push/PR
LICENSE           MIT
CONTRIBUTING.md   Kurzanleitung für Mitwirkende (Dev-Setup, Tests, eigenen Plan konfigurieren)
requirements.txt, runtime.txt, .env.example, README.md
```

---

## Datenmodell (Supabase)

- **`workout_logs`** — id, telegram_user_id, exercise, sets, reps, weight_kg,
  duration_min, distance_km, raw_text, logged_at
- **`body_weight_logs`** — id, telegram_user_id, weight_kg, raw_text, logged_at
- **`bot_state`** — key/value (last_reminder_date, last_weekly_summary_date,
  program_start_date, chat_history)

---

## Bot-Befehle

| Befehl | Funktion |
|---|---|
| _freie Nachricht (Log)_ | Trainings-/Cardio-/Körpergewichts-Eintrag, z.B. „3x8 100kg Kniebeuge", „30 min 5 km Laufen", „Gewicht heute 84,2kg" |
| _freie Nachricht (Frage)_ | Wird nicht als Log erkannt -> geht als Chat-Frage an Groq, z.B. „Was steht heute an?", „Und morgen?" (merkt sich die letzten 3 Frage-Antwort-Paare; Kontext: Tagesplan + Wochenstand + letzte 50 Einträge) |
| `/start` | Begrüßung + eigene Telegram-User-ID |
| `/verlauf <übung>` | Letzte Einträge als Text (auch `/verlauf Gewicht`) |
| `/chart <übung>` | Fortschritts-Diagramm als Bild (auch `/chart Gewicht`) |
| `/programm [datum]` | Programmstart setzen (JJJJ-MM-TT) oder Status anzeigen |
| `/undo` | Zuletzt geloggten Eintrag löschen |

---

## Dashboard-Features

- **App-artige Ansicht:** drei Tabs (Heute / Fortschritt / Verlauf) mit fester unterer
  Tab-Leiste statt einer langen Scroll-Seite. Minimalistischer, ruhiger Dark-Look
  (warmer Amber-Akzent sehr sparsam, dünne große Zahlen mit tabular-nums, Haarlinien
  statt schwerer Karten).
- **Heute:** Tagesplan + Wochennummer groß oben, Schnell-Eingabe, Wochenstreifen
  (heutiger Tag hervorgehoben, getrackte Tage mit ✓), heute geloggte Einträge.
- **Fortschritt:** Kennzahlen (Gewicht/Woche/Trainingstage), Körpergewichts-Chart mit
  Zielband, Übungs-Charts gruppiert nach Tag A/B/C/Kickboxen/Ausdauer.
- **Verlauf:** letzte Aktivitäten als editoriale Liste.
- **Installierbar als PWA:** `/manifest.webmanifest` + `/sw.js` (No-Op-Service-Worker,
  kein Offline-Caching) + `apple-touch-icon`/Meta-Tags für iOS. "Zum Startbildschirm
  hinzufügen" macht daraus eine App-artige Kachel auf dem Handy.
- **Eingabe-Formular:** gleiche Freitext-Pipeline wie Telegram (`POST /dashboard/log`),
  plus „Rückgängig"-Button (`POST /dashboard/undo`, PRG-Redirect mit Flash-Banner) —
  Einträge sind also nicht mehr nur per Telegram möglich.
- **Chart-Metrik-Fallback:** Übungen ohne Gewicht (z.B. Klimmzüge als „3x8") zeigen
  automatisch die Wiederholungs-Progression statt eines kaputten Bildes; verbleibende
  404-Fälle werden per `onerror` durch eine Textzeile ersetzt statt Fragezeichen zu
  zeigen.

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
| `GROQ_API_KEY` | Groq-API-Key (optional; ohne → Regex-Fallback / Chat-Fallback) |
| `ALLOWED_TELEGRAM_USER_ID` | Eigene Telegram-User-ID (nur diese wird verarbeitet) |
| `CRON_SECRET` | Schützt `/cron/tick` |
| `DASHBOARD_TOKEN` | Schützt `/dashboard`, `/manifest.webmanifest` |
| `TELEGRAM_WEBHOOK_SECRET` | Schützt `/webhook` (Telegram secret_token Header) — **prüfen, dass dieser Wert in Render gesetzt ist**, sonst greift die Absicherung nicht |

_Die echten Werte liegen in der lokalen `.env` (gitignored) und in den Render-Env-Vars.
Das Repo selbst enthält keine Secrets (History geprüft)._

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
  *bereits Getrackte* ist. Behoben durch explizit getrennte, beschriftete Abschnitte
  („TRAININGSPLAN FÜR HEUTE" vs. „BEREITS GETRACKTE EINTRÄGE") im Prompt.
- **Kaputte Chart-Bilder (Fragezeichen):** Übungen ohne Gewicht (z.B. Klimmzüge als
  „3x8") lieferten am Dashboard einen 404 statt eines Charts. Behoben durch
  Metrik-Fallback (Distanz → Dauer → Gewicht → Wiederholungen) in `chart.py` plus
  `onerror`-Textfallback im Dashboard.
- **Persönliches vom übrigen Code getrennt:** Wochenplan, Zielgewicht, Deload-Fenster
  und Erinnerungs-Zeiten waren über mehrere Dateien verstreut hartcodiert. In
  `app/config.py` zentralisiert, damit Forks nur eine Datei anpassen müssen.

---

## Bereits umgesetzte Features (chronologisch, neueste zuerst)

1. **Multi-Turn-Chat-Gedächtnis** — der Chat merkt sich die letzten 3 Frage-Antwort-
   Paare (global in `bot_state`, kein Schema-Change), automatischer Reset nach 60 Min
   Inaktivität.
2. **Repo-Veröffentlichung vorbereitet** — MIT-`LICENSE`, bereinigte Docs (keine
   privaten Notizen/echte URLs mehr), `CONTRIBUTING.md`, README mit Feature-Übersicht
   und Beispiel-Chart, GitHub-Beschreibung + Topics gesetzt, Repo ist jetzt **public**.
3. **Persönliche Config ausgelagert** — `app/config.py` bündelt Wochenplan,
   Programmlänge, Zielgewicht, Deload-Fenster, Erinnerungs-Zeiten.
4. **Dashboard-Redesign** — komplett neue, app-artige Ansicht mit drei Tabs
   (Heute/Fortschritt/Verlauf), minimalistischer Dark-Look, neue Chart-Palette.
5. **Fix: kaputte Chart-Bilder** bei Übungen ohne Gewicht (Metrik-Fallback).
6. **PWA-Dashboard + Web-Eingabeformular** — installierbar auf dem Handy, Einträge
   auch direkt im Browser möglich (nicht mehr nur per Telegram).
7. **Telegram-LLM-Chat** (Basis-Version) — freie Fragen wie „Was steht heute an?"
   werden über Groq mit Plan- und Verlaufskontext beantwortet.
8. **Webhook-Absicherung, Fehlerbehandlung, `/undo`**
9. **Dashboard: Wochenkalender mit echten Wochentagen**
10. **Wochenzähler, Klimmzug-Phasen, Deload-Hinweis, Wochenrückblick**
11. **Körpergewicht-Tracking, Erinnerungen, Dashboard-Grundgerüst, CI**
12. **Initial commit** — Telegram-Bot fürs Trainings-Tracking (Regex-Parser, Supabase)

---

## Was als Nächstes ansteht

**Als Nächstes geplant:**
- **Konfigurierbarer Plan über die App** — Trainingsplan im Dashboard bearbeiten statt
  in `app/config.py` per Code-Deploy. Größerer Umbau: Plan-Daten müssten aus der
  statischen Config in die Datenbank wandern (z.B. neue Tabelle oder Erweiterung von
  `bot_state`), plus eine Edit-Oberfläche im Dashboard. Sinnvoll, sobald der Plan sich
  öfter ändern soll oder andere Nutzer die App ohne eigenen Deploy anpassen wollen
  sollen.

**Weitere Ideen (noch nicht terminiert):**
- **PR-/Rekord-Erkennung** — Bot meldet „🎉 Neuer Rekord!" bei neuem Bestwert pro Übung
  (Definition klären: höchstes Gewicht oder Volumen = Gewicht × Wiederholungen?).
- **Delta-Anzeige am Gewicht-Chart** — z.B. „−1,6 kg" als Trend-Kennzahl im
  Fortschritt-Tab (kleine Ergänzung, Daten sind schon vorhanden).
- **CSV-Export** vom Dashboard (Daten-Backup / eigene Auswertung).
- **Foto-Logging** — Foto vom Trainingsgerät-Display schicken, per Vision-Modell
  auslesen (größerer Umbau, andere Groq-Prompt-Pfad nötig).
- **Mehrbenutzer-Fähigkeit** — mehrere Telegram-Nutzer mit je eigenem Plan/Daten statt
  fixem `ALLOWED_TELEGRAM_USER_ID`. Deutlich größerer Schritt (Auth, Datentrennung,
  Onboarding) — nur sinnvoll, wenn das Projekt bewusst von „für mich" zu „für viele"
  gedreht werden soll.

---

## Lokale Entwicklung

```bash
# venv liegt bereits unter venv/
venv\Scripts\activate            # Windows
pip install -r requirements.txt
pytest                           # 120 Tests
uvicorn app.main:app --reload    # lokaler Server
```

Schema-Änderungen: Inhalt von `sql/schema.sql` im Supabase-Dashboard → SQL Editor
ausführen (keine CLI nötig).
