"""
Tests unitaires du module pricing - FAGNI Platform (Lot 2, Sprint 15)
Le test le plus symbolique de cette session : empecher structurellement
qu'un coupon soit applique deux fois sur la meme Commande - le probleme
exact corrige manuellement pour Rita et Wilson au tout debut de cette
nuit, cette fois impossible par construction.
"""
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from .models import Coupon, CouponUsage
from .services import (
    valider_et_appliquer_coupon,
    calculer_repartition_articles,
    calculer_repartition_livraison,
    CouponInvalide,
)


class ApplicationCouponTests(TestCase):
    def setUp(self):
        self.coupon = Coupon.objects.create(
            code="FAGNI30", pourcentage_reduction=30, usage_max=100,
        )
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 10, "prix_unitaire": 500}],
        )  # prix_engage = 5000

    def test_application_simple(self):
        reduction = valider_et_appliquer_coupon(
            self.commande, "FAGNI30", self.client_dossier, est_premiere_commande=True,
        )
        self.assertEqual(reduction, Decimal("1500"))  # 30% de 5000

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.prix_engage, Decimal("3500"))


class DoubleCouponImpossibleTests(TestCase):
    """
    Le test le plus important de ce Sprint - reproduit exactement le
    probleme rencontre par Rita et Wilson en pilote V1, cette fois
    rendu structurellement impossible.
    """
    def setUp(self):
        Coupon.objects.create(code="FAGNI30", pourcentage_reduction=30, usage_max=100)
        self.client_dossier = ouvrir_dossier("client", "Wilson", "0749423747")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 7, "prix_unitaire": 500}],
        )

    def test_deuxieme_application_meme_coupon_refused(self):
        valider_et_appliquer_coupon(
            self.commande, "FAGNI30", self.client_dossier, est_premiere_commande=True,
        )

        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(
                self.commande, "FAGNI30", self.client_dossier, est_premiere_commande=True,
            )

        # Un seul CouponUsage doit exister, jamais deux
        self.assertEqual(CouponUsage.objects.filter(commande=self.commande).count(), 1)

    def test_prix_non_double_reduit(self):
        """Le prix ne doit avoir baisse qu'une seule fois, meme apres tentative de rejeu."""
        valider_et_appliquer_coupon(
            self.commande, "FAGNI30", self.client_dossier, est_premiere_commande=True,
        )
        prix_apres_premier = self.commande.prix_engage

        try:
            valider_et_appliquer_coupon(
                self.commande, "FAGNI30", self.client_dossier, est_premiere_commande=True,
            )
        except CouponInvalide:
            pass

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.prix_engage, prix_apres_premier)  # inchange


class ValidationCouponTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Test", "0700000090")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Pantalon", "service": "lavage", "quantite": 1, "prix_unitaire": 1000}],
        )

    def test_coupon_inexistant_refuse(self):
        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(
                self.commande, "CODE_INEXISTANT", self.client_dossier, True,
            )

    def test_coupon_inactif_refuse(self):
        Coupon.objects.create(code="INACTIF", pourcentage_reduction=20, actif=False)
        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(self.commande, "INACTIF", self.client_dossier, True)

    def test_coupon_expire_refuse(self):
        Coupon.objects.create(
            code="EXPIRE", pourcentage_reduction=20,
            valide_jusqu_a=timezone.now() - timedelta(days=1),
        )
        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(self.commande, "EXPIRE", self.client_dossier, True)

    def test_coupon_usage_max_atteint_refuse(self):
        Coupon.objects.create(code="LIMITE", pourcentage_reduction=20, usage_max=1, usage_actuel=1)
        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(self.commande, "LIMITE", self.client_dossier, True)

    def test_coupon_premiere_commande_refuse_si_pas_premiere(self):
        Coupon.objects.create(code="NOUVEAU", pourcentage_reduction=20, premiere_commande_uniquement=True)
        with self.assertRaises(CouponInvalide):
            valider_et_appliquer_coupon(self.commande, "NOUVEAU", self.client_dossier, est_premiere_commande=False)


class RepartitionTests(TestCase):
    def test_repartition_articles(self):
        repartition = calculer_repartition_articles(Decimal("5000"), commission_pct=50)
        self.assertEqual(repartition["part_partenaire"], Decimal("2500"))
        self.assertEqual(repartition["part_fagni"], Decimal("2500"))

    def test_repartition_livraison(self):
        repartition = calculer_repartition_livraison(Decimal("2000"), part_livreur_pct=80)
        self.assertEqual(repartition["part_livreur"], Decimal("1600"))
        self.assertEqual(repartition["part_fagni"], Decimal("400"))
