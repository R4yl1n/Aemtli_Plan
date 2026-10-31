# Datenmodelle der App "wg": die WG selbst und wer darin Mitglied ist.

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


def neuer_einladungscode():
    """Zufälliger 32-stelliger Code. uuid4 ist zufällig genug, dass man ihn nicht erraten kann."""
    return uuid.uuid4().hex


class WG(models.Model):
    """Eine Wohngemeinschaft."""
    name = models.CharField(max_length=100)
    einladungscode = models.CharField(max_length=32, unique=True, default=neuer_einladungscode)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MitgliedschaftQuerySet(models.QuerySet):
    def aktive(self):
        """Nur Mitgliedschaften, die nicht beendet sind. Fast jede Abfrage braucht diesen Filter,
        weil ausgetretene Mitglieder für Historie (Ämtli, Ausgaben) in der DB bleiben."""
        return self.filter(ausgetreten_am__isnull=True)


class Mitgliedschaft(models.Model):
    """Verbindet einen Benutzer mit einer WG und legt seine Rolle fest.

    Beim Austritt wird die Zeile nicht gelöscht, sondern ausgetreten_am gesetzt. So bleiben
    vergangene Ämtli-Zuteilungen und Ausgaben einer Person zuordenbar.
    """

    class Rolle(models.TextChoices):
        ADMIN = "admin", "Admin"
        MITGLIED = "mitglied", "Mitglied"

    # Kurzformen, damit Views und Tests Mitgliedschaft.ADMIN statt Mitgliedschaft.Rolle.ADMIN schreiben können
    ADMIN = Rolle.ADMIN
    MITGLIED = Rolle.MITGLIED

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mitgliedschaften")
    wg = models.ForeignKey(WG, on_delete=models.CASCADE, related_name="mitglieder")
    rolle = models.CharField(max_length=10, choices=Rolle.choices, default=Rolle.MITGLIED)
    beigetreten_am = models.DateTimeField(auto_now_add=True)
    ausgetreten_am = models.DateTimeField(blank=True, null=True)  # NULL = Mitgliedschaft ist aktiv

    objects = MitgliedschaftQuerySet.as_manager()

    class Meta:
        ordering = ["beigetreten_am"]  # Mitgliederliste in Beitrittsreihenfolge, unabhängig von der DB
        constraints = [
            # Regel "ein Benutzer, höchstens eine aktive WG" auf DB-Ebene. Eine Prüfung nur in der View
            # reicht nicht: zwei gleichzeitige Requests (Doppelklick) bestehen sie beide.
            UniqueConstraint(
                fields=["user"],
                condition=Q(ausgetreten_am__isnull=True),
                name="unique_active_user_membership",
            ),
        ]

    @property
    def ist_admin(self):
        return self.rolle == self.ADMIN

    def austreten(self):
        """Beendet die Mitgliedschaft, ohne die Zeile zu löschen (Historie bleibt erhalten)."""
        self.ausgetreten_am = timezone.now()
        self.save(update_fields=["ausgetreten_am"])

    def __str__(self):
        return f"{self.user} in {self.wg}"
