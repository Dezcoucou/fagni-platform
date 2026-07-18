"""
Services internes du module missions - FAGNI Platform (Lot 1, Sprint 4)

proposer_mission() verifie systematiquement dossiers.Dossier.est_utilisable()
avant toute assignation - premiere verification reelle de cette regle,
posee au Sprint 1 mais jamais encore testee en integration.
"""
from django.db import transaction
from evenements.services import emettre_evenement
from .models import Mission


class ActeurNonUtilisable(Exception):
    """Leve quand une Mission est proposee a un Dossier suspendu ou exclu."""
    pass


@transaction.atomic
def proposer_mission(type_mission, commande, acteur_assigne, ligne_commande=None, workflow=None):
    """
    Propose une Mission a un acteur d'execution. Refuse explicitement si
    l'acteur n'est pas utilisable (BOS chapitre 7.2 - un Dossier suspendu
    ou exclu ne peut jamais recevoir de nouvelle Mission).

    workflow : optionnel, deja resolu par l'appelant (orchestrateur) -
    fourni des la creation pour que le signal de notification (Sprint 19
    suite) puisse le voir des le tout premier evenement mission_creee,
    jamais assigne apres coup.
    """
    if not acteur_assigne.est_utilisable():
        raise ActeurNonUtilisable(
            f"Le Dossier de {acteur_assigne.nom} n'est pas utilisable "
            f"(statut: {acteur_assigne.get_statut_display()}) - "
            f"aucune Mission ne peut lui etre proposee."
        )

    mission = Mission.objects.create(
        type_mission=type_mission,
        commande=commande,
        ligne_commande=ligne_commande,
        acteur_assigne=acteur_assigne,
        workflow=workflow,
    )

    emettre_evenement(
        type_evenement="mission_creee",
        dossiers_concernes=[commande.dossier_client, acteur_assigne],
        acteur_origine=acteur_assigne,
        objet_source=mission,
        donnees={"type_mission": type_mission},
    )

    return mission


def accepter_mission(mission):
    """Le passage a 'acceptee' produit son propre evenement (chaine de reference)."""
    mission.statut = "acceptee"
    mission.save(update_fields=["statut", "updated_at"])

    emettre_evenement(
        type_evenement="mission_acceptee",
        dossiers_concernes=[mission.commande.dossier_client, mission.acteur_assigne],
        acteur_origine=mission.acteur_assigne,
        objet_source=mission,
    )
    return mission


def refuser_mission(mission, raison=""):
    """Une Mission refusee reste tracee - jamais simplement supprimee."""
    mission.statut = "refusee"
    mission.save(update_fields=["statut", "updated_at"])

    emettre_evenement(
        type_evenement="autre",
        dossiers_concernes=[mission.commande.dossier_client, mission.acteur_assigne],
        acteur_origine=mission.acteur_assigne,
        objet_source=mission,
        donnees={"sous_type": "mission_refusee", "raison": raison},
    )
    return mission


def terminer_mission(mission):
    mission.statut = "terminee"
    mission.save(update_fields=["statut", "updated_at"])
    return mission
