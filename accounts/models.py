"""
Module accounts - FAGNI Platform (Lot 1, Sprint 12)
Derive de FOS-211 v1.1 (section 9.1, Identity & Access).

Principe central : un Compte s'authentifie et agit ; le Dossier
(module dossiers) reste la memoire de ce qu'il a fait. Les deux ne se
confondent jamais - desactiver un Compte n'efface jamais l'historique
de son Dossier.
"""
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from dossiers.models import Dossier


class Organisation(models.Model):
    """
    Une entreprise cliente, un pressing a plusieurs employes, un futur
    franchise - regroupe plusieurs Comptes sous une meme entite.
    """
    TYPE_CHOICES = [
        ("entreprise_cliente", "Entreprise cliente"),
        ("pressing_multi_employes", "Pressing a plusieurs employes"),
        ("franchise", "Franchise"),
    ]

    nom = models.CharField("Nom", max_length=150)
    type_organisation = models.CharField(
        "Type", max_length=30, choices=TYPE_CHOICES,
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"

    def __str__(self):
        return f"{self.nom} ({self.get_type_organisation_display()})"


class Compte(models.Model):
    """
    L'identite qui s'authentifie et agit. Un Compte reference toujours
    un Dossier (memoire), mais n'est jamais confondu avec lui - un
    Compte peut etre desactive sans jamais toucher au Dossier sous-jacent.
    """
    ROLE_CHOICES = [
        ("membre", "Membre"),
        ("superviseur", "Superviseur"),
        ("administrateur", "Administrateur"),
    ]

    dossier = models.OneToOneField(
        Dossier, on_delete=models.PROTECT, related_name="compte",
    )
    organisation = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="comptes",
        help_text="Optionnel - un Compte peut ne dependre d'aucune organisation",
    )
    role = models.CharField(
        "Role", max_length=20, choices=ROLE_CHOICES, default="membre",
    )
    actif = models.BooleanField("Compte actif", default=True)
    mot_de_passe_hash = models.CharField(
        "Mot de passe (hache)", max_length=255, blank=True, default="",
        help_text="Jamais stocke en clair - toujours via definir_mot_de_passe()",
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    def definir_mot_de_passe(self, raw_password):
        """Hache et stocke le password."""
        self.mot_de_passe_hash = make_password(raw_password)
        self.save()
    
    def verifier_mot_de_passe(self, raw_password):
        """Vérifie un password en clair contre le hash stocké."""
        return check_password(raw_password, self.mot_de_passe_hash)

    class Meta:
        verbose_name = "Compte"
        verbose_name_plural = "Comptes"

    def __str__(self):
        etat = "actif" if self.actif else "inactif"
        return f"{self.dossier.nom} - {self.get_role_display()} ({etat})"
