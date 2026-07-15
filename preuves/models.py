"""
Module preuves - FAGNI Platform (Lot 1, Sprint 5)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objet Preuve) et de FOS-211 v1.1
(section 2.5).

Regle absolue, identique a Evenement (Sprint 2) : une Preuve, une fois
capturee, n'est jamais modifiee ni supprimee. Reutilise directement le
correctif QuerySet decouvert au Sprint 2 - la meme faille ne doit jamais
se reproduire ailleurs dans le Core Domain.
"""
from django.db import models
from dossiers.models import Dossier
from missions.models import Mission
from evenements.models import Evenement


class PreuveQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise ValueError(
            "Une Preuve est immuable (BOS chapitre 3) - "
            "la suppression en masse via QuerySet est interdite."
        )


class PreuveManager(models.Manager):
    def get_queryset(self):
        return PreuveQuerySet(self.model, using=self._db)


class Preuve(models.Model):
    TYPE_PREUVE_CHOICES = [
        ("photo", "Photo"),
        ("signature", "Signature"),
        ("declaration_texte", "Declaration texte"),
        ("position_gps", "Position GPS"),
    ]

    type_preuve = models.CharField(
        "Type de preuve", max_length=30, choices=TYPE_PREUVE_CHOICES,
    )
    mission = models.ForeignKey(
        Mission, on_delete=models.PROTECT, related_name="preuves",
    )
    evenement = models.ForeignKey(
        Evenement, on_delete=models.PROTECT, related_name="preuves",
        help_text="L'Evenement precis que cette Preuve vient etayer",
    )
    dossier_capturant = models.ForeignKey(
        Dossier, on_delete=models.PROTECT, related_name="preuves_capturees",
        help_text="L'acteur qui a physiquement capture cette preuve",
    )

    fichier = models.FileField(
        "Fichier (photo, signature)", upload_to="preuves/", null=True, blank=True,
    )
    contenu_texte = models.TextField(
        "Contenu texte (declaration, notes)", blank=True, default="",
    )
    metadonnees = models.JSONField(
        "Metadonnees (GPS, contexte)", default=dict, blank=True,
    )

    horodatage = models.DateTimeField("Capturee le", auto_now_add=True)

    objects = PreuveManager()

    class Meta:
        verbose_name = "Preuve"
        verbose_name_plural = "Preuves"
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.get_type_preuve_display()} - Mission #{self.mission_id} - {self.horodatage}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError(
                "Une Preuve est immuable (BOS chapitre 3) - "
                "elle ne peut jamais etre modifiee apres sa capture."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "Une Preuve est immuable (BOS chapitre 3) - "
            "elle ne peut jamais etre supprimee."
        )
