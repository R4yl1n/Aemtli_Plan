# Automatische Tests für Registrierung/Login und Feature F1 (WG erstellen & Mitbewohner einladen).
# Ausführen mit: python manage.py test
# Jeder Test prüft ein Akzeptanzkriterium. Django legt dafür eine leere Test-Datenbank an.

from unittest import mock                                 # Um die Vorabprüfung _hat_wg zu überspringen (simuliert Doppelklick)

from django.contrib.auth import get_user_model            # Liefert das Benutzer-Modell von Django
from django.db import IntegrityError, transaction         # Für den direkten Test des DB-Constraints
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

    def test_login_mit_korrektem_passwort(self):
        """Mit korrektem Passwort wird man eingeloggt und auf die Startseite "/" weitergeleitet."""
        make_user("lena")
        r = self.client.post(reverse("login"), {"username": "lena", "password": "pw12345!x"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)  # Session enthält den eingeloggten Benutzer

    def test_registrieren_als_eingeloggter_benutzer(self):
        """Wer schon eingeloggt ist, wird von der Registrierung weggeleitet, und es entsteht kein zweites Konto."""
        self.client.force_login(make_user("lena"))
        r = self.client.post(reverse("register"), {
            "username": "zweitkonto", "password1": "geheim-Pass9", "password2": "geheim-Pass9"})
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(username="zweitkonto").exists())

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
        self.assertEqual(self.lena.aktive_mitgliedschaft.rolle, Mitgliedschaft.ADMIN)  # Lena ist Admin

    def test_leerer_name_wird_abgelehnt(self):
        """Ohne Namen wird keine WG erstellt, das Formular erscheint erneut."""
        r = self.client.post(reverse("wg_erstellen"), {"name": ""})  # Leeren Namen absenden
        self.assertEqual(r.status_code, 200)              # 200 = Seite wird erneut angezeigt (mit Fehler)
        self.assertFalse(WG.objects.exists())             # Es wurde keine WG gespeichert

    def test_home_ohne_wg_leitet_zu_start(self):
        """Wer noch keine WG hat, landet auf der Seite "WG erstellen / beitreten"."""
        self.assertRedirects(self.client.get(reverse("home")), reverse("wg_start"))

    def test_get_auf_erstellen_und_beitreten_nicht_erlaubt(self):
        """wg_erstellen und wg_beitreten verändern Daten und nehmen deshalb nur POST an."""
        self.assertEqual(self.client.get(reverse("wg_erstellen")).status_code, 405)
        self.assertEqual(self.client.get(reverse("wg_beitreten")).status_code, 405)

    def test_zweite_wg_nicht_moeglich(self):
        """Ein Benutzer kann nicht zwei WGs erstellen."""
        self.client.post(reverse("wg_erstellen"), {"name": "A"})  # Erste WG
        self.client.post(reverse("wg_erstellen"), {"name": "B"})  # Zweiter Versuch
        self.assertEqual(WG.objects.count(), 1)           # Es gibt trotzdem nur eine WG


