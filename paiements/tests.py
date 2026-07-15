"""
Tests unitaires du module paiements - FAGNI Platform (Lot 1, Sprint 7)
L'idempotence est le test le plus important - une lecon directement
retenue du pilote V1, ou ce principe a evite plusieurs incidents reels.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from evenements.models import Evenement
from .models import Wallet, TransactionWallet, Paiement
from .services import (
    crediter_wallet,
    debiter_wallet,
    confirmer_paiement,
    obtenir_ou_creer_wallet,
    SoldeInsuffisant,
)


class WalletBaseTests(TestCase):
    def setUp(self):
        self.dossier = ouvrir_dossier("client", "Rita", "0708963511")

    def test_wallet_cree_a_la_demande(self):
        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 0)


class CreditWalletTests(TestCase):
    def setUp(self):
        self.dossier = ouvrir_dossier("client", "Wilson", "0749423747")

    def test_credit_simple(self):
        crediter_wallet(self.dossier, 1000, "Parrainage", "credit-test-001")
        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 1000)

    def test_idempotence_meme_cle_pas_de_double_credit(self):
        """
        Regle centrale, retenue directement du pilote V1 : rejouer la
        meme operation avec la meme cle ne doit jamais crediter deux fois.
        """
        crediter_wallet(self.dossier, 1000, "Parrainage", "idempotence-test-001")
        crediter_wallet(self.dossier, 1000, "Parrainage", "idempotence-test-001")  # rejoue

        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 1000)  # jamais 2000
        self.assertEqual(
            TransactionWallet.objects.filter(idempotency_key="idempotence-test-001").count(), 1,
        )

    def test_cles_differentes_creditent_independamment(self):
        crediter_wallet(self.dossier, 500, "Ajustement 1", "credit-a")
        crediter_wallet(self.dossier, 300, "Ajustement 2", "credit-b")

        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 800)


class DebitWalletTests(TestCase):
    def setUp(self):
        self.dossier = ouvrir_dossier("livreur", "Youande", "0799404886")
        crediter_wallet(self.dossier, 5000, "Solde initial", "init-credit")

    def test_debit_simple(self):
        debiter_wallet(self.dossier, 2000, "Retrait", "debit-test-001")
        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 3000)

    def test_debit_refuse_si_solde_insuffisant(self):
        with self.assertRaises(SoldeInsuffisant):
            debiter_wallet(self.dossier, 10000, "Retrait trop eleve", "debit-refuse-001")

        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 5000)  # inchange

    def test_idempotence_debit(self):
        debiter_wallet(self.dossier, 1000, "Retrait", "idempotence-debit-001")
        debiter_wallet(self.dossier, 1000, "Retrait", "idempotence-debit-001")  # rejoue

        wallet = obtenir_ou_creer_wallet(self.dossier)
        self.assertEqual(wallet.solde, 4000)  # un seul debit, pas deux


class ConfirmerPaiementTests(TestCase):
    def test_confirmation_emet_evenement(self):
        client_dossier = ouvrir_dossier("client", "Client Paiement", "0700000040")
        commande = creer_commande(
            client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 2, "prix_unitaire": 500}],
        )

        nb_avant = Evenement.objects.count()
        paiement = confirmer_paiement(commande, 1000, "wave")

        self.assertEqual(paiement.statut, "confirme")
        self.assertEqual(Evenement.objects.count(), nb_avant + 1)
        self.assertTrue(Evenement.objects.filter(type_evenement="paiement_confirme").exists())
