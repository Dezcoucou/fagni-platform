"""
Module dossiers - FAGNI Platform (Lot 1, Sprint 1)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objet Dossier) et de FOS-211 v1.1 (section 2.1).

Le Dossier est la memoire permanente d'un acteur. Il ne se cloture jamais.
Tous les autres objets metier (Commande, Mission, Evenement...) sont transitoires
et se rattachent a un ou plusieurs Dossiers - jamais l'inverse comme relation
structurante principale.
"""
from django.db import models


class Dossier(models.Model):
    TYPE_ACTEUR_CHOICES = [
        ("client", "Client"),
        ("livreur", "Livreur"),
        ("partenaire", "Partenaire (atelier)"),
        ("artisan", "Artisan specialise"),
        ("ops", "Responsable OPS"),
        ("organisation", "Organisation (entreprise, hotel, etc.)"),
    ]

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("suspendu", "Suspendu"),
        ("exclu", "Exclu"),
    ]

    type_acteur = models.CharField(
        "Type d'acteur", max_length=20, choices=TYPE_ACTEUR_CHOICES,
    )
    nom = models.CharField("Nom", max_length=150)
    telephone = models.CharField("Telephone", max_length=20, blank=True, default="")

    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="actif",
    )

    # Niveau de confiance : stocke ici, mais jamais modifie directement par une
    # application externe (FOS-211 section 5.3). Sera recalcule par le module
    # evenements/analytics une fois ces modules construits. Valeur neutre par defaut.
    niveau_confiance = models.PositiveSmallIntegerField(
        "Niveau de confiance (0-100)", default=50,
    )

    date_ouverture = models.DateTimeField("Ouvert le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis a jour le", auto_now=True)

    class Meta:
        verbose_name = "Dossier"
        verbose_name_plural = "Dossiers"
        ordering = ["-date_ouverture"]

    def __str__(self):
        return f"{self.nom} ({self.get_type_acteur_display()}) - {self.get_statut_display()}"

    def est_utilisable(self):
        """
        Un Dossier suspendu ou exclu ne peut pas recevoir de nouvelle Mission
        ni de nouvelle Commande (BOS chapitre 7.2 - decision humaine uniquement
        pour l'exclusion, jamais automatique).
        """
        return self.statut == "actif"


class EntreeHistoriqueConfiance(models.Model):
    """
    Trace chaque changement du niveau de confiance d'un Dossier, avec sa cause.
    Immuable une fois cree (coherent avec le principe des Evenements, BOS chapitre 9).
    """
    dossier = models.ForeignKey(
        Dossier, on_delete=models.CASCADE, related_name="historique_confiance",
    )
    ancien_niveau = models.PositiveSmallIntegerField("Ancien niveau")
    nouveau_niveau = models.PositiveSmallIntegerField("Nouveau niveau")
    raison = models.CharField("Raison du changement", max_length=255)
    created_at = models.DateTimeField("Enregistre le", auto_now_add=True)

    class Meta:
        verbose_name = "Entree d'historique de confiance"
        verbose_name_plural = "Historique de confiance"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.dossier.nom} : {self.ancien_niveau} -> {self.nouveau_niveau}"
