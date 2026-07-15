# Trainings-Tracker Telegram-Bot — Projektzusammenfassung

_Stand: 2026-07-15 (Repo-Aufhübschung, UI-Redesign „Ember", Kalender-Heatmap + Streak-Karte, PR-Erkennung,
Übungsverwaltung im Dashboard, Sprachnachrichten-Logging, editierbarer Wochenplan,
Bequemlichkeits-Features, Python-Version-Fix)_

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
- **Sprache/Framework:** Python 3.12 (in `.python-version` gepinnt — Render beachtet
  `runtime.txt` nicht mehr, siehe „Wichtige Fixes"), FastAPI + Uvicorn
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
  main.py         FastAPI-App: Webhook, /cron/tick, /dashboard (+/log, /undo, /exercises/*), PWA-Routen, Command-Routing
  parser.py       Regex-Parsing von Nachrichten -> ParsedWorkout (Katalog per Parameter injizierbar)
  llm_parser.py   Groq-LLM-Parsing mit Regex-Fallback (Katalog per Parameter injizierbar)
  chat.py         Freies Frage-Antwort-Chat via Groq, mit Multi-Turn-Gedächtnis (letzte 3 Paare, 60min Idle-Reset)
  exercises.py    Übungsnamen + Aliase, PLAN_SECTIONS (Tag A/B/C…), SESSION_ONLY_EXERCISES — Python-Defaults,
                  DB-Override optional über die neue exercises-Tabelle (siehe db.get_exercise_catalog)
  db.py           Supabase-Wrapper (Insert/Query/State/Delete, Übungs-Katalog-CRUD mit Seed-bei-erstem-Schreiben)
  telegram.py     sendMessage (+ reply_markup) / sendPhoto / answerCallbackQuery / Datei-Download
  transcribe.py   Sprachnachrichten-Transkription via Groq Whisper (kostenlos), kein Fallback bei Fehler
  chart.py        Matplotlib-Fortschritts-Charts (ruhige, minimalistische Dark-Palette, Metrik-Fallback)
  reminders.py    Reine Logik: Reminder, Wochenzähler, Klimmzug-Phasen, Deload, Wochenrückblick, Gewichts-Delta
  dashboard.py    App-artiges Dashboard (Tab-Navigation Heute/Fortschritt/Verlauf/Plan/Übungen, Eingabe-Formular
                  mit Autocomplete + Wiederholen-Chips, PWA-Meta-Tags)
  static/         PWA-Icons (icon-192.png, icon-512.png)
sql/schema.sql    Tabellen: workout_logs, body_weight_logs, bot_state, exercises
docs/             banner.svg (README-Header im Ember-Look: Activity-Ring + Flamme +
                  Heatmap-Punktfeld, generiert per Skript) + screenshots/*.png
                  (alle fünf Dashboard-Tabs, siehe „Bereits umgesetzte Features")
tests/            263 Tests (pytest) + conftest.py (Autouse-Fixture für Übungs-Katalog-Default)
.github/workflows/test.yml   CI: pytest bei jedem Push/PR
LICENSE           MIT
CONTRIBUTING.md   Kurzanleitung für Mitwirkende (Dev-Setup, Tests, eigenen Plan konfigurieren)
requirements.txt, .python-version, .env.example, README.md
```

---

## Datenmodell (Supabase)

- **`workout_logs`** — id, telegram_user_id, exercise, sets, reps, weight_kg,
  duration_min, distance_km, raw_text, logged_at
- **`body_weight_logs`** — id, telegram_user_id, weight_kg, raw_text, logged_at
- **`bot_state`** — key/value (last_reminder_date, last_weekly_summary_date,
  program_start_date, chat_history, training_plan)
- **`exercises`** — id, name (unique), aliases (text[]), section (nullable, einer der
  5 festen Tag-Titel), is_cardio, is_session_only, sort_order. Leer = Python-Defaults
  aus `app/exercises.py` gelten unverändert; wird bei der ersten Änderung über den
  „Übungen"-Tab einmalig komplett mit diesen Defaults befüllt (siehe
  `db._seed_exercises_if_empty`), damit ein einzelner Edit nicht alle anderen Übungen
  unsichtbar macht.

---

## Bot-Befehle

| Befehl | Funktion |
|---|---|
| _freie Nachricht (Log)_ | Trainings-/Cardio-/Körpergewichts-Eintrag, z.B. „3x8 100kg Kniebeuge", „30 min 5 km Laufen", „Gewicht heute 84,2kg" |
| _freie Nachricht (Frage)_ | Wird nicht als Log erkannt -> geht als Chat-Frage an Groq, z.B. „Was steht heute an?", „Und morgen?" (merkt sich die letzten 3 Frage-Antwort-Paare; Kontext: Tagesplan + Wochenstand + letzte 50 Einträge) |
| _Sprachnachricht_ | Wird via Groq Whisper transkribiert (kostenlos), Transkript kommt als Echo zurück und durchläuft danach dieselbe Log-/Chat-Erkennung wie eine getippte Nachricht |
| `/start` | Begrüßung + eigene Telegram-User-ID |
| `/verlauf [übung]` | Letzte Einträge als Text (auch `/verlauf Gewicht`); ohne Übung Inline-Tastatur mit den zuletzt genutzten Übungen |
| `/chart [übung]` | Fortschritts-Diagramm als Bild (auch `/chart Gewicht`); ohne Übung Inline-Tastatur |
| `/programm [datum]` | Programmstart setzen (JJJJ-MM-TT) oder Status anzeigen |
| `/undo` | Zuletzt geloggten Eintrag löschen |

Beim Loggen mit Gewicht meldet der Bot zusätzlich „🎉 Neuer Rekord!", wenn `weight_kg`
den bisher höchsten für diese Übung geloggten Wert übertrifft (Definition: höchstes
Gewicht, nicht Volumen).

---

## Dashboard-Features

- **App-artige Ansicht:** fünf Tabs (Heute / Fortschritt / Verlauf / Plan / Übungen)
  mit schwebender Pill-Tab-Bar statt einer langen Scroll-Seite. Dark-Look „Ember":
  warmer Amber-Akzent, dünne große Zahlen mit tabular-nums, Glas-Karten
  (rgba-Flächen + Haarlinien-Rand) über einem statischen Ambiente-Hintergrund aus
  zwei Radial-Glows. Sticky App-Header mit `max(env(safe-area-inset-top), 14px)` —
  auf dem iPhone (Statusleiste/Dynamic Island) wird kein Inhalt mehr verdeckt.
  Aktiver Tab wird server-seitig über `?view=` gesteuert (z.B. nach einem Redirect
  gezielt auf einem Tab landen).
- **Heute:** Tagesplan + Wochennummer groß oben, „Zuletzt"-Chips (letzter geloggter
  Satz je Übung, Antippen füllt das Eingabefeld vor statt neu zu tippen),
  Schnell-Eingabe mit Übungsnamen-Autocomplete (`<datalist>`), Wochenstreifen
  (heutiger Tag hervorgehoben, getrackte Tage mit ✓), Activity-Ring
  (Apple-Watch-artig: Bogen = Trainingstage/Wochenziel mit Amber-Gradient und
  CSS-Füllanimation, animierte SVG-Flamme im Zentrum — grau/erloschen ohne
  Aktivität — daneben „X / 6 Tage diese Woche" + Wochen-Serie), heute geloggte
  Einträge.
- **Fortschritt:** Kennzahlen (Gewicht/Woche/Trainingstage), Körpergewichts-Chart mit
  Zielband + 7-Tage-Delta (z.B. „↓ 1,6 kg"), Übungs-Charts gruppiert nach
  Tag A/B/C/Kickboxen/Ausdauer.
- **Verlauf:** GitHub-artige Kalender-Heatmap der letzten 26 Wochen (Monatslabels,
  heutiger Tag markiert, horizontal scrollbar) + letzte Aktivitäten als editoriale Liste.
- **Plan:** Wochenplan (Lang-/Kurzform je Wochentag) direkt im Dashboard bearbeiten
  statt per Code-Deploy in `app/config.py` — liegt als Override in `bot_state`
  (JSON), fällt pro Tag auf die Config-Defaults zurück, „Zurücksetzen"-Button stellt
  die Defaults wieder her. Wirkt sich auf Telegram-Erinnerung, Heute-Tab und den
  LLM-Chat-Kontext aus.
- **Übungen:** volle Verwaltung des Übungs-Katalogs — neue Übungen anlegen,
  bestehende umbenennen (kaskadiert automatisch auf `workout_logs`, Verlaufsdaten
  bleiben erhalten), Aliase bearbeiten, Tag-Zuordnung ändern (die 5 Tag-Titel selbst
  bleiben fix), Cardio-/Session-only-Flags setzen, löschen (nur der Katalog-Eintrag —
  bisherige Log-Einträge bleiben unter „Sonstiges" im Fortschritt-Tab sichtbar). Kein
  „Alles zurücksetzen", um eigene Anpassungen nicht versehentlich zu verwerfen.
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
| `GROQ_API_KEY` | Groq-API-Key (optional; ohne → Regex-Fallback / Chat-Fallback; Sprachnachrichten-Transkription funktioniert ganz ohne Fallback nicht) |
| `ALLOWED_TELEGRAM_USER_ID` | Eigene Telegram-User-ID (nur diese wird verarbeitet) |
| `CRON_SECRET` | Schützt `/cron/tick` |
| `DASHBOARD_TOKEN` | Schützt `/dashboard`, `/manifest.webmanifest` |
| `TELEGRAM_WEBHOOK_SECRET` | Schützt `/webhook` (Telegram secret_token Header) — **prüfen, dass dieser Wert in Render gesetzt ist**, sonst greift die Absicherung nicht |

_Die echten Werte liegen in der lokalen `.env` (gitignored) und in den Render-Env-Vars.
Das Repo selbst enthält keine Secrets (History geprüft)._

---

## Wichtige Fixes/Erkenntnisse während der Entwicklung

- **Render wählte anfangs Python 3.14** → matplotlib hatte dafür keine fertigen Wheels,
  Build hing beim Kompilieren. Zunächst gelöst durch `runtime.txt` mit `python-3.12.10`.
- **`runtime.txt` wird von Render nicht mehr beachtet:** Render hat die Versions-Auswahl
  umgestellt (Priorität: `PYTHON_VERSION`-Env-Var → `.python-version`-Datei → Default nach
  Service-Erstellungsdatum) und ignoriert `runtime.txt` inzwischen still, ohne Fehler. Der
  Build lief dadurch unbemerkt wieder auf Python 3.14 (aktueller Default). Behoben durch
  `.python-version` mit `3.12.10` statt `runtime.txt`.
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

1. **Screenshots aufs Ember-Design aktualisiert** — die fünf Galerie-PNGs unter
   `docs/screenshots/` liefen als eigener Background-Task parallel zur
   Repo-Aufhübschung (Punkt 2) und landeten deshalb zunächst auf einem eigenen
   Branch (`claude/fervent-bun-e414f9`), der von einem älteren Commit-Stand
   abzweigte. Da dieser Branch auch eine veraltete README-Version enthielt, wurden
   **nur die PNGs** per `git checkout <branch> -- docs/screenshots/` auf `master`
   übernommen, das bereits überarbeitete README blieb unangetastet (Commit
   `4f48f11`). Der Nebenbranch wurde nach Nutzer-Freigabe gelöscht (destruktive
   Git-Aktionen brauchen hier explizite Zustimmung). Nach dem Push zeigte GitHub
   kurzzeitig noch die alten Bilder
   (Browser-/Bild-Proxy-Cache bei unverändertem Dateinamen); per `curl -I` auf
   `raw.githubusercontent.com` wurde bestätigt, dass der Server bereits die neue
   Dateigröße ausliefert — mit Hard-Reload war es dann sofort aktuell.
2. **Repo-Aufhübschung** — neuer README-Banner im Ember-Look (Activity-Ring mit
   Flamme, Heatmap-Punktfeld, generiert deterministisch per Skript), README
   editorial umgebaut: Tagline, erzählende Feature-Absätze statt Stichpunkte,
   Mermaid-Architekturdiagramm (rendert direkt auf GitHub), Setup-Schritte in
   aufklappbare `<details>`-Blöcke kollabiert, Nutzungs-Tabelle,
   Screenshot-Dateinamen unverändert (Galerie-PNGs kamen wie in Punkt 1
   beschrieben aus einer separaten Session). GitHub-Repo-Beschreibung geschärft +
   Topic `telegram`.
3. **UI-Redesign „Ember"** — sticky App-Header mit Safe-Area-Padding (iPhone-
   Statusleiste verdeckte vorher Inhalt), Streak-Karte zum Apple-Watch-artigen
   Activity-Ring umgebaut (SVG-Bogen = Trainingstage/Wochenziel, Amber-Gradient,
   Flamme im Zentrum, Füllanimation rein per CSS über `stroke-dashoffset`; der
   Keyframe definiert bewusst nur `from` — `var()` in Keyframes ist in älteren
   Safari-Versionen unzuverlässig), statischer Ambiente-Hintergrund, Glas-Karten,
   schwebende Pill-Tab-Bar, gestaffelte Einblend-Animationen (nur
   transform/opacity, hinter `prefers-reduced-motion`). Markup der Tests
   unverändert — alle 263 weiterhin grün, nur `app/dashboard.py` angefasst.
4. **Kalender-Heatmap + Streak-Karte mit Flammenanimation** — Verlauf-Tab zeigt
   eine 26-Wochen-Heatmap der Trainingstage (binär trainiert/nicht, ein einziger
   zusätzlicher DB-Call, der auch die Streak-Berechnung speist); Heute-Tab zeigt
   unter dem Wochenstreifen eine Streak-Karte mit animierter SVG-Flamme
   (CSS-Transform-Flackern hinter `prefers-reduced-motion`, Glow bewusst statisch —
   ein animierter `drop-shadow`-Filter würde pro Frame neu rastern). Neue reine
   Logik `weekly_day_counts`/`week_streak` in `reminders.py` (laufende Woche bricht
   die Serie nicht, zählt ab Zielerreichung mit), 13 neue Tests (263 gesamt).
5. **README-Überarbeitung (Banner, Badges, Screenshots)** — SVG-Banner im
   Dashboard-Look (dunkler Grund, Amber-Akzent, abstrakte Fortschrittslinie,
   `docs/banner.svg`) ersetzt den nackten Projekttitel; Badges für CI-Status,
   Python-Version, PWA und Lizenz direkt darunter. Neue Screenshot-Galerie zeigt
   alle fünf Dashboard-Tabs (Heute/Fortschritt/Verlauf/Plan/Übungen) als echte
   Renderings der Dashboard-HTML/CSS/JS unter `docs/screenshots/`. Erzeugt über
   einen lokal gestarteten Server mit frei erfundenen Demo-Trainingsdaten (alle
   `db.*`-Funktionen gemockt, kein Zugriff auf die echte Supabase-DB), per
   headless Edge (`msedge --headless=new --screenshot=...`) abfotografiert.
   Ersetzt das alte einzelne Beispiel-Chart-Bild.
6. **PR-Erkennung + Übungsverwaltung im Dashboard** — Bot meldet „🎉 Neuer Rekord!" bei
   neuem Bestgewicht pro Übung. Neuer „Übungen"-Tab: Übungen/Aliase/Tag-Zuordnung/
   Cardio-Flags voll verwaltbar statt nur per Code-Deploy in `app/exercises.py` —
   neue `exercises`-Tabelle (Migration ausgeführt), Seed-bei-erstem-Schreiben
   verhindert, dass ein einzelner Edit alle anderen Übungen unsichtbar macht,
   Umbenennung kaskadiert auf `workout_logs`.
7. **Sprachnachrichten-Logging** — Trainingseinträge per Telegram-Sprachnachricht statt
   Tippen. Transkription via Groq Whisper (kostenlos), rohes Transkript kommt immer
   zuerst als Echo zurück (Transparenz bei möglichen Fehltranskriptionen deutscher
   Fachbegriffe), danach dieselbe Erkennungs-/Bestätigungs-/Chat-Fallback-Pipeline wie
   bei getippten Nachrichten. Kein Fallback bei Transkriptions-Fehlern möglich (anders
   als beim Text-Parsing) — eigene Fehlermeldung dafür.
8. **Vier Bequemlichkeits-Features** — Übungsnamen-Autocomplete im Eingabefeld,
   7-Tage-Delta am Gewicht-Chart, „Zuletzt"-Chips zum Wiederholen des letzten Satzes
   je Übung, Telegram-Inline-Tastaturen für `/verlauf` und `/chart` ohne Argument.
9. **Dashboard-Routen gegen transiente DB-Fehler abgesichert** — bei einem kurzen
   Supabase-Netzwerk-Hänger zeigen `/dashboard*`-Routen jetzt eine freundliche
   Meldung statt der rohen FastAPI-500-Seite (analog zum bestehenden Muster im
   Webhook).
10. **Python-Version-Pinning repariert** — Render beachtet `runtime.txt` nicht mehr
   (Versions-Auswahl umgestellt auf `PYTHON_VERSION`-Env-Var/`.python-version`);
   Build lief dadurch unbemerkt wieder auf Python 3.14. Behoben durch
   `.python-version` mit `3.12.10`.
11. **Editierbarer Wochenplan** — neuer „Plan"-Tab im Dashboard, Wochenplan-Text liegt
   als Override in `bot_state` (JSON) statt nur in `app/config.py`, Fallback pro Tag
   auf die Config-Defaults, wirkt sich auf Erinnerung/Heute-Tab/Chat-Kontext aus.
12. **Multi-Turn-Chat-Gedächtnis** — der Chat merkt sich die letzten 3 Frage-Antwort-
   Paare (global in `bot_state`, kein Schema-Change), automatischer Reset nach 60 Min
   Inaktivität.
13. **Repo-Veröffentlichung vorbereitet** — MIT-`LICENSE`, bereinigte Docs (keine
   privaten Notizen/echte URLs mehr), `CONTRIBUTING.md`, README mit Feature-Übersicht
   und Beispiel-Chart, GitHub-Beschreibung + Topics gesetzt, Repo ist jetzt **public**.
14. **Persönliche Config ausgelagert** — `app/config.py` bündelt Wochenplan,
   Programmlänge, Zielgewicht, Deload-Fenster, Erinnerungs-Zeiten.
15. **Dashboard-Redesign** — komplett neue, app-artige Ansicht mit drei Tabs
    (Heute/Fortschritt/Verlauf), minimalistischer Dark-Look, neue Chart-Palette.
16. **Fix: kaputte Chart-Bilder** bei Übungen ohne Gewicht (Metrik-Fallback).
17. **PWA-Dashboard + Web-Eingabeformular** — installierbar auf dem Handy, Einträge
    auch direkt im Browser möglich (nicht mehr nur per Telegram).
18. **Telegram-LLM-Chat** (Basis-Version) — freie Fragen wie „Was steht heute an?"
    werden über Groq mit Plan- und Verlaufskontext beantwortet.
19. **Webhook-Absicherung, Fehlerbehandlung, `/undo`**
20. **Dashboard: Wochenkalender mit echten Wochentagen**
21. **Wochenzähler, Klimmzug-Phasen, Deload-Hinweis, Wochenrückblick**
22. **Körpergewicht-Tracking, Erinnerungen, Dashboard-Grundgerüst, CI**
23. **Initial commit** — Telegram-Bot fürs Trainings-Tracking (Regex-Parser, Supabase)

---

## Was als Nächstes ansteht

**Noch nicht terminiert:**
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
pytest                           # 263 Tests
uvicorn app.main:app --reload    # lokaler Server
```

Schema-Änderungen: Inhalt von `sql/schema.sql` im Supabase-Dashboard → SQL Editor
ausführen (keine CLI nötig).
