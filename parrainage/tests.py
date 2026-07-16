"""
Tests unitaires du module parrainage - FAGNI Platform (Lot 2, Sprint 18)
Verifie les deux garde-fous anti-fraude retenus du pilote V1 : pas
d'auto-parrainage, delai de 48h avant credit effectif.
"""
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from paiements.services import obtenir_ou_creer_wallet
from .models import Parrainage
from .services import enregistrer_parrainage, crediter_si_eligible, ParrainageInvalide


class EnregistrementParrainageTests(TestCase):
    def setUp(self):
        self.parrain = ouvrir_dossier("client", "Rita", "0708963511")
        self.filleul = ouvrir_dossier("client", "Wilson", "0749423747")
        self.commande = creer_commande(
            self.filleul,
            [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )

    def test_enregistrement_simple(self):
        parrainage = enregistrer_parrainage(self.parrain, self.filleul, self.commande)
        self.assertEqual(parrainage.statut, "en_attente_delai")
        self.assertEqual(parrainage.montant_credit, 1000)


class AntiFraudeTests(TestCase):
    """Coeur de ce Sprint : les deux garde-fous retenus du pilote V1."""

    def test_auto_parrainage_refuse(self):
        client_dossier = ouvrir_dossier("client", "Client Solo", "0700000098")
        commande = creer_commande(
            client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )
        with self.assertRaises(ParrainageInvalide):
            enregistrer_parrainage(client_dossier, client_dossier, commande)

        self.assertEqual(Parrainage.objects.count(), 0)

    def test_filleul_parraine_deux_fois_refuse(self):
        parrain1 = ouvrir_dossier("client", "Parrain 1", "0700000099")
        parrain2 = ouvrir_dossier("client", "Parrain 2", "0700000100")
        filleul = ouvrir_dossier("client", "Filleul Unique", "0700000101")
        commande = creer_commande(
            filleul, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )

        enregistrer_parrainage(parrain1, filleul, commande)

        with self.assertRaises(ParrainageInvalide):
            enregistrer_parrainage(parrain2, filleul, commande)

        self.assertEqual(Parrainage.objects.filter(filleul=filleul).count(), 1)


class DelaiCreditTests(TestCase):
    """Le delai de 48h ne doit jamais etre contourne, meme sous pression."""

    def setUp(self):
        self.parrain = ouvrir_dossier("client", "Parrain Delai", "0700000102")
        self.filleul = ouvrir_dossier("client", "Filleul Delai", "0700000103")
        commande = creer_commande(
            self.filleul, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )
        self.parrainage = enregistrer_parrainage(self.parrain, self.filleul, commande)

    def test_credit_refuse_avant_delai(self):
        """Un parrainage tout juste cree (moins de 48h) ne doit jamais crediter."""
        crediter_si_eligible(self.parrainage)

        self.parrainage.refresh_from_db()
        self.assertEqual(self.parrainage.statut, "en_attente_delai")

        wallet = obtenir_ou_creer_wallet(self.parrain)
        self.assertEqual(wallet.solde, Decimal("0"))

    def test_credit_applique_apres_delai(self):
        """Une fois le delai ecoule, le credit doit s'appliquer normalement."""
        self.parrainage.eligible_a_partir_de = timezone.now() - timedelta(hours=1)
        self.parrainage.save(update_fields=["eligible_a_partir_de"])

        crediter_si_eligible(self.parrainage)

        self.parrainage.refresh_from_db()
        self.assertEqual(self.parrainage.statut, "credite")

        wallet = obtenir_ou_creer_wallet(self.parrain)
        self.assertEqual(wallet.solde, Decimal("1000"))

    def test_rejeu_apres_credit_idempotent(self):
        """Rejouer le credit apres qu'il ait deja eu lieu ne double jamais le montant."""
        self.parrainage.eligible_a_partir_de = timezone.now() - timedelta(hours=1)
        self.parrainage.save(update_fields=["eligible_a_partir_de"])

        crediter_si_eligible(self.parrainage)
        crediter_si_eligible(self.parrainage)  # rejoue

        wallet = obtenir_ou_creer_wallet(self.parrain)
        self.assertEqual(wallet.solde, Decimal("1000"))  # jamais 2000
