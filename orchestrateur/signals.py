"""
Signaux du module orchestrateur - FAGNI Platform (Lot 3, suite Sprint 19).

Notifie automatiquement quand une etape de workflow tracee sur une
Mission est franchie - jamais de creation automatique de la mission
suivante (decision de gouvernance, coherente avec BOS chapitre 12 :
decision assistee, pas encore une optimisation reelle - meme principe
que capacites_activees, reste dormant jusqu'a activation explicite).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from evenements.models import Evenement
from missions.models import Mission
from dossiers.models import Dossier
from notifications.services import envoyer_notification


@receiver(post_save, sender=Evenement)
def notifier_etape_workflow_franchie(sender, instance, created, **kwargs):
    """
    A chaque nouvel Evenement, verifie s'il correspond a une etape
    attendue dans le workflow trace d'une ou plusieurs Missions liees
    (directement, ou via la Commande source) - et notifie si oui.
    Silencieux si aucune mission concernee, jamais bloquant.
    """
    if not created:
        return

    evenement = instance
    missions_concernees = []

    if evenement.objet_source_type is not None:
        model_class = evenement.objet_source_type.model_class()
        if model_class is Mission:
            missions_concernees = list(
                Mission.objects.filter(id=evenement.objet_source_id, workflow__isnull=False)
            )
        elif model_class is not None and model_class._meta.model_name == "commande":
            missions_concernees = list(
                Mission.objects.filter(commande_id=evenement.objet_source_id, workflow__isnull=False)
            )

    for mission in missions_concernees:
        etapes = mission.workflow.etapes.filter(type_evenement=evenement.type_evenement)
        if not etapes.exists():
            continue

        destinataires = [mission.acteur_assigne] + list(
            Dossier.objects.filter(type_acteur="ops", statut="actif")
        )
        for dossier in destinataires:
            envoyer_notification(
                dossier, "push", evenement,
                f"Etape '{evenement.get_type_evenement_display()}' franchie "
                f"pour la mission #{mission.id} (workflow {mission.workflow.nom}).",
            )
