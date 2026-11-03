# Views der App "wg": WG erstellen, beitreten, verwalten, verlassen und löschen (Feature F1).

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BeitrittForm, WGForm
from .models import Mitgliedschaft, WG, neuer_einladungscode
from .permissions import nur_wg_admin, nur_wg_mitglied


def _hat_wg(user):
    """True, wenn der Benutzer eine aktive Mitgliedschaft hat. Ausgetretene zählen nicht."""
    return Mitgliedschaft.objects.aktive().filter(user=user).exists()


@login_required
def home(request):
    """Startseite "/": mit WG zur Übersicht, ohne WG zu "erstellen oder beitreten"."""
    if _hat_wg(request.user):
        return redirect("wg_detail")
    return redirect("wg_start")


@login_required
def wg_start(request):
    """Seite für Benutzer ohne WG: zeigt die Formulare "WG erstellen" und "Beitreten"."""
    if _hat_wg(request.user):
        return redirect("wg_detail")
    return render(request, "wg/start.html", {
        "erstellen_form": WGForm(),
        "beitritt_form": BeitrittForm(),
    })


@login_required
@require_POST
def wg_erstellen(request):
    """Legt eine neue WG an. Der Ersteller wird automatisch Admin."""
    if _hat_wg(request.user):                             # Höchstens eine aktive WG pro Benutzer
        return redirect("wg_detail")
    form = WGForm(request.POST)
    if form.is_valid():
        # WG und Admin-Mitgliedschaft gehören zusammen: entweder beide gespeichert oder keine.
        # Bei einem Doppelklick bestehen beide Requests _hat_wg(); der zweite scheitert erst am
        # UniqueConstraint. Ohne atomic() bliebe dann eine WG ohne Mitglieder zurück.
        try:
            with transaction.atomic():
                wg = form.save()
                Mitgliedschaft.objects.create(user=request.user, wg=wg, rolle=Mitgliedschaft.ADMIN)
        except IntegrityError:                            # Benutzer hat inzwischen schon eine aktive WG
            return redirect("wg_detail")
        messages.success(request, f"WG «{wg.name}» erstellt.")
        return redirect("wg_detail")
    return render(request, "wg/start.html", {             # Mit Fehlermeldungen erneut anzeigen
        "erstellen_form": form,
        "beitritt_form": BeitrittForm(),
    })


@login_required
@require_POST
def wg_beitreten(request):
    """Tritt einer bestehenden WG mit dem Einladungscode bei."""
    if _hat_wg(request.user):                             # Höchstens eine aktive WG pro Benutzer
        return redirect("wg_detail")
    form = BeitrittForm(request.POST)
    if form.is_valid():                                   # Code-Prüfung in BeitrittForm.clean
        wg = form.cleaned_data["wg"]
        # Gleicher Schutz wie bei wg_erstellen. atomic() setzt einen Savepoint, damit ein
        # IntegrityError die umgebende DB-Transaktion nicht unbrauchbar macht.
        try:
            with transaction.atomic():
                Mitgliedschaft.objects.create(user=request.user, wg=wg)
        except IntegrityError:                            # Benutzer hat inzwischen schon eine aktive WG
            return redirect("wg_detail")
        messages.success(request, f"Du bist «{wg.name}» beigetreten.")
        return redirect("wg_detail")
    return render(request, "wg/start.html", {             # Mit Fehlermeldung erneut anzeigen
        "erstellen_form": WGForm(),
        "beitritt_form": form,
    })


@nur_wg_mitglied
def wg_detail(request):
    """Übersicht der eigenen WG: Name, Einladungscode, aktive Mitglieder."""
    return render(request, "wg/detail.html", {
        "wg": request.wg,
        "mitgliedschaften": request.wg.mitglieder.aktive().select_related("user"),  # select_related: Benutzernamen ohne Zusatzabfrage pro Zeile
        "ist_admin": request.mitgliedschaft.ist_admin,    # Nur für die Anzeige der Buttons, die Views prüfen selbst
    })


def _letzter_admin(m):
    """True, wenn m der einzige aktive Admin der WG ist. Dann darf m weder entfernt noch herabgestuft
    werden, sonst könnte niemand mehr die WG verwalten."""
    return m.ist_admin and m.wg.mitglieder.aktive().filter(rolle=Mitgliedschaft.ADMIN).count() == 1


