"""
Module workflows - FAGNI Platform (Lot 1, Sprint 9)
Derive de FOS-210 v1.1 (section 12, workflows configurables).

Principe central : un Workflow n'est jamais une nouvelle chaine
d'evenements inventee - c'est une composition ordonnee a partir du
vocabulaire commun deja defini dans evenements.Evenement.TYPE_EVENEMENT_CHOICES
(FOS-210 section 9). Ajouter un metier = configurer une sequence, jamais
reecrire les principes deja poses.
"""
from django.db import models
from evenements.models import Evenement


class Workflow(models.Model):
    """
    Une configuration de sequence propre a un service ou un metier.
    Exemple : "pressing_standard" suit la chaine de reference sans ecart ;
    "cordonnerie" y insere une etape de devis obligatoire.
    """
    nom = models.CharField("Nom", max_length=100, unique=True)
    description = models.TextField("Description", blank=True, default="")
    service_associe = models.CharField(
        "Service associe", max_length=100,
        help_text="Correspond au champ 'service' des lignes de commande",
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    class Meta:
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"

    def __str__(self):
        return f"{self.nom} ({self.service_associe})"


class EtapeWorkflow(models.Model):
    """
    Une etape dans la sequence - reference directement un type d'evenement
    du vocabulaire commun (evenements.Evenement), jamais un type invente
    localement.
    """
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="etapes",
    )
    type_evenement = models.CharField(
        "Type d'evenement", max_length=40, choices=Evenement.TYPE_EVENEMENT_CHOICES,
    )
    ordre = models.PositiveIntegerField("Ordre dans la sequence")
    obligatoire = models.BooleanField("Etape obligatoire", default=True)

    class Meta:
        verbose_name = "Etape de workflow"
        verbose_name_plural = "Etapes de workflow"
        ordering = ["workflow", "ordre"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "ordre"], name="unique_ordre_par_workflow",
            ),
        ]

    def __str__(self):
        return f"{self.workflow.nom} #{self.ordre} - {self.get_type_evenement_display()}"
