"""
Module notifications - FAGNI Platform (Lot 1, Sprint 14 - dernier module
du Core Domain)
Derive du BOS FAGNI 2035 v2.0 (chapitre 5, flux de notifications) et de
FOS-211 v1.1 (section 9.4).

Lecon retenue directement du pilote V1 : un tag anti-doublon avait du
etre ajoute a posteriori sur l'app driver pour eviter les notifications
envoyees deux fois pour le meme evenement. Ici, la contrainte d'unicite
est posee des le modele, jamais ajoutee apres coup.
"""
from django.db import models
from dossiers.models import Dossier
from evenements.models import Evenement


class Notification(models.Model):
    CANAL_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("push", "Notification push"),
        ("email", "Email"),
    ]

    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("envoyee", "Envoyee"),
        ("echouee", "Echouee"),
    ]

    dossier_destinataire = models.ForeignKey(
        Dossier, on_delete=models.CASCADE, related_name="notifications",
    )
    canal = models.CharField("Canal", max_length=20, choices=CANAL_CHOICES)
    evenement_declencheur = models.ForeignKey(
        Evenement, on_delete=models.CASCADE, related_name="notifications",
        help_text="Toute notification est declenchee par un Evenement precis (BOS chapitre 5)",
    )
    contenu = models.TextField("Contenu")
    statut_envoi = models.CharField(
        "Statut d'envoi", max_length=20, choices=STATUT_CHOICES, default="en_attente",
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["dossier_destinataire", "canal", "evenement_declencheur"],
                name="unique_notification_par_dossier_canal_evenement",
            ),
        ]

    def __str__(self):
        return f"{self.get_canal_display()} -> {self.dossier_destinataire.nom} ({self.get_statut_envoi_display()})"
