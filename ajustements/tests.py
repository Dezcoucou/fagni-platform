"""
Tests unitaires du module ajustements - FAGNI Platform (Lot 2, Sprint 16)
L'idempotence est verifiee des la premiere version - anticipee grace a
la contrainte OneToOneField ajoutee avant meme d'ecrire les services,
pas decouverte apres coup comme au Sprint 2.
"""
from decimal import Decimal
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from paiements.services import obtenir_ou_creer_wallet
from .models import AjustementCommande
from .services import traiter_ecart_quantite, confirmer_complement


class AucunEcartTests(TestCase):
    def test_quantite_identique_retourne_none(self):
        client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        commande = creer_commande(
            client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 5, "prix_unitaire": 500}],
        )
        ligne = commande.lignes.first()

        resultat = traiter_ecart_quantite(ligne, quantite_reelle=5)
        self.assertIsNone(resultat)
        self.assertEqual(AjustementCommande.objects.count(), 0)


class DeficitTests(TestCase):
    """Coeur du BOS 4.1 : un deficit rembourse automatiquement, sans jamais demander d'accord."""

    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Wilson", "0749423747")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 10, "prix_unitaire": 300}],
        )
        self.ligne = self.commande.lignes.first()

    def test_deficit_credite_automatiquement(self):
        ajustement = traiter_ecart_quantite(self.ligne, quantite_reelle=7)

        self.assertEqual(ajustement.type_ajustement, "deficit")
        self.assertEqual(ajustement.statut, "automatique_applique")
        self.assertEqual(ajustement.montant_ajustement, Decimal("900"))  # 3 manquants x 300

        wallet = obtenir_ou_creer_wallet(self.client_dossier)
        self.assertEqual(wallet.solde, Decimal("900"))

    def test_rejeu_idempotent_pas_de_double_credit(self):
        """
        Le test central de ce Sprint : appeler traiter_ecart_quantite
        deux fois pour la meme ligne ne doit jamais crediter deux fois
        le wallet - anticipe des la conception grace au OneToOneField.
        """
        traiter_ecart_quantite(self.ligne, quantite_reelle=7)
        traiter_ecart_quantite(self.ligne, quantite_reelle=7)  # rejoue

        wallet = obtenir_ou_creer_wallet(self.client_dossier)
        self.assertEqual(wallet.solde, Decimal("900"))  # jamais 1800
        self.assertEqual(AjustementCommande.objects.filter(ligne_commande=self.ligne).count(), 1)


class ExcedentTests(TestCase):
    """Coeur du BOS 4.1 : un excedent n'est jamais facture automatiquement."""

    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Excedent", "0700000091")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Pantalon", "service": "lavage", "quantite": 3, "prix_unitaire": 400}],
        )
        self.ligne = self.commande.lignes.first()

    def test_excedent_en_attente_jamais_facture_directement(self):
        ajustement = traiter_ecart_quantite(self.ligne, quantite_reelle=5)

        self.assertEqual(ajustement.type_ajustement, "excedent")
        self.assertEqual(ajustement.statut, "en_attente_complement")
        self.assertEqual(ajustement.montant_ajustement, Decimal("800"))  # 2 en trop x 400

        # Aucun credit ni debit ne doit avoir eu lieu - jamais automatique
        wallet = obtenir_ou_creer_wallet(self.client_dossier)
        self.assertEqual(wallet.solde, Decimal("0"))

    def test_confirmation_acceptee(self):
        ajustement = traiter_ecart_quantite(self.ligne, quantite_reelle=5)
        confirmer_complement(ajustement, accepte=True)
        ajustement.refresh_from_db()
        self.assertEqual(ajustement.statut, "complement_paye")

    def test_confirmation_refusee(self):
        ajustement = traiter_ecart_quantite(self.ligne, quantite_reelle=5)
        confirmer_complement(ajustement, accepte=False)
        ajustement.refresh_from_db()
        self.assertEqual(ajustement.statut, "complement_refuse")

    def test_confirmation_sur_deficit_refusee(self):
        """La confirmation ne s'applique jamais a un deficit - seulement a un excedent."""
        client2 = ouvrir_dossier("client", "Client Deficit", "0700000092")
        commande2 = creer_commande(
            client2, [{"article": "Robe", "service": "lavage", "quantite": 5, "prix_unitaire": 500}],
        )
        ligne2 = commande2.lignes.first()
        ajustement_deficit = traiter_ecart_quantite(ligne2, quantite_reelle=3)

        with self.assertRaises(ValueError):
            confirmer_complement(ajustement_deficit, accepte=True)
