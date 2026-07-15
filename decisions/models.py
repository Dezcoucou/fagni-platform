"""
Module decisions - FAGNI Platform (Lot 1, Sprint 10)
Derive du BOS FAGNI 2035 v2.0 (chapitre 12, systeme de decision) et de
FOS-210 v1.1 (section 10, RACI metier).

Regle centrale, BOS chapitre 7.2 et 12.3 : trois conditions rendent une
decision automatisable (regle connue, preuve disponible, erreur
reversible) - MAIS certaines decisions restent toujours humaines quelles
que soient les conditions (l'exclusion d'un Dossier, notamment). Ce
module distingue explicitement ces deux logiques.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from dossiers.models import Dossier


class ReglaDecision(models.Model):
    """
    Definit, pour un contexte donne, si la decision peut suivre la
    logique des trois conditions (BOS 12.3) ou reste TOUJOURS humaine
    par principe (BOS 7.2), sans exception possible.
    """
    code = models.CharField("Code", max_length=100, unique=True)
    description = models.TextField("Description", blank=True, default="")
    toujours_humaine = models.BooleanField(
        "Toujours humaine (aucune exception)", default=False,
        help_text="BOS chapitre 7.2 - ex: exclusion definitive d'un Dossier",
    )

    class Meta:
        verbose_name = "Regle de decision"
        verbose_name_plural = "Regles de decision"

    def __str__(self):
        suffixe = " [TOUJOURS HUMAINE]" if self.toujours_humaine else ""
        return f"{self.code}{suffixe}"


class Decision(models.Model):
    """
    Trace chaque decision reellement prise - le niveau applique (chapitre
    12), qui a decide si humain, et sur quel objet transitoire elle porte.
    """
    NIVEAU_CHOICES = [
        ("automatique", "Automatique"),
        ("assistee", "Assistee"),
        ("humaine", "Humaine"),
    ]

    regle = models.ForeignKey(
        ReglaDecision, on_delete=models.PROTECT, related_name="decisions",
    )
    niveau_applique = models.CharField(
        "Niveau applique", max_length=20, choices=NIVEAU_CHOICES,
    )
    decideur = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decisions_prises",
        help_text="Renseigne obligatoirement si niveau_applique='humaine'",
    )

    objet_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
    )
    objet_id = models.PositiveIntegerField(null=True, blank=True)
    objet_source = GenericForeignKey("objet_type", "objet_id")

    justification = models.TextField("Justification", blank=True, default="")
    created_at = models.DateTimeField("Prise le", auto_now_add=True)

    class Meta:
        verbose_name = "Decision"
        verbose_name_plural = "Decisions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.regle.code} - {self.get_niveau_applique_display()} - {self.created_at}"