@nur_wg_admin
def mitglied_entfernen(request, pk):
    """Admin entfernt ein Mitglied aus der WG. GET zeigt eine Bestätigungsseite, POST führt es aus."""
    # Filter auf die eigene WG: Fremde oder bereits ausgetretene Mitgliedschaften ergeben 404
    m = get_object_or_404(Mitgliedschaft.objects.aktive(), pk=pk, wg=request.wg)
    if _letzter_admin(m):
        messages.error(request, "Der letzte Admin kann nicht entfernt werden.")
    elif request.method != "POST":                        # GET ändert nie etwas, sondern fragt nur nach
        return render(request, "wg/entfernen.html", {"mitgliedschaft": m})
    else:
        m.austreten()                                     # Austritt statt Löschen, damit die Historie erhalten bleibt
        messages.success(request, f"{m.user.username} wurde entfernt.")
    return redirect("wg_detail")


@nur_wg_admin
@require_POST
def rolle_wechseln(request, pk):
    """Admin wechselt die Rolle eines Mitglieds: Mitglied <-> Admin."""
    # Filter auf die eigene WG: Fremde oder bereits ausgetretene Mitgliedschaften ergeben 404
    m = get_object_or_404(Mitgliedschaft.objects.aktive(), pk=pk, wg=request.wg)
    if _letzter_admin(m):
        messages.error(request, "Es muss mindestens ein Admin bleiben.")
    else:
        m.rolle = Mitgliedschaft.MITGLIED if m.ist_admin else Mitgliedschaft.ADMIN
        m.save()
    return redirect("wg_detail")


@nur_wg_mitglied
def wg_verlassen(request):
    """Mitglied verlässt die WG selbst. GET zeigt eine Bestätigungsseite, POST führt den Austritt aus."""
    m = request.mitgliedschaft
    allein = request.wg.mitglieder.aktive().count() == 1
    # Der einzige Admin darf nur gehen, wenn sonst niemand mehr da ist, sonst bliebe die WG unverwaltbar
    if not allein and _letzter_admin(m):
        messages.error(request, "Bitte zuerst ein anderes Mitglied zum Admin machen.")
        return redirect("wg_detail")
    if request.method != "POST":                          # GET ändert nie etwas, sondern fragt nur nach
        return render(request, "wg/verlassen.html", {
            "wg": request.wg,
            "allein": allein,                             # Hinweis, dass die WG danach keine aktiven Mitglieder mehr hat
        })
    # Auch die letzte Person tritt nur aus: Die WG bleibt ohne aktive Mitglieder bestehen, damit
    # Ämtli- und Ausgaben-Historie nicht per CASCADE verloren geht. Hart löscht nur "WG löschen".
    with transaction.atomic():
        m.austreten()
        if allein:
            # Leere WG schliessen: Mit einem alten Code soll niemand die Historie einer aufgelösten
            # WG sehen können. Den Code ersetzen statt leeren, weil das Feld unique ist.
            request.wg.einladungscode = neuer_einladungscode()
            request.wg.save(update_fields=["einladungscode"])
    messages.success(request, f"Du hast «{request.wg.name}» verlassen.")
    return redirect("wg_start")


@nur_wg_admin
def wg_loeschen(request):
    """Admin löscht die ganze WG. GET zeigt eine Bestätigungsseite, POST löscht."""
    if request.method != "POST":                          # GET ändert nie etwas, sondern fragt nur nach
        return render(request, "wg/loeschen.html", {
            "wg": request.wg,
            "anzahl": request.wg.mitglieder.aktive().count(),
        })
    name = request.wg.name                                # Merken, bevor das Objekt gelöscht ist
    # Bewusst hartes Löschen: einzige Stelle, an der Historie verschwindet. Benutzerkonten bleiben bestehen.
    request.wg.delete()
    messages.success(request, f"Die WG «{name}» wurde gelöscht.")
    return redirect("wg_start")


@nur_wg_admin
@require_POST
def code_erneuern(request):
    """Admin erzeugt einen neuen Einladungscode. Der alte Code funktioniert danach nicht mehr,
    z.B. wenn er an die falsche Person ging."""
    request.wg.einladungscode = neuer_einladungscode()
    request.wg.save()
    messages.success(request, "Neuer Einladungscode erzeugt.")
    return redirect("wg_detail")
