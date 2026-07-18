"""
Module abonnements - FAGNI Platform.
Derive du principe deja etabli en V1 (pilote Cocody, module Subscription
jamais utilise en production - 0 abonnement cree) - meme concept metier
repris (pack, taille de sac, jour fixe de collecte/livraison), mais
implementation neuve, coherente avec l'architecture V2 : le prix n'est
jamais code en dur, toujours lu depuis configuration.services au moment
de la generation (FOS-211 section 9.2).
"""
from django.db import models
from dossiers.models import Dossier


class Abonnement(models.Model):
    """
    Un engagement recurrent d'un client (BOS chapitre 3, meme famille
    que Commande mais jamais confondu avec elle - une Commande est
    generee A PARTIR d'un Abonnement a chaque echeance, via services.py,
    jamais l'inverse).
    """
    PACK_CHOICES = [
        ("essentiel", "Essentiel"),
        ("confort", "Confort"),
    ]

    TAILLE_SAC_CHOICES = [
        ("S", "Sac S"),
        ("M", "Sac M"),
    ]

    JOUR_CHOICES = [
        (0, "Lundi"), (1, "Mardi"), (2, "Mercredi"), (3, "Jeudi"),
        (4, "Vendredi"), (5, "Samedi"), (6, "Dimanche"),
    ]

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("suspendu", "Suspendu"),
        ("resilie", "Resilie"),
    ]

    dossier_client = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="abonnements",
    )
    pack = models.CharField("Pack", max_length=20, choices=PACK_CHOICES)
    taille_sac = models.CharField("Taille sac", max_length=2, choices=TAILLE_SAC_CHOICES)
    jour_collecte = models.PositiveSmallIntegerField("Jour collecte", choices=JOUR_CHOICES)
    jour_livraison = models.PositiveSmallIntegerField("Jour livraison", choices=JOUR_CHOICES)

    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="actif",
    )
    date_debut = models.DateField("Date de debut", null=True, blank=True)

    created_at = models.DateTimeField("Cree le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis a jour le", auto_now=True)

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Abonnement {self.get_pack_display()} - {self.dossier_client.nom} ({self.get_statut_display()})"

    def est_actif(self):
        return self.statut == "actif"
