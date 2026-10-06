# Formulare der App "wg". Ein Formular prüft Benutzereingaben, bevor wir sie speichern.

from django import forms                                  # Basis für alle Django-Formulare

from .models import WG                                    # Das WG-Modell, für das wir ein Formular brauchen


class WGForm(forms.ModelForm):
    """Formular zum Erstellen einer WG. Wird automatisch aus dem WG-Modell erzeugt."""
    class Meta:
        model = WG                                        # Formular basiert auf dem WG-Modell
        fields = ["name"]                                 # Nur der Name wird eingegeben (Code wird automatisch erzeugt)
        labels = {"name": "Name der WG"}                  # Beschriftung des Eingabefelds


class BeitrittForm(forms.Form):
    """Formular zum Beitreten einer WG mit einem Einladungscode."""
    code = forms.CharField(label="Einladungscode", max_length=32)  # Eingabefeld für den Code

    def clean_code(self):
        """Wird von Django automatisch aufgerufen, um das Feld 'code' zu prüfen."""
        code = self.cleaned_data["code"].strip()          # Eingabe holen und Leerzeichen am Rand entfernen
        try:
            self.wg = WG.objects.get(einladungscode=code) # WG mit diesem Code suchen und merken
        except WG.DoesNotExist:                           # Keine WG gefunden
            raise forms.ValidationError("Ungültiger Einladungscode.")  # Fehlermeldung beim Feld anzeigen
        return code                                       # Gültigen Code zurückgeben
