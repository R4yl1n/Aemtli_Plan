from django.db import models
from django.db.models import UniqueConstraint
from django.conf import settings
from wg.models import WG  # Cross-App Import

class Aemtli(models.Model):
    wg = models.ForeignKey(WG, on_delete=models.CASCADE, related_name='aemtli')
    bezeichnung = models.CharField(max_length=100)
    beschreibung = models.TextField(blank=True, null=True)
    intervall_wochen = models.PositiveSmallIntegerField(default=1)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.bezeichnung


class AemtliZuteilung(models.Model):
    aemtli = models.ForeignKey(Aemtli, on_delete=models.CASCADE, related_name='zuteilungen')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='aemtli_zuteilungen')
    woche_start = models.DateField()
    erledigt_am = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['aemtli', 'woche_start'], 
                name='unique_aemtli_per_week'
            )
        ]

    def __str__(self):
        return f"{self.aemtli} ({self.woche_start})"