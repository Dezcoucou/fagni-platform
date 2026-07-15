"""
Module commandes - FAGNI Platform (Lot 1, Sprint 3)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objets Commande/Article/Service)
et de FOS-211 v1.1 (section 2.2).

Decision ouverte tranchee (voir FOS-212, decisions de gouvernance) :
statut PAR LIGNE, pas de statut global sur la Commande elle-meme - une
commande contenant plusieurs prestations differentes peut avoir des lignes
a des stades differents simultanement.
"""
from django.db import models
from dossiers.models import Dossier


class Commande(models.Model):
    """
    L'engagement du client (BOS chapitre 3). Le prix engage est verrouille
    (BOS chapitre 4.1) : il ne peut jamais etre revise a la hausse sans
    accord explicite du client - regle appliquee dans services.py, jamais
    contournable par une simple modification directe du champ.
    """
    dossier_client = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="commandes",
    )
    prix_engage = models.DecimalField(
        "Prix engage (FCFA)", max_digits=10, decimal_places=2,
    )
    delai_annonce = models.CharField(
        "Delai annonce", max_length=100, blank=True, default="",
    )
    created_at = models.DateTimeField("Creee le", auto_now_add=True)
    updated_at = models.DateTimeField("Mise a jour le", auto_now=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commande #{self.id} - {self.dossier_client.nom} - {self.prix_engage} FCFA"


class LigneCommande(models.Model):
    """
    Une ligne = un Article + un Service + un Niveau de service (FOS-210
    section 1.3). Chaque ligne a SON PROPRE statut, independant des autres
    lignes de la meme Commande.
    """
    NIVEAU_SERVICE_CHOICES = [
        ("complet", "Traitement complet"),
        ("partiel", "Traitement partiel"),
        ("specialise", "Intervention specialisee"),
    ]

    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("collecte", "Collectee"),
        ("en_traitement", "En traitement"),
        ("terminee", "Terminee"),
        ("livree", "Livree"),
        ("annulee", "Annulee"),
    ]

    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="lignes",
    )
    article = models.CharField("Article", max_length=150)
    service = models.CharField("Service", max_length=100)
    niveau_service = models.CharField(
        "Niveau de service", max_length=20, choices=NIVEAU_SERVICE_CHOICES,
        default="complet",
    )
    quantite = models.PositiveIntegerField("Quantite", default=1)
    prix_unitaire = models.DecimalField(
        "Prix unitaire (FCFA)", max_digits=10, decimal_places=2,
    )
    statut = models.CharField(
        "Statut de la ligne", max_length=20, choices=STATUT_CHOICES,
        default="en_attente",
    )

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"

    def __str__(self):
        return f"{self.article} x{self.quantite} ({self.get_niveau_service_display()}) - {self.get_statut_display()}"

    @property
    def total_ligne(self):
        return self.prix_unitaire * self.quantite
