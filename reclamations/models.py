"""
Module reclamations - FAGNI Platform (Lot 1, Sprint 6)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objet Reclamation) et de
FOS-211 v1.1 (section 2.5).

Contrairement a Evenement et Preuve, une Reclamation n'est PAS immuable -
c'est un objet a cycle de vie (ouverte -> resolue), comme Commande et
Mission. Ce qui reste immuable, c'est la trace de sa resolution une fois
tranchee (voir services.py).
"""
from django.db import models
from dossiers.models import Dossier
from commandes.models import Commande


class Reclamation(models.Model):
    STATUT_CHOICES = [
        ("ouverte", "Ouverte"),
        ("en_investigation", "En investigation"),
        ("resolue", "Resolue"),
        ("rejetee", "Rejetee"),
    ]

    commande = models.ForeignKey(
        Commande, on_delete=models.PROTECT, related_name="reclamations",
    )
    dossiers_concernes = models.ManyToManyField(
        Dossier, related_name="reclamations",
        help_text="Toutes les parties concernees par le desaccord",
    )
    description = models.TextField("Description du desaccord")
    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="ouverte",
    )

    decision = models.TextField("Decision rendue", blank=True, default="")
    favorable_au_client = models.BooleanField(
        "Favorable au client", null=True, blank=True,
        help_text="Renseigne uniquement une fois la reclamation resolue",
    )
    resolu_avec_preuve = models.BooleanField(
        "Resolue avec preuve verifiable", null=True, blank=True,
    )
    resolu_par = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reclamations_resolues",
        help_text="L'acteur humain ayant tranche, si resolution non automatique",
    )

    created_at = models.DateTimeField("Ouverte le", auto_now_add=True)
    resolved_at = models.DateTimeField("Resolue le", null=True, blank=True)

    class Meta:
        verbose_name = "Reclamation"
        verbose_name_plural = "Reclamations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reclamation #{self.id} - Commande #{self.commande_id} - {self.get_statut_display()}"
