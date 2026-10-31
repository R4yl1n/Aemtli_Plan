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

    def clean(self):
        """Sucht die WG zum Code und legt sie in cleaned_data["wg"] ab.
        So liefert das Formular alles, was die View braucht, über cleaned_data statt über ein
        zusätzliches Attribut, das nur nach is_valid() existiert."""
        cleaned_data = super().clean()
        code = cleaned_data.get("code")                   # Fehlt, wenn das Feld schon leer/ungültig war
        if code:                                          # Leerzeichen am Rand entfernt das CharField bereits selbst
            try:
                cleaned_data["wg"] = WG.objects.get(einladungscode=code)
            except WG.DoesNotExist:
                self.add_error("code", "Ungültiger Einladungscode.")  # Fehler direkt beim Feld anzeigen
        return cleaned_data