class DoppelklickTests(TestCase):
    """Zwei gleichzeitige Requests: beide bestehen _hat_wg(), erst die DB lehnt den zweiten ab.
    Simuliert, indem _hat_wg für den zweiten Request auf False gesetzt wird."""

    def setUp(self):
        """Lena ist schon Admin einer WG."""
        self.lena = make_user("lena")
        self.wg = WG.objects.create(name="WG")
        Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)
        self.client.force_login(self.lena)

    @mock.patch("wg.views._hat_wg", return_value=False)
    def test_erstellen_doppelt_keine_verwaiste_wg(self, _):
        """Der zweite Request führt zu einer Weiterleitung statt 500, und es bleibt keine WG ohne Mitglieder zurück."""
        r = self.client.post(reverse("wg_erstellen"), {"name": "Doppelt"})
        self.assertRedirects(r, reverse("wg_detail"))
        self.assertEqual(WG.objects.count(), 1)           # Nur die ursprüngliche WG

    @mock.patch("wg.views._hat_wg", return_value=False)
    def test_beitreten_doppelt_kein_fehler(self, _):
        """Beitritt trotz aktiver Mitgliedschaft: Weiterleitung statt 500, Lena bleibt in ihrer WG."""
        andere = WG.objects.create(name="Andere")
        r = self.client.post(reverse("wg_beitreten"), {"code": andere.einladungscode})
        self.assertRedirects(r, reverse("wg_detail"))
        self.assertEqual(self.lena.aktive_mitgliedschaft.wg, self.wg)


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
        m = self.sara.aktive_mitgliedschaft               # Saras Mitgliedschaft holen
        self.assertEqual(m.wg, self.wg)                   # Richtige WG?
        self.assertEqual(m.rolle, Mitgliedschaft.MITGLIED)  # Rolle = Mitglied, nicht Admin

    def test_beitritt_mit_ungueltigem_code(self):
        """Mit einem falschen Code passiert nichts, es erscheint eine Fehlermeldung."""
        r = self.client.post(reverse("wg_beitreten"), {"code": "falsch"})
        self.assertEqual(r.status_code, 200)              # Formular wird erneut angezeigt
        self.assertFalse(Mitgliedschaft.objects.filter(user=self.sara).exists())  # Sara ist nicht beigetreten

    def test_code_mit_leerzeichen_am_rand(self):
        """Beim Kopieren mitgenommene Leerzeichen am Rand stören den Beitritt nicht."""
        self.client.post(reverse("wg_beitreten"), {"code": f"  {self.wg.einladungscode}  "})
        self.assertEqual(self.sara.aktive_mitgliedschaft.wg, self.wg)

    def test_mitglied_kann_keiner_anderen_wg_beitreten(self):
        """Wer schon in einer WG ist, bleibt dort, auch mit einem gültigen Code einer anderen WG."""
        Mitgliedschaft.objects.create(user=self.sara, wg=self.wg)  # Sara ist schon in der WG von Lena
        andere = WG.objects.create(name="Andere")
        r = self.client.post(reverse("wg_beitreten"), {"code": andere.einladungscode})
        self.assertRedirects(r, reverse("wg_detail"))
        self.assertEqual(self.sara.aktive_mitgliedschaft.wg, self.wg)  # Weiterhin in der alten WG
        self.assertFalse(andere.mitglieder.exists())      # In der anderen WG ist niemand

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
        """Der Admin kann ein Mitglied entfernen. Die Zeile bleibt als Historie, ist aber nicht mehr aktiv."""
        self.client.force_login(self.lena)
        self.client.post(reverse("mitglied_entfernen", args=[self.mm.pk]))  # Marco entfernen
        self.assertFalse(Mitgliedschaft.objects.aktive().filter(pk=self.mm.pk).exists())  # Marco ist nicht mehr aktiv
        self.mm.refresh_from_db()
        self.assertIsNotNone(self.mm.ausgetreten_am)      # Austritt gesetzt statt gelöscht

    def test_entfernen_braucht_bestaetigung(self):
        """Das blosse Aufrufen der Entfernen-Seite (ohne Bestätigen) ändert nichts."""
        self.client.force_login(self.lena)
        r = self.client.get(reverse("mitglied_entfernen", args=[self.mm.pk]))  # Nur die Bestätigungsseite öffnen
        self.assertEqual(r.status_code, 200)              # Seite wird angezeigt
        self.assertContains(r, "marco")                   # ... und nennt die betroffene Person
        self.assertTrue(Mitgliedschaft.objects.aktive().filter(pk=self.mm.pk).exists())  # Marco ist noch aktiv
        self.mm.refresh_from_db()
        self.assertIsNone(self.mm.ausgetreten_am)         # Kein Austritt gesetzt

    def test_mitglied_darf_nicht_entfernen(self):
        """Ein normales Mitglied darf niemanden entfernen."""
        self.client.force_login(self.marco)
        r = self.client.post(reverse("mitglied_entfernen", args=[self.ml.pk]))  # Marco versucht Lena zu entfernen
        self.assertEqual(r.status_code, 403)              # Verboten
        self.assertTrue(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lena ist noch da

    def test_letzter_admin_kann_nicht_entfernt_werden(self):
        """Der einzige Admin kann nicht entfernt werden."""
        self.client.force_login(self.lena)
        self.client.post(reverse("mitglied_entfernen", args=[self.ml.pk]))  # Sich selbst entfernen versuchen
        self.assertTrue(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lesbare Meldung, falls gelöscht
        self.ml.refresh_from_db()
        self.assertIsNone(self.ml.ausgetreten_am)         # Weiterhin aktiv
        self.assertTrue(self.ml.ist_admin)

    def test_letzter_admin_kann_nicht_herabgestuft_werden(self):
        """Der einzige Admin kann sich nicht selbst zum normalen Mitglied machen."""
        self.client.force_login(self.lena)
        self.client.post(reverse("rolle_wechseln", args=[self.ml.pk]))      # Sich selbst herabstufen versuchen
        self.assertTrue(Mitgliedschaft.objects.filter(pk=self.ml.pk).exists())  # Lesbare Meldung, falls gelöscht
        self.ml.refresh_from_db()
        self.assertTrue(self.ml.ist_admin)                # Lena ist weiterhin Admin

    def test_mitglied_darf_rolle_nicht_wechseln(self):
        """Ein normales Mitglied darf keine Rollen ändern, auch nicht die eigene."""
        self.client.force_login(self.marco)
        r = self.client.post(reverse("rolle_wechseln", args=[self.mm.pk]))  # Marco will sich zum Admin machen
        self.assertEqual(r.status_code, 403)
        self.mm.refresh_from_db()
        self.assertEqual(self.mm.rolle, Mitgliedschaft.MITGLIED)  # Rolle unverändert

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

    def test_admin_sieht_in_eigener_zeile_kein_entfernen(self):
        """Der Admin sieht "Entfernen" nur bei anderen. Für sich selbst gibt es "WG verlassen"."""
        self.client.force_login(self.lena)
        r = self.client.get(reverse("wg_detail"))
        self.assertContains(r, reverse("mitglied_entfernen", args=[self.mm.pk]))     # Bei Marco vorhanden
        self.assertNotContains(r, reverse("mitglied_entfernen", args=[self.ml.pk]))  # Bei Lena selbst nicht
        self.assertContains(r, reverse("wg_verlassen"))

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
        self.assertFalse(Mitgliedschaft.objects.aktive().filter(user=self.marco).exists())  # Marco ist nicht mehr aktiv
        self.mm.refresh_from_db()
        self.assertIsNotNone(self.mm.ausgetreten_am)      # Austritt gesetzt statt gelöscht (Historie bleibt)
        self.assertTrue(WG.objects.filter(pk=self.wg.pk).exists())                 # Die WG gibt es weiterhin

    def test_verlassen_braucht_bestaetigung(self):
        """Das blosse Aufrufen der Seite (ohne Bestätigen) ändert nichts."""
        self.client.force_login(self.marco)
        r = self.client.get(reverse("wg_verlassen"))      # Nur die Bestätigungsseite öffnen
        self.assertEqual(r.status_code, 200)              # Seite wird angezeigt
        self.assertTrue(Mitgliedschaft.objects.filter(user=self.marco).exists())  # Marco ist noch Mitglied
        self.mm.refresh_from_db()
        self.assertIsNone(self.mm.ausgetreten_am)         # Kein Austritt gesetzt, Mitgliedschaft weiter aktiv

    def test_einziger_admin_kann_nicht_verlassen(self):
        """Lena ist einzige Admin und Marco ist noch da: Sie muss zuerst die Admin-Rolle weitergeben."""
        self.client.force_login(self.lena)
        r = self.client.post(reverse("wg_verlassen"))     # Austritt versuchen
        self.assertRedirects(r, reverse("wg_detail"))     # Abgelehnt, zurück zur Übersicht
        self.assertTrue(Mitgliedschaft.objects.aktive().filter(pk=self.ml.pk).exists())  # Lena ist weiterhin aktiv

    def test_admin_kann_nach_rollenweitergabe_verlassen(self):
        """Gibt es einen zweiten Admin, darf Lena gehen."""
        self.mm.rolle = Mitgliedschaft.ADMIN              # Marco zum Admin machen
        self.mm.save()
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))         # Austritt
        self.assertFalse(Mitgliedschaft.objects.aktive().filter(pk=self.ml.pk).exists())  # Lena ist nicht mehr aktiv

    def test_einziges_mitglied_verlaesst_wg_bleibt(self):
        """Verlässt das letzte aktive Mitglied die WG, bleibt die WG mit 0 aktiven Mitgliedern bestehen.
        Grund: Die Historie (Ämtli, Ausgaben) soll nicht automatisch per CASCADE verschwinden."""
        self.mm.austreten()                               # Marco ist schon ausgetreten, Lena ist allein
        self.client.force_login(self.lena)
        r = self.client.post(reverse("wg_verlassen"))     # Austritt
        self.assertRedirects(r, reverse("wg_start"))
        self.assertTrue(WG.objects.filter(pk=self.wg.pk).exists())   # WG existiert weiter
        self.assertEqual(self.wg.mitglieder.aktive().count(), 0)    # ... aber ohne aktive Mitglieder
        self.assertEqual(self.wg.mitglieder.count(), 2)              # Beide Mitgliedschaften sind als Historie da

    def test_leere_wg_mit_altem_code_nicht_betretbar(self):
        """Nach dem Austritt des letzten Mitglieds ist die WG geschlossen: Der alte Code funktioniert nicht mehr,
        damit niemand die Historie einer aufgelösten WG sieht."""
        alt = self.wg.einladungscode
        self.mm.austreten()                               # Lena ist allein
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))         # Letzte Person geht
        self.wg.refresh_from_db()
        self.assertNotEqual(self.wg.einladungscode, alt)  # Code wurde ersetzt
        sara = make_user("sara")
        self.client.force_login(sara)
        r = self.client.post(reverse("wg_beitreten"), {"code": alt})  # Versuch mit dem alten Code
        self.assertEqual(r.status_code, 200)              # Formular mit Fehlermeldung
        self.assertIsNone(sara.aktive_mitgliedschaft)     # Sara ist nicht beigetreten
        self.assertEqual(self.wg.mitglieder.aktive().count(), 0)

    def test_verlassen_mit_weiteren_mitgliedern_behaelt_code(self):
        """Solange noch jemand in der WG ist, bleibt der Einladungscode gleich."""
        alt = self.wg.einladungscode
        self.client.force_login(self.marco)
        self.client.post(reverse("wg_verlassen"))
        self.wg.refresh_from_db()
        self.assertEqual(self.wg.einladungscode, alt)

    def test_nach_verlassen_neu_beitreten(self):
        """Wer gegangen ist, kann mit einem Code wieder einer WG beitreten."""
        self.client.force_login(self.marco)
        self.client.post(reverse("wg_verlassen"))         # Austritt
        self.client.post(reverse("wg_beitreten"), {"code": self.wg.einladungscode})  # Wieder beitreten
        self.assertTrue(Mitgliedschaft.objects.aktive().filter(user=self.marco, wg=self.wg).exists())  # Marco ist wieder dabei


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


