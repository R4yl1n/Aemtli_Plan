# URL-Routen der App "accounts" (werden in aemtli_plan/urls.py unter /accounts/ eingebunden).

from django.contrib.auth import views as auth_views       # Djangos fertige Login-/Logout-Views
from django.urls import path                              # Funktion, um eine URL einer View zuzuordnen

from . import views                                       # Unsere eigenen Views (register)

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),       # /accounts/login/   -> Login-Seite (Template: registration/login.html)
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),    # /accounts/logout/  -> Ausloggen (nur per POST erlaubt)
    path("register/", views.register, name="register"),                 # /accounts/register/ -> Konto erstellen
]
