# Datenmodell der App "accounts".

from django.contrib.auth.models import AbstractUser


class Benutzer(AbstractUser):
    """Benutzerkonto der App.

    Erbt von AbstractUser statt von models.Model, damit Login, Logout, Passwort-Hashing und
    request.user direkt mit diesem Modell funktionieren. In settings.py als AUTH_USER_MODEL eingetragen.
    Ein eigenes Modell (statt auth.User) erlaubt es, später Felder zu ergänzen, ohne die
    Migrationen neu aufsetzen zu müssen.
    """

    @property
    def aktive_mitgliedschaft(self):
        """Die aktuelle Mitgliedschaft oder None.
        Ausgetretene Mitgliedschaften bleiben als Historie in der DB, zählen hier aber nicht.
        Die DB stellt sicher, dass es höchstens eine aktive gibt (siehe wg.models.Mitgliedschaft)."""
        return self.mitgliedschaften.filter(ausgetreten_am__isnull=True).select_related("wg").first()
