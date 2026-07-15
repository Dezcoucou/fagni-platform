"""
Module capacites - FAGNI Platform (Lot 1, Sprint 8)
Derive de FOS-210 v1.1 (section 11, moteur de capacites).

Decision de gouvernance deja tranchee (FOS-212) : ce module est livre
maintenant, mais reste INACTIF dans l'orchestration du module missions
tant qu'un seul service est officiellement propose. Aucune contrainte
bloquante n'est ajoutee a missions/services.py a ce stade.
"""
from django.db import models
from dossiers.models import Dossier


class Capacite(models.Model):
    """
    Relation entre un Dossier partenaire et un Service precis - jamais
    une categorie entiere par defaut (FOS-210 section 11.1). Un excellent
    atelier textile peut ne declarer aucune capacite en cordonnerie.
    """
    dossier = models.ForeignKey(
        Dossier, on_delete=models.CASCADE, related_name="capacites",
    )
    service = models.CharField(
        "Service maitrise", max_length=100,
        help_text="Correspond au champ 'service' des lignes de commande",
    )
    niveau_confiance_service = models.PositiveSmallIntegerField(
        "Niveau de confiance sur ce service (0-100)", default=50,
        help_text="Distinct de la reputation generale du Dossier (BOS chapitre 4.5)",
    )
    volume_disponible = models.PositiveIntegerField(
        "Volume disponible", default=0,
        help_text="Ce que le partenaire peut reellement absorber sur ce service maintenant",
    )
    active = models.BooleanField("Capacite active", default=True)

    created_at = models.DateTimeField("Declaree le", auto_now_add=True)
    updated_at = models.DateTimeField("Mise a jour le", auto_now=True)

    class Meta:
        verbose_name = "Capacite"
        verbose_name_plural = "Capacites"
        constraints = [
            models.UniqueConstraint(
                fields=["dossier", "service"], name="unique_capacite_dossier_service",
            ),
        ]

    def __str__(self):
        etat = "active" if self.active else "inactive"
        return f"{self.dossier.nom} - {self.service} ({etat})"
