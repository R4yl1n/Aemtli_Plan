# URL-Routen der App "wg" (werden in aemtli_plan/urls.py ohne Präfix eingebunden).
# Format: path("adresse/", view-funktion, name="name-für-{% url %}-und-redirect")

from django.urls import path                              # Funktion, um eine URL einer View zuzuordnen

from . import views                                       # Die Views aus wg/views.py

urlpatterns = [
    path("", views.home, name="home"),                                       # /  -> Startseite, leitet weiter
    path("wg/start/", views.wg_start, name="wg_start"),                      # WG erstellen oder beitreten (Seite)
    path("wg/erstellen/", views.wg_erstellen, name="wg_erstellen"),          # Formular "WG erstellen" absenden
    path("wg/beitreten/", views.wg_beitreten, name="wg_beitreten"),          # Formular "Beitreten" absenden
    path("wg/", views.wg_detail, name="wg_detail"),                          # Übersicht der eigenen WG
    path("wg/mitglied/<int:pk>/entfernen/", views.mitglied_entfernen, name="mitglied_entfernen"),  # Mitglied entfernen (pk = ID der Mitgliedschaft)
    path("wg/mitglied/<int:pk>/rolle/", views.rolle_wechseln, name="rolle_wechseln"),              # Rolle wechseln
    path("wg/code-erneuern/", views.code_erneuern, name="code_erneuern"),    # Neuen Einladungscode erzeugen
]
