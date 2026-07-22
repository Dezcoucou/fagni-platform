"""
Tests unitaires du module abonnements - FAGNI Platform.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from configuration.services import definir_parametre
from .services import (
    creer_abonnement, generer_commande_depuis_abonnement,
    obtenir_prix_pack, obtenir_prix_pack_avec_version,
    DossierNonUtilisable, PrixAbonnementNonConfigure,
    CommandeDejaGenereePourCetteEcheance,
)
from .models import Abonnement


class CreationAbonnementTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963520")

    def test_creation_simple(self):
        abonnement = creer_abonnement(
            self.client_dossier, "essentiel", "M", jour_collecte=0, jour_livraison=3,
        )
        self.assertEqual(abonnement.statut, "actif")
        self.assertEqual(abonnement.dossier_client, self.client_dossier)

    def test_refuse_si_dossier_suspendu(self):
        self.client_dossier.statut = "suspendu"
        self.client_dossier.save(update_fields=["statut"])

        with self.assertRaises(DossierNonUtilisable):
            creer_abonnement(self.client_dossier, "essentiel", "M", jour_collecte=0, jour_livraison=3)


class PrixPackTests(TestCase):
    def test_prix_non_configure_leve_erreur_explicite(self):
        """Jamais de prix par defaut suppose - doit refuser explicitement."""
        with self.assertRaises(PrixAbonnementNonConfigure):
            obtenir_prix_pack("essentiel", "M")

    def test_prix_lu_depuis_configuration(self):
        definir_parametre("abonnement_prix_essentiel_M", "8000")
        self.assertEqual(obtenir_prix_pack("essentiel", "M"), 8000.0)


class GenerationCommandeDepuisAbonnementTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963521")
        definir_parametre("abonnement_prix_essentiel_M", "8000")
        self.abonnement = creer_abonnement(
            self.client_dossier, "essentiel", "M", jour_collecte=0, jour_livraison=3,
        )

    def test_genere_une_commande_avec_le_bon_prix(self):
        commande = generer_commande_depuis_abonnement(self.abonnement)
        self.assertEqual(commande.dossier_client, self.client_dossier)
        self.assertEqual(float(commande.prix_engage), 8000.0)

    def test_refuse_si_abonnement_non_actif(self):
        self.abonnement.statut = "suspendu"
        self.abonnement.save(update_fields=["statut"])

        with self.assertRaises(ValueError):
            generer_commande_depuis_abonnement(self.abonnement)

    def test_refuse_si_prix_non_configure_pour_ce_pack(self):
        abonnement_confort = creer_abonnement(
            self.client_dossier, "confort", "S", jour_collecte=1, jour_livraison=4,
        )
        with self.assertRaises(PrixAbonnementNonConfigure):
            generer_commande_depuis_abonnement(abonnement_confort)

    def test_reutilise_bien_le_cycle_evenement_commande_creee(self):
        """Verifie que la Commande generee emet bien commande_creee - meme vocabulaire, rien invente."""
        from evenements.models import Evenement
        from django.contrib.contenttypes.models import ContentType

        commande = generer_commande_depuis_abonnement(self.abonnement)
        existe = Evenement.objects.filter(
            type_evenement="commande_creee",
            objet_source_type=ContentType.objects.get_for_model(commande),
            objet_source_id=commande.id,
        ).exists()
        self.assertTrue(existe)


class AntiDoublonGenerationTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963530")
        definir_parametre("abonnement_prix_confort_M", "10900")
        self.abonnement = creer_abonnement(
            self.client_dossier, "confort", "M", jour_collecte=0, jour_livraison=3,
        )

    def test_deuxieme_generation_immediate_refusee(self):
        """Une deuxieme generation moins de 6 jours apres la premiere doit etre refusee."""
        generer_commande_depuis_abonnement(self.abonnement)

        with self.assertRaises(CommandeDejaGenereePourCetteEcheance):
            generer_commande_depuis_abonnement(self.abonnement)

    def test_commande_generee_tracee_sur_abonnement(self):
        """La Commande generee doit etre tracee vers son Abonnement source."""
        commande = generer_commande_depuis_abonnement(self.abonnement)
        self.assertEqual(commande.abonnement, self.abonnement)

    def test_generation_au_dela_du_delai_autorisee(self):
        """Passe le delai de 6 jours, une nouvelle generation doit etre possible."""
        from django.utils import timezone
        from datetime import timedelta
        from commandes.models import Commande

        premiere = generer_commande_depuis_abonnement(self.abonnement)
        Commande.objects.filter(pk=premiere.pk).update(
            created_at=timezone.now() - timedelta(days=7)
        )

        deuxieme = generer_commande_depuis_abonnement(self.abonnement)
        self.assertNotEqual(premiere.id, deuxieme.id)


class ObtenirPrixPackAvecVersionTests(TestCase):
    def test_retourne_prix_et_version_coherents(self):
        """
        SE-01 (FOS-213) : obtenir_prix_pack_avec_version() doit retourner
        exactement le meme prix que obtenir_prix_pack(), plus la
        VersionParametre exacte utilisee pour ce calcul.
        """
        definir_parametre("abonnement_prix_confort_M", "10900")

        prix_simple = obtenir_prix_pack("confort", "M")
        prix_avec_version, version = obtenir_prix_pack_avec_version("confort", "M")

        self.assertEqual(prix_simple, prix_avec_version)
        self.assertEqual(prix_avec_version, 10900.0)
        self.assertEqual(float(version.valeur), 10900.0)

    def test_leve_prix_non_configure_si_absent(self):
        """Meme comportement d'erreur que obtenir_prix_pack() - jamais suppose."""
        with self.assertRaises(PrixAbonnementNonConfigure):
            obtenir_prix_pack_avec_version("essentiel", "S")

    def test_obtenir_prix_pack_existant_inchange(self):
        """
        Non-regression explicite (critere de validation SE-01) : la
        fonction existante, deja utilisee en production, doit continuer
        a fonctionner exactement comme avant.
        """
        definir_parametre("abonnement_prix_confort_S", "7500")
        self.assertEqual(obtenir_prix_pack("confort", "S"), 7500.0)
