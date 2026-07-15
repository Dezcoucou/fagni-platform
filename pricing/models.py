"""
Module pricing - FAGNI Platform (Lot 2, Sprint 15)
Derive de FOS-210 v1.1 (chapitre 6, moteur de pricing) et du BOS
chapitre 11 (moteur economique).

Lecon retenue directement du pilote V1 : le coupon FAGNI30 avait des
problemes d'affichage sur plusieurs ecrans, mais jamais de double
application reelle. Ici, la contrainte d'unicite empeche structurellement
qu'un coupon soit applique deux fois a la meme Commande - jamais
seulement une verification applicative fragile.
"""
from django.db import models
from dossiers.models import Dossier
from commandes.models import Commande


class Coupon(models.Model):
    code = models.CharField("Code", max_length=30, unique=True)
    pourcentage_reduction = models.DecimalField(
        "Pourcentage de reduction", max_digits=5, decimal_places=2,
    )
    usage_max = models.PositiveIntegerField(
        "Usage maximum", null=True, blank=True,
        help_text="None = illimite",
    )
    usage_actuel = models.PositiveIntegerField("Usage actuel", default=0)
    premiere_commande_uniquement = models.BooleanField(
        "Premiere commande uniquement", default=True,
    )
    actif = models.BooleanField("Actif", default=True)
    valide_jusqu_a = models.DateTimeField(
        "Valide jusqu'a", null=True, blank=True,
        help_text="None = pas de date d'expiration",
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    class Meta:
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"

    def __str__(self):
        return f"{self.code} (-{self.pourcentage_reduction}%)"


class CouponUsage(models.Model):
    """
    Une utilisation reelle d'un Coupon sur une Commande precise.
    unique=True sur commande garantit structurellement qu'une Commande
    ne peut jamais recevoir deux coupons ni le meme coupon deux fois -
    jamais une verification applicative seule.
    """
    coupon = models.ForeignKey(
        Coupon, on_delete=models.PROTECT, related_name="usages",
    )
    dossier_client = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="coupons_utilises",
    )
    commande = models.OneToOneField(
        Commande, on_delete=models.CASCADE, related_name="coupon_usage",
    )
    montant_reduction = models.DecimalField(
        "Montant de la reduction (FCFA)", max_digits=10, decimal_places=2,
    )
    created_at = models.DateTimeField("Applique le", auto_now_add=True)

    class Meta:
        verbose_name = "Utilisation de coupon"
        verbose_name_plural = "Utilisations de coupon"

    def __str__(self):
        return f"{self.coupon.code} sur Commande #{self.commande_id} (-{self.montant_reduction} FCFA)"
