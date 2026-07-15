"""
Module ajustements - FAGNI Platform (Lot 2, Sprint 16)
Derive de FOS-210 v1.1 (chapitre 6, moteur de pricing - "definir les
regles quand le panier reel differe du panier declare") et du BOS
chapitre 4.1.

Regle centrale : un deficit (moins d'articles que declares) se
rembourse automatiquement - le doute profite au client. Un excedent
(plus d'articles que declares) n'est jamais facture automatiquement,
il attend toujours une confirmation explicite (BOS 4.1 - une hausse
n'est jamais imposee sans accord).
"""
from django.db import models
from commandes.models import Commande, LigneCommande


class AjustementCommande(models.Model):
    TYPE_CHOICES = [
        ("deficit", "Deficit (moins que declare)"),
        ("excedent", "Excedent (plus que declare)"),
    ]

    STATUT_CHOICES = [
        ("automatique_applique", "Applique automatiquement"),
        ("en_attente_complement", "En attente de complement client"),
        ("complement_paye", "Complement paye"),
        ("complement_refuse", "Complement refuse par le client"),
    ]

    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="ajustements",
    )
    ligne_commande = models.OneToOneField(
        LigneCommande, on_delete=models.CASCADE, related_name="ajustement",
        help_text="Un seul ajustement possible par ligne - empeche structurellement le rejeu double",
    )
    type_ajustement = models.CharField("Type", max_length=20, choices=TYPE_CHOICES)
    quantite_declaree = models.PositiveIntegerField("Quantite declaree")
    quantite_reelle = models.PositiveIntegerField("Quantite reelle constatee")
    montant_ajustement = models.DecimalField(
        "Montant de l'ajustement (FCFA)", max_digits=10, decimal_places=2,
    )
    statut = models.CharField(
        "Statut", max_length=30, choices=STATUT_CHOICES,
    )
    created_at = models.DateTimeField("Constate le", auto_now_add=True)

    class Meta:
        verbose_name = "Ajustement de commande"
        verbose_name_plural = "Ajustements de commande"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_ajustement_display()} - Commande #{self.commande_id} - {self.montant_ajustement} FCFA"
