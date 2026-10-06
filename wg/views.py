# Views der App "wg". Eine View nimmt eine Anfrage (request) entgegen und gibt eine Antwort zurück
# (eine HTML-Seite oder eine Weiterleitung).

from django.contrib import messages                       # Kurze Meldungen oben auf der Seite ("WG erstellt.")
from django.contrib.auth.decorators import login_required # Nur für eingeloggte Benutzer
from django.shortcuts import get_object_or_404, redirect, render  # Objekt holen oder 404 / weiterleiten / Seite anzeigen
from django.views.decorators.http import require_POST     # Erlaubt nur POST (Formular-Absenden), sonst Fehler 405

from .forms import BeitrittForm, WGForm                   # Unsere Formulare aus wg/forms.py
from .models import Mitgliedschaft, WG, neuer_einladungscode  # Modelle und Code-Generator aus wg/models.py
from .permissions import nur_wg_admin, nur_wg_mitglied    # Zugriffsschutz aus wg/permissions.py


def _hat_wg(user):
    """Hilfsfunktion: True, wenn der Benutzer schon in einer WG ist."""
    return Mitgliedschaft.objects.filter(user=user).exists()


@login_required
def home(request):
    """Startseite "/": leitet je nach Situation weiter."""
    if _hat_wg(request.user):                             # Schon in einer WG?
        return redirect("wg_detail")                      # -> WG-Übersicht
    return redirect("wg_start")                           # Sonst -> WG erstellen oder beitreten


@login_required
def wg_start(request):
    """Seite für Benutzer ohne WG: zeigt die Formulare "WG erstellen" und "Beitreten"."""
    if _hat_wg(request.user):                             # Wer schon eine WG hat, braucht diese Seite nicht
        return redirect("wg_detail")
    return render(request, "wg/start.html", {             # Seite mit zwei leeren Formularen anzeigen
        "erstellen_form": WGForm(),
        "beitritt_form": BeitrittForm(),
    })


@login_required
@require_POST
def wg_erstellen(request):
    """Legt eine neue WG an. Der Ersteller wird automatisch Admin."""
    if _hat_wg(request.user):                             # Nur eine WG pro Benutzer erlaubt
        return redirect("wg_detail")
    form = WGForm(request.POST)                           # Formular mit den eingegebenen Daten füllen
    if form.is_valid():                                   # Name vorhanden und nicht zu lang?
        wg = form.save()                                  # WG speichern (Einladungscode wird automatisch erzeugt)
        Mitgliedschaft.objects.create(                    # Ersteller als Mitglied eintragen ...
            user=request.user, wg=wg, rolle=Mitgliedschaft.ADMIN,  # ... und zwar als Admin
        )
        messages.success(request, f"WG «{wg.name}» erstellt.")    # Erfolgsmeldung
        return redirect("wg_detail")                      # Weiter zur WG-Übersicht
    return render(request, "wg/start.html", {             # Fehler: Seite nochmal mit Fehlermeldungen zeigen
        "erstellen_form": form,
        "beitritt_form": BeitrittForm(),
    })


@login_required
@require_POST
def wg_beitreten(request):
    """Tritt einer bestehenden WG mit dem Einladungscode bei."""
    if _hat_wg(request.user):                             # Nur eine WG pro Benutzer erlaubt
        return redirect("wg_detail")
    form = BeitrittForm(request.POST)                     # Formular mit dem eingegebenen Code füllen
    if form.is_valid():                                   # Code gültig? (Prüfung in BeitrittForm.clean_code)
        Mitgliedschaft.objects.create(user=request.user, wg=form.wg)    # Als normales Mitglied eintragen
        messages.success(request, f"Du bist «{form.wg.name}» beigetreten.")  # Erfolgsmeldung
        return redirect("wg_detail")                      # Weiter zur WG-Übersicht
    return render(request, "wg/start.html", {             # Ungültiger Code: Seite mit Fehlermeldung zeigen
        "erstellen_form": WGForm(),
        "beitritt_form": form,
    })


@nur_wg_mitglied
def wg_detail(request):
    """Übersicht der eigenen WG: Name, Einladungscode, Mitgliederliste."""
    return render(request, "wg/detail.html", {
        "wg": request.wg,                                 # Die eigene WG (gesetzt von @nur_wg_mitglied)
        "mitgliedschaften": request.wg.mitgliedschaften.select_related("user"),  # Alle Mitglieder inkl. Benutzerdaten in einer Abfrage
        "ist_admin": request.mitgliedschaft.ist_admin,    # Steuert, ob Verwaltungs-Buttons angezeigt werden
    })


def _letzter_admin(m):
    """True, wenn m der einzige Admin der WG ist. Dann darf m weder entfernt noch herabgestuft werden,
    sonst könnte niemand mehr die WG verwalten."""
    return m.ist_admin and m.wg.mitgliedschaften.filter(rolle=Mitgliedschaft.ADMIN).count() == 1


@nur_wg_admin
@require_POST
def mitglied_entfernen(request, pk):
    """Admin entfernt ein Mitglied aus der WG."""
    m = get_object_or_404(Mitgliedschaft, pk=pk, wg=request.wg)  # Nur Mitglieder der eigenen WG, sonst 404
    if _letzter_admin(m):                                 # Letzten Admin schützen
        messages.error(request, "Der letzte Admin kann nicht entfernt werden.")
    else:
        m.delete()                                        # Mitgliedschaft löschen (Benutzerkonto bleibt bestehen)
        messages.success(request, f"{m.user.username} wurde entfernt.")
    return redirect("wg_detail")                          # Zurück zur WG-Übersicht


@nur_wg_admin
@require_POST
def rolle_wechseln(request, pk):
    """Admin wechselt die Rolle eines Mitglieds: Mitglied <-> Admin."""
    m = get_object_or_404(Mitgliedschaft, pk=pk, wg=request.wg)  # Nur Mitglieder der eigenen WG, sonst 404
    if _letzter_admin(m):                                 # Letzten Admin nicht herabstufen
        messages.error(request, "Es muss mindestens ein Admin bleiben.")
    else:
        m.rolle = Mitgliedschaft.MITGLIED if m.ist_admin else Mitgliedschaft.ADMIN  # Rolle umdrehen
        m.save()                                          # Änderung speichern
    return redirect("wg_detail")                          # Zurück zur WG-Übersicht


@nur_wg_admin
@require_POST
def code_erneuern(request):
    """Admin erzeugt einen neuen Einladungscode. Der alte Code funktioniert danach nicht mehr."""
    request.wg.einladungscode = neuer_einladungscode()    # Neuen Zufallscode setzen
    request.wg.save()                                     # Speichern
    messages.success(request, "Neuer Einladungscode erzeugt.")
    return redirect("wg_detail")                          # Zurück zur WG-Übersicht
