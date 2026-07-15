"""
Tests unitaires du module accounts - FAGNI Platform (Lot 1, Sprint 12)
Verifie la limite volontaire du module (autorise, ne decide jamais) et
la distinction stricte entre Compte (identite) et Dossier (memoire).
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from .models import Organisation, Compte
from .services import creer_compte, autoriser_action, desactiver_compte


class CreationCompteTests(TestCase):
    def test_creation_simple(self):
        dossier = ouvrir_dossier("client", "Rita", "0708963511")
        compte = creer_compte(dossier)
        self.assertEqual(compte.role, "membre")
        self.assertTrue(compte.actif)

    def test_compte_avec_organisation(self):
        dossier = ouvrir_dossier("client", "Entreprise ABC (contact)", "0700000070")
        org = Organisation.objects.create(nom="Entreprise ABC", type_organisation="entreprise_cliente")
        compte = creer_compte(dossier, organisation=org, role="administrateur")

        self.assertEqual(compte.organisation, org)
        self.assertEqual(org.comptes.count(), 1)


class AutorisationActionTests(TestCase):
    """Coeur de ce Sprint : le module autorise, il ne decide jamais lui-meme."""

    def test_membre_autorise_a_consulter(self):
        dossier = ouvrir_dossier("client", "Membre Test", "0700000071")
        compte = creer_compte(dossier, role="membre")
        self.assertTrue(autoriser_action(compte, "consulter"))

    def test_membre_non_autorise_a_gerer_organisation(self):
        """Un simple membre ne doit jamais etre autorise pour une action d'administration."""
        dossier = ouvrir_dossier("client", "Membre Limite", "0700000072")
        compte = creer_compte(dossier, role="membre")
        self.assertFalse(autoriser_action(compte, "gerer_organisation"))

    def test_administrateur_autorise_a_gerer_organisation(self):
        dossier = ouvrir_dossier("ops", "Admin Test", "0700000073")
        compte = creer_compte(dossier, role="administrateur")
        self.assertTrue(autoriser_action(compte, "gerer_organisation"))

    def test_compte_inactif_jamais_autorise_meme_administrateur(self):
        """
        Regle stricte : un Compte inactif n'est jamais autorise pour rien,
        meme s'il porte le role le plus eleve.
        """
        dossier = ouvrir_dossier("ops", "Admin Desactive", "0700000074")
        compte = creer_compte(dossier, role="administrateur")
        desactiver_compte(compte)

        self.assertFalse(autoriser_action(compte, "consulter"))
        self.assertFalse(autoriser_action(compte, "gerer_organisation"))

    def test_action_inconnue_jamais_autorisee(self):
        dossier = ouvrir_dossier("ops", "Test Action Inconnue", "0700000075")
        compte = creer_compte(dossier, role="administrateur")
        self.assertFalse(autoriser_action(compte, "action_qui_n_existe_pas"))


class DistinctionIdentiteMemoireTests(TestCase):
    """
    Verifie que le Compte (identite) et le Dossier (memoire) restent
    structurellement independants - desactiver l'un ne touche jamais
    l'autre.
    """
    def test_desactivation_compte_ne_touche_pas_dossier(self):
        dossier = ouvrir_dossier("livreur", "Youande", "0799404886")
        compte = creer_compte(dossier, role="membre")

        desactiver_compte(compte)

        dossier.refresh_from_db()
        self.assertEqual(dossier.statut, "actif")  # le Dossier reste intact
        self.assertFalse(compte.actif)  # seul le Compte change
