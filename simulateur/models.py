"""
Module simulateur - FAGNI Platform (FOS-213 v1.3, Simulation Engine).
Derive du dossier Produit/UX "Simulateur Universel & Tunnel de Conversion
v1.2" (gele) - traduction technique uniquement, aucune redefinition
fonctionnelle.

Cross-backend par construction : le produit simule (abonnement
hebdomadaire) n'existe que cote V2 (module abonnements), mais le
frontend consommateur (fagni-client) et l'execution operationnelle
reelle restent en V1. Voir FOS-213 section 0.
"""
import secrets
from django.db import models


class Simulation(models.Model):
    """
    Une estimation demandee par un visiteur, avant creation de compte.
    sim_id : identifiant d'AFFICHAGE/SUPPORT uniquement, jamais utilise
    comme jeton d'acces (FOS-213 v1.2, correction de securite).
    resume_token : seul champ utilisable pour recuperer une Simulation
    via l'API - genere avec une entropie suffisante (secrets.token_urlsafe).
    """

    TAILLE_SAC_CHOICES = [("S", "S"), ("M", "M")]
    PACK_CHOICES = [("essentiel", "Essentiel"), ("confort", "Confort")]

    STATUT_CHOICES = [
        ("en_cours", "En cours"),
        ("resultat_affiche", "Resultat affiche"),
        ("envoyee_whatsapp", "Envoyee par WhatsApp"),
        ("reservee", "Reservee"),
        ("commande_creee", "Commande creee"),
        ("expiree", "Expiree"),
        # "abandonnee" volontairement absent (FOS-213 v1.3 section 5) -
        # jamais une transition reellement declenchee par le client,
        # uniquement une lecture derivee (voir services.py)
    ]

    sim_id = models.CharField("ID de reference", max_length=20, unique=True, db_index=True)
    resume_token = models.CharField(max_length=64, unique=True, db_index=True)

    service = models.CharField("Service", max_length=50, default="pressing")
    strategy_version = models.CharField("Version de strategie", max_length=30, default="pressing-v1")

    zone_code = models.CharField(
        "Zone", max_length=50,
        help_text="Liste fermee de zones pilote (ex: RIVIERA_3) - portee par configuration.Parametre.",
    )

    taille_sac = models.CharField("Taille sac", max_length=2, choices=TAILLE_SAC_CHOICES)
    pack = models.CharField("Pack", max_length=20, choices=PACK_CHOICES)

    prix_calcule = models.DecimalField("Prix calcule (FCFA)", max_digits=10, decimal_places=2)
    version_parametre_prix = models.ForeignKey(
        "configuration.VersionParametre", on_delete=models.PROTECT,
        related_name="simulations",
        help_text="Version tarifaire exacte utilisee pour ce calcul - jamais alteree retroactivement.",
    )

    nb_partenaires_disponibles = models.PositiveIntegerField("Partenaires disponibles", default=0)

    telephone = models.CharField("Telephone", max_length=20, blank=True, default="")
    nom = models.CharField("Nom", max_length=150, blank=True, default="")
    dossier = models.ForeignKey(
        "dossiers.Dossier", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="simulations",
    )
    abonnement = models.ForeignKey(
        "abonnements.Abonnement", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="simulation_origine",
    )

    simulation_precedente = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="versions_suivantes",
        help_text="Renseigne uniquement si cette Simulation nait du recalcul d'une simulation expiree.",
    )

    statut = models.CharField("Statut", max_length=20, choices=STATUT_CHOICES, default="en_cours")

    created_at = models.DateTimeField("Creee le", auto_now_add=True)
    updated_at = models.DateTimeField("Mise a jour le", auto_now=True)

    class Meta:
        verbose_name = "Simulation"
        verbose_name_plural = "Simulations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sim_id"]),
            models.Index(fields=["resume_token"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["statut", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.resume_token:
            self.resume_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sim_id} - {self.pack}/{self.taille_sac} - {self.get_statut_display()}"


class EvenementSimulation(models.Model):
    """
    Telemetrie legere - volontairement separee du vocabulaire
    evenements.Evenement (qui documente le cycle de vie METIER reel,
    Commande/Mission). Ici : instrumentation UX, jamais un fait metier
    engageant. Pas de garde-fou d'immuabilite contrairement a Evenement.
    """

    TYPE_EVENEMENT_CHOICES = [
        ("arrivee", "Arrivee"),
        ("etape_1", "Etape 1 (taille sac)"),
        ("etape_2", "Etape 2 (pack)"),
        ("resultat_affiche", "Resultat affiche"),
        ("whatsapp_ouvert", "WhatsApp ouvert"),
        ("reservation", "Reservation"),
        ("commande_creee", "Commande creee"),
    ]

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="events")
    type_evenement = models.CharField("Type", max_length=40, choices=TYPE_EVENEMENT_CHOICES)
    donnees = models.JSONField("Donnees", default=dict, blank=True)
    horodatage = models.DateTimeField("Horodate le", auto_now_add=True)

    class Meta:
        verbose_name = "Evenement de simulation"
        verbose_name_plural = "Evenements de simulation"
        ordering = ["-horodatage"]
        indexes = [models.Index(fields=["simulation", "type_evenement"])]

    def __str__(self):
        return f"{self.simulation.sim_id} - {self.get_type_evenement_display()}"
