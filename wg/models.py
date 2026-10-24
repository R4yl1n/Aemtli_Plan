from django.db import models
from django.db.models import Q, UniqueConstraint
from accounts.models import Benutzer
import uuid  # <-- NEU: Import für den Code-Generator

# <-- NEU: Die fehlende Funktion, die von views.py gesucht wird
def neuer_einladungscode():
    return uuid.uuid4().hex  # Generiert einen zufälligen, 32-stelligen String

class WG(models.Model):
    name = models.CharField(max_length=100)
    # Sie können die Funktion hier auch direkt als Standardwert (default) setzen, falls gewünscht:
    einladungscode = models.CharField(max_length=32, unique=True, default=neuer_einladungscode)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Mitgliedschaft(models.Model):
    class Rolle(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MITGLIED = 'mitglied', 'Mitglied'

    user = models.ForeignKey(Benutzer, on_delete=models.CASCADE, related_name='mitgliedschaften')
    wg = models.ForeignKey(WG, on_delete=models.CASCADE, related_name='mitglieder')
    rolle = models.CharField(max_length=10, choices=Rolle.choices, default=Rolle.MITGLIED)
    beigetreten_am = models.DateTimeField(auto_now_add=True)
    ausgetreten_am = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user'], 
                condition=Q(ausgetreten_am__isnull=True), 
                name='unique_active_user_membership'
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.wg}"