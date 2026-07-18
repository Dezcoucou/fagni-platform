"""
Module missions - FAGNI Platform (Lot 1, Sprint 4)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objet Mission) et de FOS-211 v1.1
(section 2.3).
"""
from django.db import models
from dossiers.models import Dossier
from workflows.models import Workflow
from commandes.models import Commande, LigneCommande


class Mission(models.Model):
    """
    Une action physique unique confiee a un acteur d'execution (BOS
    chapitre 3). Ne peut etre assignee qu'a un Dossier utilisable
    (statut actif - dossiers.est_utilisable()) - verifie dans services.py,
    jamais suppose.
    """
    TYPE_MISSION_CHOICES = [
        ("collecte", "Collecte"),
        ("livraison", "Livraison"),
        ("transport_intermediaire", "Transport intermediaire"),
    ]

    STATUT_CHOICES = [
        ("proposee", "Proposee"),
        ("acceptee", "Acceptee"),
        ("en_cours", "En cours"),
        ("terminee", "Terminee"),
        ("refusee", "Refusee"),
    ]

    type_mission = models.CharField(
        "Type de mission", max_length=30, choices=TYPE_MISSION_CHOICES,
    )
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="missions",
    )
    ligne_commande = models.ForeignKey(
        LigneCommande, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="missions",
        help_text="Optionnel - la mission peut concerner une ligne precise ou toute la commande",
    )
    acteur_assigne = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="missions_assignees",
    )
    workflow = models.ForeignKey(
        Workflow, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="missions",
        help_text="Workflow selectionne par orchestrateur.selectionner_workflow() au moment de la creation - trace, jamais suppose.",
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="proposee",
    )
    created_at = models.DateTimeField("Creee le", auto_now_add=True)
    updated_at = models.DateTimeField("Mise a jour le", auto_now=True)

    class Meta:
        verbose_name = "Mission"
        verbose_name_plural = "Missions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_mission_display()} - {self.acteur_assigne.nom} - {self.get_statut_display()}"
