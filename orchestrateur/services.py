"""
Services internes du module orchestrateur - FAGNI Platform (Lot 3, Sprint 19)
Derive de FOS-211 (Lot 3 - "le veritable cerveau de FAGNI, il decide
quel partenaire, quel livreur, quelles notifications").

Respecte la decision de gouvernance deja prise (Sprint 8, FOS-212) : le
filtrage par capacites reste desactive par defaut - active uniquement
via un parametre de configuration, jamais code en dur, jamais suppose.
"""
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from dossiers.models import Dossier
from capacites.services import lister_partenaires_compatibles
from configuration.services import obtenir_valeur_courante, ParametreInconnu
from missions.services import proposer_mission
from evenements.models import Evenement
from notifications.services import envoyer_notification
from workflows.models import Workflow
from workflows.services import obtenir_sequence


def capacites_activees():
    """
    Lit le parametre 'orchestrateur_utiliser_capacites' - jamais code en
    dur. Absent = False par defaut, coherent avec la decision de
    gouvernance du Sprint 8 : un seul service actif ne justifie pas
    encore ce filtrage.
    """
    try:
        valeur = obtenir_valeur_courante("orchestrateur_utiliser_capacites")
        return valeur.lower() == "true"
    except ParametreInconnu:
        return False


def suggerer_partenaires(service, type_acteur="partenaire"):
    """
    Si les capacites sont desactivees : retourne tous les Dossiers actifs
    du type demande, sans filtrage (comportement historique V1).
    Si activees : filtre reellement par compatibilite declaree
    (FOS-210 section 11.2) - la premiere vraie connexion du moteur de
    capacites, longtemps reste inactif depuis le Sprint 8.
    """
    if capacites_activees():
        compatibles = lister_partenaires_compatibles(service)
        return [c.dossier for c in compatibles if c.dossier.est_utilisable()]

    return list(Dossier.objects.filter(type_acteur=type_acteur, statut="actif"))


@transaction.atomic
def orchestrer_mission(type_mission, commande, service, acteur_assigne=None, ligne_commande=None):
    """
    Point d'entree principal : cree la Mission via missions.services
    (jamais directement), puis declenche automatiquement les
    notifications du role "Informe" (RACI, FOS-210 section 10).

    Sans acteur_assigne fourni, choisit automatiquement une suggestion -
    decision assistee (BOS chapitre 12), pas encore une optimisation reelle.
    """
    if acteur_assigne is None:
        suggestions = suggerer_partenaires(service)
        if not suggestions:
            raise ValueError(f"Aucun partenaire disponible pour le service '{service}'.")
        acteur_assigne = suggestions[0]

    mission = proposer_mission(type_mission, commande, acteur_assigne, ligne_commande)

    workflow = selectionner_workflow(service)
    if workflow is not None:
        mission.workflow = workflow
        mission.save(update_fields=["workflow"])

    content_type = ContentType.objects.get_for_model(mission)
    evenement = Evenement.objects.filter(
        objet_source_type=content_type, objet_source_id=mission.id, type_evenement="mission_creee",
    ).latest("horodatage")

    envoyer_notification(
        acteur_assigne, "push", evenement,
        f"Nouvelle mission {type_mission} pour la commande #{commande.id}",
    )
    envoyer_notification(
        commande.dossier_client, "push", evenement,
        f"Votre commande #{commande.id} a ete assignee.",
    )

    return mission

def selectionner_workflow(service):
    """
    Retourne le Workflow configure pour ce service (FOS-210 section 12).
    Retourne None si aucun workflow n'a encore ete configure pour ce
    service - jamais une erreur bloquante, un simple signal que ce
    service suit encore le comportement par defaut, non formalise.
    """
    return Workflow.objects.filter(service_associe=service).first()


def etat_execution(mission):
    """
    Derive l'etat d'avancement de la mission dans son workflow trace -
    jamais un nouvel etat stocke, uniquement deduit des Evenement deja
    emis (BOS chapitre 9, immuabilite) pour la Mission ET sa Commande
    parente (la sequence d'un Workflow peut melanger les deux origines).

    Retourne None si aucun workflow n'a ete trace sur cette mission
    (selectionner_workflow n'a rien trouve au moment de l'orchestration).
    """
    if mission.workflow is None:
        return None

    sequence = obtenir_sequence(mission.workflow)

    types_realises = set(
        Evenement.objects.filter(
            objet_source_type=ContentType.objects.get_for_model(mission),
            objet_source_id=mission.id,
        ).values_list("type_evenement", flat=True)
    ) | set(
        Evenement.objects.filter(
            objet_source_type=ContentType.objects.get_for_model(mission.commande),
            objet_source_id=mission.commande.id,
        ).values_list("type_evenement", flat=True)
    )

    etapes_etat = [
        {"etape": etape, "realisee": etape.type_evenement in types_realises}
        for etape in sequence
    ]

    etape_courante = None
    prochaine_etape = None
    for item in etapes_etat:
        if item["realisee"]:
            etape_courante = item["etape"]
        elif prochaine_etape is None:
            prochaine_etape = item["etape"]

    return {
        "workflow": mission.workflow,
        "etapes": etapes_etat,
        "etape_courante": etape_courante,
        "prochaine_etape": prochaine_etape,
        "termine": prochaine_etape is None,
    }
