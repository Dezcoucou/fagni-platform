"""
Tests unitaires du module capacites - FAGNI Platform (Lot 1, Sprint 8)
Verifie la regle centrale de FOS-210 section 11.2 : un Dossier sans
Capacite declaree n'est jamais compatible par defaut.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from .models import Capacite
from .services import (
    declarer_capacite,
    desactiver_capacite,
    est_compatible,
    lister_partenaires_compatibles,
)


class DeclarationCapaciteTests(TestCase):
    def setUp(self):
        self.atelier = ouvrir_dossier("partenaire", "Atelier X", "0546562713")

    def test_declaration_simple(self):
        capacite = declarer_capacite(self.atelier, "lavage", volume_disponible=20)
        self.assertEqual(capacite.service, "lavage")
        self.assertTrue(capacite.active)

    def test_redeclaration_met_a_jour(self):
        """Redeclarer le meme service met a jour, ne cree jamais de doublon."""
        declarer_capacite(self.atelier, "lavage", volume_disponible=10)
        declarer_capacite(self.atelier, "lavage", volume_disponible=25)

        self.assertEqual(Capacite.objects.filter(dossier=self.atelier, service="lavage").count(), 1)
        capacite = Capacite.objects.get(dossier=self.atelier, service="lavage")
        self.assertEqual(capacite.volume_disponible, 25)


class CompatibiliteTests(TestCase):
    """
    Coeur de ce Sprint : aucune compatibilite par defaut, jamais supposee -
    un excellent atelier textile n'est PAS automatiquement compatible avec
    la cordonnerie, meme s'il a une excellente reputation generale.
    """
    def setUp(self):
        self.atelier = ouvrir_dossier("partenaire", "Atelier Textile", "0546562714")
        declarer_capacite(self.atelier, "lavage")

    def test_compatible_sur_service_declare(self):
        self.assertTrue(est_compatible(self.atelier, "lavage"))

    def test_non_compatible_sur_service_non_declare(self):
        """L'atelier n'a jamais declare la cordonnerie - donc non compatible."""
        self.assertFalse(est_compatible(self.atelier, "cordonnerie"))

    def test_dossier_sans_aucune_capacite_jamais_compatible(self):
        """Un tout nouveau partenaire, sans aucune Capacite declaree, n'est compatible avec rien."""
        nouveau = ouvrir_dossier("partenaire", "Nouveau Partenaire", "0700000050")
        self.assertFalse(est_compatible(nouveau, "lavage"))

    def test_desactivation_rend_incompatible(self):
        self.assertTrue(est_compatible(self.atelier, "lavage"))
        desactiver_capacite(self.atelier, "lavage")
        self.assertFalse(est_compatible(self.atelier, "lavage"))

        # La Capacite existe toujours, juste inactive - jamais supprimee
        self.assertTrue(Capacite.objects.filter(dossier=self.atelier, service="lavage").exists())


class ListePartenairesCompatiblesTests(TestCase):
    def test_liste_uniquement_les_actifs(self):
        atelier1 = ouvrir_dossier("partenaire", "Atelier 1", "0700000051")
        atelier2 = ouvrir_dossier("partenaire", "Atelier 2", "0700000052")
        declarer_capacite(atelier1, "repassage")
        declarer_capacite(atelier2, "repassage")
        desactiver_capacite(atelier2, "repassage")

        compatibles = lister_partenaires_compatibles("repassage")
        dossiers_compatibles = [c.dossier for c in compatibles]

        self.assertIn(atelier1, dossiers_compatibles)
        self.assertNotIn(atelier2, dossiers_compatibles)
