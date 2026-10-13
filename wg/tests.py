# Automatische Tests für Registrierung/Login und Feature F1 (WG erstellen & Mitbewohner einladen).
# Ausführen mit: python manage.py test
# Jeder Test prüft ein Akzeptanzkriterium. Django legt dafür eine leere Test-Datenbank an.

from django.contrib.auth import get_user_model            # Liefert das Benutzer-Modell von Django
from django.test import TestCase                          # Basisklasse für Tests; self.client simuliert einen Browser
from django.urls import reverse                           # Wandelt einen URL-Namen (z.B. "wg_detail") in die Adresse um

from .models import Mitgliedschaft, WG                    # Unsere Modelle, um Ergebnisse in der DB zu prüfen

User = get_user_model()                                   # Benutzer-Modell als Kurzname


def make_user(name):
    """Hilfsfunktion: legt einen Testbenutzer mit festem Passwort an."""
    return User.objects.create_user(name, password="pw12345!x")


class RegistrierungLoginTests(TestCase):
    """Konto erstellen und Zugriffsschutz für nicht eingeloggte Benutzer."""

    def test_registrieren_loggt_ein(self):
        """Nach erfolgreicher Registrierung existiert das Konto und man landet auf der Startseite."""
        r = self.client.post(reverse("register"), {       # Registrierungsformular absenden
            "username": "lena", "password1": "geheim-Pass9", "password2": "geheim-Pass9"})
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)  # Weiterleitung zur Startseite?
        self.assertTrue(User.objects.filter(username="lena").exists())          # Konto in der DB?

    def test_login_noetig(self):
        """Ohne Login wird man von der WG-Seite zum Login weitergeleitet."""
        r = self.client.get(reverse("wg_detail"))         # WG-Seite ohne Login aufrufen
        self.assertEqual(r.status_code, 302)              # 302 = Weiterleitung
        self.assertIn(reverse("login"), r.url)            # ... und zwar zur Login-Seite


class WGErstellenTests(TestCase):
    """S1: Lena gründet eine WG."""

    def setUp(self):
        """Läuft vor jedem Test: Lena anlegen und einloggen."""
        self.lena = make_user("lena")
        self.client.force_login(self.lena)                # Einloggen ohne Passwort-Formular

    def test_ersteller_ist_admin_und_code_vorhanden(self):
        """Wer eine WG erstellt, wird Admin, und die WG hat einen Einladungscode."""
        self.client.post(reverse("wg_erstellen"), {"name": "WG Seeblick"})  # WG erstellen
        wg = WG.objects.get()                             # Genau eine WG muss existieren
        self.assertTrue(wg.einladungscode)                # Code darf nicht leer sein
        self.assertEqual(self.lena.mitgliedschaft.rolle, Mitgliedschaft.ADMIN)  # Lena ist Admin

    def test_leerer_name_wird_abgelehnt(self):
        """Ohne Namen wird keine WG erstellt, das Formular erscheint erneut."""
        r = self.client.post(reverse("wg_erstellen"), {"name": ""})  # Leeren Namen absenden
        self.assertEqual(r.status_code, 200)              # 200 = Seite wird erneut angezeigt (mit Fehler)
        self.assertFalse(WG.objects.exists())             # Es wurde keine WG gespeichert

    def test_home_ohne_wg_leitet_zu_start(self):
        """Wer noch keine WG hat, landet auf der Seite "WG erstellen / beitreten"."""
        self.assertRedirects(self.client.get(reverse("home")), reverse("wg_start"))

    def test_zweite_wg_nicht_moeglich(self):
        """Ein Benutzer kann nicht zwei WGs erstellen."""
        self.client.post(reverse("wg_erstellen"), {"name": "A"})  # Erste WG
        self.client.post(reverse("wg_erstellen"), {"name": "B"})  # Zweiter Versuch
        self.assertEqual(WG.objects.count(), 1)           # Es gibt trotzdem nur eine WG


