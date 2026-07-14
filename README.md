# Trainings-Tracker Telegram-Bot

Trackt Trainingseinheiten per Telegram-Nachricht (z.B. "2 Sätze 8 Wiederholungen 80kg
Bankdrücken"), speichert sie in Supabase und zeigt Fortschritt per `/verlauf` und
`/chart`. Nachrichten werden per kostenloser Groq-LLM-API in strukturierte Daten
umgewandelt (versteht auch freie Formulierungen); ist kein `GROQ_API_KEY` gesetzt oder
schlägt der API-Call fehl, springt automatisch ein Regex-Parser als Fallback ein.

## 1. Telegram-Bot erstellen

1. In Telegram den Chat **@BotFather** öffnen.
2. `/newbot` senden, Namen vergeben.
3. Den erhaltenen **Bot-Token** notieren (Format `123456:ABC-...`).

## 2. Supabase-Projekt einrichten

1. Auf [supabase.com](https://supabase.com) kostenloses Projekt anlegen.
2. Im SQL-Editor (Dashboard → SQL Editor, **keine CLI nötig**) den Inhalt von
   [`sql/schema.sql`](sql/schema.sql) einfügen und ausführen.
3. Unter **Settings → API**: `Project URL` und **`service_role`**-Key notieren
   (⚠️ nicht den `anon`/`publishable` Key verwenden — der service_role-Key ist geheim
   und umgeht Row-Level-Security, wird aber nur serverseitig in Render eingetragen,
   niemals committet oder öffentlich geteilt).

## 3. Groq API-Key erstellen (optional, aber empfohlen)

1. Auf [console.groq.com](https://console.groq.com) kostenlos registrieren (keine
   Kreditkarte nötig).
2. Unter **API Keys** einen neuen Key erstellen.
3. Ohne diesen Key funktioniert der Bot trotzdem — er nutzt dann automatisch den
   eingebauten Regex-Parser statt der LLM-Erkennung.

## 4. Lokal testen (optional, aber empfohlen)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # dann Werte eintragen
pytest                         # Parser-Tests laufen lassen
```

Server lokal starten und Webhook-Request simulieren:

```bash
uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d "{\"message\":{\"chat\":{\"id\":1},\"from\":{\"id\":1},\"text\":\"2 Sätze 8 Wiederholungen 80kg Bankdrücken\"}}"
```

(`ALLOWED_TELEGRAM_USER_ID=1` in `.env` setzen für diesen Testaufruf.)

## 5. Auf GitHub pushen

```bash
git init
git add .
git commit -m "Trainings-Tracker Bot"
```

Dann Repo auf GitHub erstellen und pushen (siehe GitHub-Anleitung "push an existing
repository").

## 6. Auf Render deployen

1. Auf [render.com](https://render.com) Account erstellen, mit GitHub verbinden.
2. **New → Web Service** → das gepushte Repo auswählen.
3. Einstellungen:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Unter **Environment** die Variablen aus `.env.example` eintragen
   (`TELEGRAM_BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`,
   `CRON_SECRET`, `DASHBOARD_TOKEN`, `ALLOWED_TELEGRAM_USER_ID` — letztere zunächst leer
   lassen, siehe Schritt 7).
5. Deployen, Render-URL notieren (z.B. `https://dein-bot.onrender.com`).

## 7. Eigene Telegram-User-ID herausfinden

Dem Bot in Telegram `/start` schreiben (funktioniert erst nachdem `ALLOWED_TELEGRAM_USER_ID`
vorläufig auf irgendeinen Wert gesetzt und der Webhook (Schritt 8) gesetzt ist — oder
einfacher: `/start` an [@userinfobot](https://t.me/userinfobot) schreiben, der zeigt die
eigene ID sofort). ID danach in Render unter `ALLOWED_TELEGRAM_USER_ID` eintragen und
Service neu deployen lassen.

## 8. Telegram-Webhook setzen

Einmalig im eigenen Terminal (Token und Render-URL ersetzen):

```bash
curl "https://api.telegram.org/bot<DEIN_TOKEN>/setWebhook?url=https://dein-bot.onrender.com/webhook"
```

Antwort sollte `"ok":true` enthalten.

## 9. Keep-Alive + morgendliche Erinnerung einrichten

Der Endpoint `/cron/tick?token=<CRON_SECRET>` hält den Server wach **und** verschickt um
7:00 Uhr (Europe/Berlin) die Trainings-Erinnerung für den Tag — beides in einem Aufruf,
ausgelöst von einem externen kostenlosen Ping-Dienst (kein GitHub-Actions-Cron, da das bei
einem privaten Repo das kostenlose Minutenkontingent sprengen würde):

1. Kostenlosen Account bei [cron-job.org](https://cron-job.org) anlegen.
2. Neuen Cronjob anlegen: URL = `https://dein-bot.onrender.com/cron/tick?token=<CRON_SECRET>`,
   Intervall = alle 10 Minuten.
3. Fertig — kein weiterer Code nötig.

## 10. Dashboard aufrufen

`https://dein-bot.onrender.com/dashboard?token=<DASHBOARD_TOKEN>` im Browser öffnen und als
Lesezeichen speichern. Zeigt Körpergewichts-Trend, eine Karte pro geloggter Übung mit
Verlaufs-Chart, sowie die letzten 20 Aktivitäten.

## Nutzung

- Beliebige Nachricht mit Übung + Zahlen senden, z.B. `Kniebeuge 4x5 100kg`.
- Körpergewicht: `Gewicht heute 84,2kg`.
- Cardio: `30 min 5 km Laufen`.
- `/verlauf Kniebeuge` (oder `/verlauf Gewicht`) — letzte Einträge als Text.
- `/chart Kniebeuge` (oder `/chart Gewicht`) — Liniendiagramm als Bild.
- Dashboard: siehe Schritt 10.

**Sicherheitshinweis:** `TELEGRAM_BOT_TOKEN` wurde im Rahmen der Einrichtung im Klartext
geteilt. Empfehlenswert (kein Muss): über @BotFather (`/mybots` → Bot auswählen →
API Token → Revoke current token) einmal neu generieren, danach `.env` und Render-Env-Var
aktualisieren.
