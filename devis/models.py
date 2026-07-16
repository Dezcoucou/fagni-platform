"""
Module devis - FAGNI Platform (Lot 2, Sprint 17)
Derive de FOS-210 v1.1 (chapitre 6, moteur de pricing - articles sur
devis) et section 12.1 (exemple cordonnerie : decision humaine
systematique, jamais automatique).
"""
from django.db import models
from dossiers.models import Dossier
from commandes.models import Commande, LigneCommande


class Devis(models.Model):
    STATUT_CHOICES = [
        ("en_attente", "En attente de proposition"),
        ("propose", "Montant propose"),
        ("accepte", "Accepte par le client"),
        ("refuse", "Refuse par le client"),
    ]

    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="devis",
    )
    ligne_commande = models.ForeignKey(
        LigneCommande, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devis",
    )
    description = models.TextField("Description du besoin de devis")
    montant_propose = models.DecimalField(
        "Montant propose (FCFA)", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    propose_par = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devis_proposes",
        help_text="L'acteur humain (artisan, partenaire) ayant propose le montant",
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="en_attente",
    )
    created_at = models.DateTimeField("Demande le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis a jour le", auto_now=True)

    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Devis #{self.id} - Commande #{self.commande_id} - {self.get_statut_display()}"
