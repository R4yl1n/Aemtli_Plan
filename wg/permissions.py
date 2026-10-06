# Zugriffsschutz für Views, als Decorators.
# Diese werden auch von den anderen Apps (aemtli, finanzen) wiederverwendet.
# Verwendung: @nur_wg_mitglied oder @nur_wg_admin direkt über eine View-Funktion schreiben.

from functools import wraps                               # Behält Name/Doku der Original-View beim Einpacken

from django.contrib.auth.decorators import login_required # Djangos Decorator: leitet nicht eingeloggte Benutzer zum Login
from django.core.exceptions import PermissionDenied       # Fehler, der zu einer "403 Verboten"-Antwort führt
from django.shortcuts import redirect                     # Weiterleitung auf eine andere Seite

from .models import Mitgliedschaft                        # Wird gebraucht, um "hat keine WG" zu erkennen


def nur_wg_mitglied(view):
    """Erlaubt die View nur eingeloggten Benutzern, die in einer WG sind.
    Setzt danach request.mitgliedschaft und request.wg, damit die View sie direkt nutzen kann."""
    @wraps(view)
    @login_required                                       # Schritt 1: nicht eingeloggt -> zum Login
    def wrapper(request, *args, **kwargs):
        try:
            m = request.user.mitgliedschaft               # Schritt 2: Mitgliedschaft des Benutzers holen
        except Mitgliedschaft.DoesNotExist:               # Benutzer ist in keiner WG
            return redirect("wg_start")                   # -> zur Seite "WG erstellen / beitreten"
        request.mitgliedschaft = m                        # Für die View bereitstellen
        request.wg = m.wg                                 # Für die View bereitstellen (die eigene WG)
        return view(request, *args, **kwargs)             # Schritt 3: eigentliche View ausführen
    return wrapper


def nur_wg_admin(view):
    """Wie nur_wg_mitglied, aber zusätzlich muss der Benutzer Admin seiner WG sein."""
    @wraps(view)
    @nur_wg_mitglied                                      # Zuerst alle Prüfungen von nur_wg_mitglied
    def wrapper(request, *args, **kwargs):
        if not request.mitgliedschaft.ist_admin:          # Kein Admin?
            raise PermissionDenied                        # -> 403 Verboten
        return view(request, *args, **kwargs)             # Admin -> View ausführen
    return wrapper