class AusgetreteneMitgliederTests(TestCase):
    """Ausgetretene Mitgliedschaften bleiben als Historie in der DB, dürfen aber nirgends als aktiv zählen."""

    def setUp(self):
        """WG mit Lena (Admin) und Marco (Mitglied); Sara war Admin und ist ausgetreten."""
        self.wg = WG.objects.create(name="WG")
        self.lena = make_user("lena")
        self.marco = make_user("marco")
        self.sara = make_user("sara")
        self.ml = Mitgliedschaft.objects.create(user=self.lena, wg=self.wg, rolle=Mitgliedschaft.ADMIN)
        self.mm = Mitgliedschaft.objects.create(user=self.marco, wg=self.wg)
        self.ms = Mitgliedschaft.objects.create(user=self.sara, wg=self.wg, rolle=Mitgliedschaft.ADMIN)
        self.ms.austreten()

    def test_ausgetretene_hat_keinen_zugriff(self):
        """Sara landet nach dem Austritt auf "WG erstellen / beitreten", nicht in der alten WG."""
        self.client.force_login(self.sara)
        self.assertRedirects(self.client.get(reverse("wg_detail")), reverse("wg_start"))
        self.assertEqual(self.client.get(reverse("wg_start")).status_code, 200)  # Startseite statt Weiterleitung

    def test_ausgetretene_nicht_in_mitgliederliste(self):
        """Die Übersicht zeigt nur aktive Mitglieder."""
        self.client.force_login(self.marco)
        r = self.client.get(reverse("wg_detail"))
        self.assertContains(r, "lena")
        self.assertNotContains(r, "sara")

    def test_ausgetretene_admin_zaehlt_nicht_als_zweiter_admin(self):
        """Sara war Admin, ist aber weg: Lena ist einzige aktive Admin und darf nicht verlassen."""
        self.client.force_login(self.lena)
        self.client.post(reverse("wg_verlassen"))
        self.assertTrue(Mitgliedschaft.objects.aktive().filter(pk=self.ml.pk).exists())

    def test_ausgetretene_nicht_verwaltbar(self):
        """Eine beendete Mitgliedschaft lässt sich weder entfernen noch in der Rolle ändern (404)."""
        self.client.force_login(self.lena)
        self.assertEqual(self.client.post(reverse("mitglied_entfernen", args=[self.ms.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("rolle_wechseln", args=[self.ms.pk])).status_code, 404)

    def test_ausgetretene_kann_wieder_beitreten(self):
        """Neuer Beitritt erzeugt eine neue Zeile; die alte bleibt als Historie bestehen."""
        self.client.force_login(self.sara)
        self.client.post(reverse("wg_beitreten"), {"code": self.wg.einladungscode})
        self.assertEqual(self.sara.mitgliedschaften.count(), 2)          # Alte + neue Mitgliedschaft
        self.assertEqual(self.sara.aktive_mitgliedschaft.rolle, Mitgliedschaft.MITGLIED)  # Neu als Mitglied, nicht als Admin

    def test_db_erlaubt_nur_eine_aktive_mitgliedschaft(self):
        """Der UniqueConstraint lehnt eine zweite aktive Mitgliedschaft ab, ausgetretene stören nicht."""
        andere = WG.objects.create(name="Andere")
        with self.assertRaises(IntegrityError), transaction.atomic():  # atomic: Test-Transaktion bleibt nutzbar
            Mitgliedschaft.objects.create(user=self.marco, wg=andere)    # Marco ist schon aktiv in self.wg
        Mitgliedschaft.objects.create(user=self.sara, wg=andere)         # Sara: nur ausgetretene Zeile -> erlaubt
