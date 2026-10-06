# Haupt-URL-Datei des Projekts: verteilt Anfragen an die URL-Dateien der einzelnen Apps.
# Hinweis: Die Django-Admin-Seite ist absichtlich nicht eingebunden (Projektvorgabe).

from django.urls import include, path                     # include = URL-Datei einer App einbinden

urlpatterns = [
    path('accounts/', include('accounts.urls')),          # /accounts/... -> Login, Logout, Registrierung
    path('', include('wg.urls')),                         # /  und /wg/... -> Startseite und WG-Verwaltung
]
