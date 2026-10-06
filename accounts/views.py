# Views der App "accounts": alles rund um Benutzerkonten.
# Login und Logout liefert Django selbst (siehe accounts/urls.py),
# hier steht nur die Registrierung, weil Django dafür keine fertige View hat.

from django.contrib.auth import login                     # Funktion, die einen Benutzer einloggt (Session setzen)
from django.contrib.auth.forms import UserCreationForm    # Fertiges Django-Formular: Benutzername + Passwort zweimal
from django.shortcuts import redirect, render             # redirect = weiterleiten, render = HTML-Template ausgeben


def register(request):
    """Zeigt das Registrierungsformular an und legt beim Absenden ein neues Konto an."""
    if request.method == "POST":                          # Formular wurde abgeschickt
        form = UserCreationForm(request.POST)             # Formular mit den eingegebenen Daten füllen
        if form.is_valid():                               # Prüft z.B. ob Benutzername frei und Passwörter gleich sind
            user = form.save()                            # Neuen Benutzer in der Datenbank speichern
            login(request, user)                          # Direkt einloggen, damit man sich nicht nochmal anmelden muss
            return redirect("home")                       # Weiter zur Startseite
    else:                                                 # Seite wird nur aufgerufen (GET)
        form = UserCreationForm()                         # Leeres Formular erzeugen
    # Formular anzeigen: entweder leer oder mit Fehlermeldungen, falls is_valid() fehlgeschlagen ist
    return render(request, "accounts/register.html", {"form": form})