class BeitrittTests(TestCase):
    """S1: Sara tritt mit dem Einladungscode bei."""

    def setUp(self):
        """WG mit Lena als Admin anlegen, Sara (noch ohne WG) einloggen."""
        self.wg = WG.objects.create(name="WG")
        self.lena = make_user("lena")
        Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)
        self.sara = make_user("sara")
        self.client.force_login(self.sara)

    def test_beitritt_mit_gueltigem_code(self):
        """Mit dem richtigen Code wird Sara normales Mitglied dieser WG."""
        self.client.post(reverse("wg_beitreten"), {"code": self.wg.einladungscode})
        m = self.sara.mitgliedschaft                      # Saras Mitgliedschaft holen
        self.assertEqual(m.wg, self.wg)                   # Richtige WG?
        self.assertEqual(m.rolle, Mitgliedschaft.MITGLIED)  # Rolle = Mitglied, nicht Admin

    def test_beitritt_mit_ungueltigem_code(self):
        """Mit einem falschen Code passiert nichts, es erscheint eine Fehlermeldung."""
        r = self.client.post(reverse("wg_beitreten"), {"code": "falsch"})
        self.assertEqual(r.status_code, 200)              # Formular wird erneut angezeigt
        self.assertFalse(Mitgliedschaft.objects.filter(user=self.sara).exists())  # Sara ist nicht beigetreten

    def test_alter_code_nach_erneuern_ungueltig(self):
        """Nachdem der Admin den Code erneuert hat, funktioniert der alte Code nicht mehr."""
        alt = self.wg.einladungscode                      # Alten Code merken
        self.client.force_login(self.lena)                # Als Admin einloggen
        self.client.post(reverse("code_erneuern"))        # Code erneuern
        self.wg.refresh_from_db()                         # WG neu aus der DB laden
        self.assertNotEqual(alt, self.wg.einladungscode)  # Code hat sich geändert
        self.client.force_login(self.sara)                # Wieder als Sara
        self.client.post(reverse("wg_beitreten"), {"code": alt})  # Mit altem Code versuchen
        self.assertFalse(Mitgliedschaft.objects.filter(user=self.sara).exists())  # Beitritt abgelehnt

    def test_mitglied_kann_code_nicht_erneuern(self):
        """Nur Admins dürfen den Code erneuern."""
        Mitgliedschaft.objects.create(user=self.sara, wg=self.wg)  # Sara als normales Mitglied
        r = self.client.post(reverse("code_erneuern"))    # Versuch, den Code zu erneuern
        self.assertEqual(r.status_code, 403)              # 403 = Verboten


class VerwaltungTests(TestCase):
    """Admin verwaltet Mitglieder (entfernen, Rolle wechseln) – mit Rechteprüfung."""

    def setUp(self):
        """WG mit Lena (Admin) und Marco (Mitglied)."""
        self.wg = WG.objects.create(name="WG")
        self.lena = make_user("lena")
        self.marco = make_user("marco")
        self.ml = Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)  # Lenas Mitgliedschaft
        self.mm = Mitgliedschaft.objects.create(user=self.marco, wg=self.wg)                            # Marcos Mitgliedschaft

    def test_admin_entfernt_mitglied(self):
        """Der Admin kann ein Mitglied entfernen."""
        self.client.force_login(self.lena)
        self.client.post(reverse("mitglied_entfernen", args=[self.mm.pk]))  # Marco entfernen
        self.assertFalse(Mitgliedschaft.objects.filter(pk=self.mm.pk).exists())  # Marco ist weg

    def test_mitglied_darf_nicht_entfernen(self):
        """Ein normales Mitglied darf niemanden entfernen."""
        self.client.force_login(self.marco)
        r = self.client.post(reverse("mitglied_entfernen", args=[self.ml.pk]))  # Marco versucht Lena zu entfernen
        self.assertEqual(r.status_code, 403)              # Verboten
        self.assertTrue(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lena ist noch da

    def test_letzter_admin_bleibt(self):
        """Der einzige Admin kann weder entfernt noch herabgestuft werden."""
        self.client.force_login(self.lena)
        self.client.post(reverse("mitglied_entfernen", args=[self.ml.pk]))  # Sich selbst entfernen versuchen
        self.client.post(reverse("rolle_wechseln", args=[self.ml.pk]))      # Sich selbst herabstufen versuchen
        self.ml.refresh_from_db()                         # Neu laden (wirft Fehler, falls gelöscht)
        self.assertTrue(self.ml.ist_admin)                # Lena ist weiterhin Admin

    def test_rolle_wechseln(self):
        """Der Admin kann ein Mitglied zum Admin machen."""
        self.client.force_login(self.lena)
        self.client.post(reverse("rolle_wechseln", args=[self.mm.pk]))  # Marcos Rolle wechseln
        self.mm.refresh_from_db()
        self.assertTrue(self.mm.ist_admin)                # Marco ist jetzt Admin

    def test_fremde_wg_nicht_verwaltbar(self):
        """Ein Admin kann keine Mitglieder einer anderen WG entfernen."""
        andere = WG.objects.create(name="Andere")         # Zweite, fremde WG
        x = Mitgliedschaft.objects.create(user=make_user("x"), wg=andere)  # Mitglied dort
        self.client.force_login(self.lena)
        r = self.client.post(reverse("mitglied_entfernen", args=[x.pk]))  # Lena versucht x zu entfernen
        self.assertEqual(r.status_code, 404)              # 404 = für Lena existiert diese Mitgliedschaft nicht

    def test_detail_zeigt_mitglieder(self):
        """Die WG-Übersicht zeigt alle Mitbewohner an."""
        self.client.force_login(self.marco)
        r = self.client.get(reverse("wg_detail"))         # WG-Seite als Marco öffnen
        self.assertContains(r, "lena")                    # Lena steht in der Liste


class VerlassenTests(TestCase):
    """US-F1-06: Ein Mitglied verlässt die WG selbst."""

    def setUp(self):
        """WG mit Lena (Admin) und Marco (Mitglied)."""
        self.wg = WG.objects.create(name="WG")
        self.lena = make_user("lena")
        self.marco = make_user("marco")
        self.ml = Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)  # Lenas Mitgliedschaft
        self.mm = Mitgliedschaft.objects.create(user=self.marco, wg=self.wg)                            # Marcos Mitgliedschaft

    def test_mitglied_verlaesst_wg(self):
        """Nach dem Verlassen ist Marco kein Mitglied mehr und landet auf "WG gründen oder beitreten"."""
        self.client.force_login(self.marco)
        r = self.client.post(reverse("wg_verlassen"))     # Austritt bestätigen
        self.assertRedirects(r, reverse("wg_start"))      # Weiter zur Startseite ohne WG
        self.assertFalse(Mitgliedschaft.objects.filter(user=self.marco).exists())  # Marco ist nicht mehr Mitglied
        self.assertTrue(WG.objects.filter(pk=self.wg.pk).exists())                 # Die WG gibt es weiterhin

    def test_verlassen_braucht_bestaetigung(self):
        """Das blosse Aufrufen der Seite (ohne Bestätigen) ändert nichts."""
        self.client.force_login(self.marco)
        r = self.client.get(reverse("wg_verlassen"))      # Nur die Bestätigungsseite öffnen
        self.assertEqual(r.status_code, 200)              # Seite wird angezeigt
        self.assertTrue(Mitgliedschaft.objects.filter(user=self.marco).exists())  # Marco ist noch Mitglied

    def test_einziger_admin_kann_nicht_verlassen(self):
        """Lena ist einzige Admin und Marco ist noch da: Sie muss zuerst die Admin-Rolle weitergeben."""
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))         # Austritt versuchen
        self.assertTrue(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lena ist weiterhin Mitglied

    def test_admin_kann_nach_rollenweitergabe_verlassen(self):
        """Gibt es einen zweiten Admin, darf Lena gehen."""
        self.mm.rolle = Mitgliedschaft.ADMIN              # Marco zum Admin machen
        self.mm.save()
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))         # Austritt
        self.assertFalse(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lena ist weg

    def test_letzte_person_loescht_wg(self):
        """Verlässt die letzte Person die WG, wird die WG gelöscht."""
        self.mm.delete()                                  # Marco ist schon weg, Lena ist allein
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))         # Austritt
        self.assertFalse(WG.objects.filter(pk=self.wg.pk).exists())  # WG existiert nicht mehr

    def test_nach_verlassen_neu_beitreten(self):
        """Wer gegangen ist, kann mit einem Code wieder einer WG beitreten."""
        self.client.force_login(self.marco)
        self.client.post(reverse("wg_verlassen"))         # Austritt
        self.client.post(reverse("wg_beitreten"), {"code": self.wg.einladungscode})  # Wieder beitreten
        self.assertTrue(Mitgliedschaft.objects.filter(user=self.marco, wg=self.wg).exists())  # Marco ist wieder dabei


