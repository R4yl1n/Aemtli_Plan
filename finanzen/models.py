from django.db import models
from django.conf import settings
from wg.models import WG  # Cross-App Import

class Ausgabe(models.Model):
    wg = models.ForeignKey(WG, on_delete=models.CASCADE, related_name='ausgaben')
    zahler = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bezahlte_ausgaben')
    beschreibung = models.CharField(max_length=200)

    def __str__(self):
        return self.beschreibung