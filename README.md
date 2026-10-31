# Ämtli

Web-App für Wohngemeinschaften: Ämtliplan mit automatischer wöchentlicher Rotation, gemeinsame Ausgaben mit Saldo («wer schuldet wem») und Mitbewohner-Einladung per Code. Gebaut mit Django und SQLite.

## Starten

Python 3.14 (getestet), dann:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Die App läuft danach unter http://127.0.0.1:8000/.

## Umgebungsvariablen

Beide sind optional. Ohne sie läuft die App lokal mit Entwicklungs-Einstellungen.

| Variable | Bedeutung | Standard |
|---|---|---|
| `DJANGO_SECRET_KEY` | Geheimer Schlüssel von Django | unsicherer Entwicklungs-Schlüssel |
| `DJANGO_DEBUG` | `1` = Debug-Modus an, `0` = aus | `1` |

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY='...' python manage.py runserver
```

Hinweis: Mit `DJANGO_DEBUG=0` muss zusätzlich `ALLOWED_HOSTS` in `aemtli_plan/settings.py` gesetzt sein.

## Tests

```bash
python manage.py test
```
