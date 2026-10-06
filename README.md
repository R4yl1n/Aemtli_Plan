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

## Tests

```bash
python manage.py test
```
