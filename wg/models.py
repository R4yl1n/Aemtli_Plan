# Datenmodelle der App "wg": die WG selbst und wer darin Mitglied ist.
# Jede Klasse hier wird von Django zu einer Tabelle in der Datenbank.

import secrets                                            # Python-Modul für sichere Zufallswerte (für den Einladungscode)

from django.conf import settings                          # Zugriff auf settings.py (für AUTH_USER_MODEL)
from django.db import models                              # Basis für alle Django-Modelle und Feldtypen


def neuer_einladungscode():
    """Erzeugt einen zufälligen, schwer erratbaren Code wie 'aZ3k_9Qp1xY'."""
    return secrets.token_urlsafe(8)                       # 8 Zufalls-Bytes -> ca. 11 Zeichen, URL-tauglich


class WG(models.Model):
    """Eine Wohngemeinschaft."""
    name = models.CharField(max_length=100)               # Name der WG, z.B. "WG Seeblick" (Pflichtfeld)
    einladungscode = models.CharField(                    # Code, mit dem neue Mitbewohner beitreten
        max_length=32,                                    # maximal 32 Zeichen
        unique=True,                                      # darf nur bei einer WG vorkommen
        default=neuer_einladungscode,                     # wird beim Erstellen automatisch erzeugt
    )
    erstellt_am = models.DateTimeField(auto_now_add=True) # Zeitpunkt der Erstellung, wird automatisch gesetzt

    def __str__(self):
        return self.name                                  # So wird die WG als Text angezeigt (z.B. in der Shell)


class Mitgliedschaft(models.Model):
    """Verbindet einen Benutzer mit einer WG und legt seine Rolle fest."""
    ADMIN = "admin"                                       # Wert für die Admin-Rolle (darf verwalten)
    MITGLIED = "mitglied"                                 # Wert für normale Mitbewohner
    ROLLEN = [(ADMIN, "Admin"), (MITGLIED, "Mitglied")]   # Auswahl: (Wert in der DB, Anzeigename)

    user = models.OneToOneField(                          # OneToOne = ein Benutzer gehört zu genau einer WG
        settings.AUTH_USER_MODEL,                         # verweist auf Djangos Benutzer-Tabelle
        on_delete=models.CASCADE,                         # wird der Benutzer gelöscht, verschwindet auch die Mitgliedschaft
        related_name="mitgliedschaft",                    # erlaubt user.mitgliedschaft im Code
    )
    wg = models.ForeignKey(                               # ForeignKey = viele Mitgliedschaften gehören zu einer WG
        WG,                                               # verweist auf die WG-Tabelle
        on_delete=models.CASCADE,                         # wird die WG gelöscht, verschwinden alle Mitgliedschaften
        related_name="mitgliedschaften",                  # erlaubt wg.mitgliedschaften.all() im Code
    )
    rolle = models.CharField(max_length=10, choices=ROLLEN, default=MITGLIED)  # Rolle, standardmässig "Mitglied"
    beigetreten_am = models.DateTimeField(auto_now_add=True)                   # Zeitpunkt des Beitritts, automatisch

    class Meta:
        ordering = ["beigetreten_am"]                     # Mitglieder immer in Beitrittsreihenfolge sortieren

    @property
    def ist_admin(self):
        """True, wenn diese Person Admin der WG ist. Aufruf ohne Klammern: m.ist_admin"""
        return self.rolle == self.ADMIN

    def __str__(self):
        return f"{self.user} in {self.wg}"                # Textanzeige, z.B. "lena in WG Seeblick"
