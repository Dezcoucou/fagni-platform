"""
Module evenements - FAGNI Platform (Lot 1, Sprint 2)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objet Evenement) et de FOS-210 v1.1
(section 9, moteur d'evenements) et FOS-211 v1.1 (section 2.4).

Regle absolue : un evenement, une fois cree, n'est JAMAIS modifie ni supprime
(BOS chapitre 9, invariant). Ce module l'applique techniquement, pas seulement
par convention.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from dossiers.models import Dossier


class EvenementQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise ValueError(
            "Un Evenement est immuable (BOS chapitre 9) - "
            "la suppression en masse via QuerySet est interdite, "
            "exactement comme la suppression individuelle."
        )


class EvenementManager(models.Manager):
    def get_queryset(self):
        return EvenementQuerySet(self.model, using=self._db)


class Evenement(models.Model):
    """
    Chaine de reference (FOS-210 v1.1, section 9.1) :
    commande_creee -> collecte_commencee -> collecte_terminee -> inspection_realisee
    -> paiement_confirme -> mission_creee -> mission_acceptee -> service_termine
    -> controle_qualite_realise -> livraison_effectuee -> avis_recu -> cloture

    D'autres types peuvent s'ajouter au fil des modules suivants (workflows
    configurables, FOS-210 section 12) - la liste ci-dessous n'est pas figee,
    mais chaque nouvel ajout doit etre documente dans le Pilot Book / Execution
    Book, jamais improvise silencieusement dans le code.
    """
    TYPE_EVENEMENT_CHOICES = [
        ("commande_creee", "Commande creee"),
        ("collecte_commencee", "Collecte commencee"),
        ("collecte_terminee", "Collecte terminee"),
        ("inspection_realisee", "Inspection realisee"),
        ("paiement_confirme", "Paiement confirme"),
        ("mission_creee", "Mission creee"),
        ("mission_acceptee", "Mission acceptee"),
        ("service_termine", "Service termine"),
        ("controle_qualite_realise", "Controle qualite realise"),
        ("livraison_effectuee", "Livraison effectuee"),
        ("avis_recu", "Avis recu"),
        ("cloture", "Cloture"),
        ("autre", "Autre (specifique a un workflow)"),
    ]

    type_evenement = models.CharField(
        "Type d'evenement", max_length=40, choices=TYPE_EVENEMENT_CHOICES,
    )

    # Toujours rattache a au moins un Dossier (FOS-211 section 2.4). Plusieurs
    # Dossiers peuvent etre concernes par le meme evenement (ex: client ET livreur
    # pour une collecte terminee).
    dossiers_concernes = models.ManyToManyField(
        Dossier, related_name="evenements", verbose_name="Dossiers concernes",
    )

    # L'acteur precis qui a declenche l'evenement (peut etre None si systeme/automatique)
    acteur_origine = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evenements_declenches", verbose_name="Acteur a l'origine",
    )

    # Reference generique vers l'objet transitoire source (Commande, Mission...).
    # Generique car les modules commandes/missions n'existent pas encore -
    # evite une dependance directe qui casserait la frontiere entre modules
    # (FOS-211 section 5.2).
    objet_source_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
    )
    objet_source_id = models.PositiveIntegerField(null=True, blank=True)
    objet_source = GenericForeignKey("objet_source_type", "objet_source_id")

    donnees = models.JSONField("Donnees complementaires", default=dict, blank=True)

    horodatage = models.DateTimeField("Horodate le", auto_now_add=True)

    objects = EvenementManager()

    class Meta:
        verbose_name = "Evenement"
        verbose_name_plural = "Evenements"
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.get_type_evenement_display()} - {self.horodatage}"

    def save(self, *args, **kwargs):
        """
        Immutabilite technique : une fois cree (pk existant), aucune
        modification n'est autorisee. Seule la creation initiale passe.
        """
        if self.pk is not None:
            raise ValueError(
                "Un Evenement est immuable (BOS chapitre 9) - "
                "il ne peut jamais etre modifie apres sa creation."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "Un Evenement est immuable (BOS chapitre 9) - "
            "il ne peut jamais etre supprime."
        )
