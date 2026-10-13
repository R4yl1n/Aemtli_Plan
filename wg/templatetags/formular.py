# Template-Filter, damit Django-Formularfelder mit Bootstrap-Klassen ausgegeben werden.
# Verwendung im Template: {% load formular %} und dann {{ feld|bootstrap }}
# Wird vom gemeinsamen Formular-Baustein templates/includes/formular.html genutzt.

from django import forms                                  # Für die Widget-Typen (Checkbox, Auswahlliste)
from django import template                               # Basis, um eigene Template-Filter zu registrieren

register = template.Library()                             # Sammelt die Filter dieser Datei, Django findet sie über {% load formular %}


@register.filter
def bootstrap(feld):
    """Gibt das Eingabefeld mit der passenden Bootstrap-Klasse aus (rot umrandet, falls ein Fehler vorliegt)."""
    widget = feld.field.widget                            # Das HTML-Element hinter dem Feld (Textfeld, Checkbox, ...)
    if isinstance(widget, forms.CheckboxInput):           # Einzelne Checkbox
        klasse = "form-check-input"                       # Bootstrap-Klasse für Checkboxen
    elif isinstance(widget, forms.Select):                # Auswahlliste (Dropdown)
        klasse = "form-select"                            # Bootstrap-Klasse für Dropdowns
    else:                                                 # Alle anderen: Text, Passwort, Zahl, Datum ...
        klasse = "form-control"                           # Bootstrap-Klasse für normale Eingabefelder
    if feld.errors:                                       # Hat das Feld einen Fehler?
        klasse += " is-invalid"                           # Dann rot umranden
    return feld.as_widget(attrs={"class": klasse})        # Feld als HTML mit dieser Klasse ausgeben
