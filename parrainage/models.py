"""
Module parrainage - FAGNI Platform (Lot 2, Sprint 18)
Derive de FOS-210 v1.1 (chapitre 6, moteur de pricing) et de la lecon
retenue du pilote V1 : 1000 FCFA credites au parrain, declenche par la
premiere commande PAYEE du filleul, avec deux garde-fous anti-fraude -
pas d'auto-parrainage, delai de 48h avant credit effectif.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from dossiers.models import Dossier
from commandes.models import Commande


class Parrainage(models.Model):
    STATUT_CHOICES = [
        ("en_attente_delai", "En attente du delai de 48h"),
        ("credite", "Credite"),
        ("refuse", "Refuse"),
    ]

    parrain = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="parrainages_effectues",
    )
    filleul = models.OneToOneField(
        Dossier, on_delete=models.CASCADE, related_name="parrainage_recu",
        help_text="Un Dossier ne peut etre parraine qu'une seule fois",
    )
    commande_declenchante = models.ForeignKey(
        Commande, on_delete=models.PROTECT, related_name="parrainages_declenches",
    )
    montant_credit = models.DecimalField(
        "Montant du credit (FCFA)", max_digits=10, decimal_places=2, default=1000,
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="en_attente_delai",
    )
    eligible_a_partir_de = models.DateTimeField(
        "Eligible a partir de", help_text="created_at + 48h, anti-fraude",
    )
    created_at = models.DateTimeField("Enregistre le", auto_now_add=True)

    class Meta:
        verbose_name = "Parrainage"
        verbose_name_plural = "Parrainages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.parrain.nom} -> {self.filleul.nom} - {self.get_statut_display()}"

    def save(self, *args, **kwargs):
        if not self.eligible_a_partir_de:
            self.eligible_a_partir_de = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)
