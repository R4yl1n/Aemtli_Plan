# Views der App "accounts": alles rund um Benutzerkonten.
# Login und Logout liefert Django selbst (siehe accounts/urls.py),
# hier steht nur die Registrierung, weil Django dafür keine fertige View hat.

from django.contrib.auth import login                     # Funktion, die einen Benutzer einloggt (Session setzen)
from django.shortcuts import redirect, render             # redirect = weiterleiten, render = HTML-Template ausgeben

from .forms import RegistrierungForm                      # Benutzername + Passwort zweimal, speichert in accounts.Benutzer


def register(request):
    """Zeigt das Registrierungsformular an und legt beim Absenden ein neues Konto an."""
    if request.user.is_authenticated:                     # Wer eingeloggt ist, braucht kein zweites Konto;
        return redirect("home")                           # sonst würde login() unten die aktuelle Sitzung ersetzen
    if request.method == "POST":                          # Formular wurde abgeschickt
        form = RegistrierungForm(request.POST)             # Formular mit den eingegebenen Daten füllen
        if form.is_valid():                               # Prüft z.B. ob Benutzername frei und Passwörter gleich sind
            user = form.save()                            # Neuen Benutzer in der Datenbank speichern
            login(request, user)                          # Direkt einloggen, damit man sich nicht nochmal anmelden muss
            return redirect("home")                       # Weiter zur Startseite
    else:                                                 # Seite wird nur aufgerufen (GET)
        form = RegistrierungForm()                         # Leeres Formular erzeugen
    # Formular anzeigen: entweder leer oder mit Fehlermeldungen, falls is_valid() fehlgeschlagen ist
    return render(request, "accounts/register.html", {"form": form})
