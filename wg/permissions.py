# Zugriffsschutz für Views, als Decorators.
# Diese werden auch von den anderen Apps (aemtli, finanzen) wiederverwendet.
# Verwendung: @nur_wg_mitglied oder @nur_wg_admin direkt über eine View-Funktion schreiben.

from functools import wraps                               # Behält Name/Doku der Original-View beim Einpacken

from django.contrib.auth.decorators import login_required # Djangos Decorator: leitet nicht eingeloggte Benutzer zum Login
from django.core.exceptions import PermissionDenied       # Fehler, der zu einer "403 Verboten"-Antwort führt
from django.shortcuts import redirect                     # Weiterleitung auf eine andere Seite


def nur_wg_mitglied(view):
    """Erlaubt die View nur eingeloggten Benutzern mit einer AKTIVEN Mitgliedschaft.
    Wer ausgetreten ist, gilt als "ohne WG", auch wenn die alte Mitgliedschaft noch in der DB steht.
    Setzt danach request.mitgliedschaft und request.wg, damit die View sie direkt nutzen kann."""
    @wraps(view)
    @login_required                                       # Schritt 1: nicht eingeloggt -> zum Login
    def wrapper(request, *args, **kwargs):
        m = request.user.aktive_mitgliedschaft            # Schritt 2: aktive Mitgliedschaft holen (oder None)
        if m is None:                                     # Benutzer ist in keiner WG (mehr)
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