class LoeschenTests(TestCase):
    """US-F1-08: Ein Admin löscht die ganze WG."""

    def setUp(self):
        """WG mit Lena (Admin) und Marco (Mitglied)."""
        self.wg = WG.objects.create(name="WG")
        self.lena = make_user("lena")
        self.marco = make_user("marco")
        Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)
        Mitgliedschaft.objects.create(user=self.marco, wg=self.wg)

    def test_admin_loescht_wg(self):
        """Nach dem Löschen gibt es weder die WG noch Mitgliedschaften, die Konten bleiben aber bestehen."""
        self.client.force_login(self.lena)
        r = self.client.post(reverse("wg_loeschen"))      # Löschen bestätigen
        self.assertRedirects(r, reverse("wg_start"))      # Weiter zur Startseite ohne WG
        self.assertFalse(WG.objects.exists())             # WG ist weg
        self.assertFalse(Mitgliedschaft.objects.exists()) # Alle Mitgliedschaften sind weg
        self.assertTrue(User.objects.filter(username="marco").exists())  # Marcos Konto existiert noch

    def test_loeschen_braucht_bestaetigung(self):
        """Das blosse Aufrufen der Seite (ohne Bestätigen) löscht nichts."""
        self.client.force_login(self.lena)
        r = self.client.get(reverse("wg_loeschen"))       # Nur die Bestätigungsseite öffnen
        self.assertEqual(r.status_code, 200)              # Seite wird angezeigt
        self.assertTrue(WG.objects.exists())              # WG gibt es noch

    def test_mitglied_darf_nicht_loeschen(self):
        """Ein normales Mitglied darf die WG nicht löschen."""
        self.client.force_login(self.marco)
        r = self.client.post(reverse("wg_loeschen"))      # Marco versucht zu löschen
        self.assertEqual(r.status_code, 403)              # 403 = Verboten
        self.assertTrue(WG.objects.exists())              # WG gibt es noch
