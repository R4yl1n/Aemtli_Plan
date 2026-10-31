# Formulare der App "accounts".

from django.contrib.auth.forms import UserCreationForm

from .models import Benutzer


class RegistrierungForm(UserCreationForm):
    """Djangos UserCreationForm ist fest an auth.User gebunden. Ohne diese Unterklasse würde die
    Registrierung Konten in der falschen Tabelle anlegen (bzw. fehlschlagen)."""

    class Meta(UserCreationForm.Meta):
        model = Benutzer
        fields = ("username",)
