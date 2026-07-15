"""
Services internes du module reclamations - FAGNI Platform (Lot 1, Sprint 6)

Applique une regle nuancee du BOS chapitre 4.2 : "Aucune reclamation ne
peut etre tranchee sans preuve verifiable ; en son absence, le doute
profite au client." Ce n'est PAS une interdiction de resoudre sans preuve -
c'est une regle qui force la resolution en faveur du client quand la
preuve manque, jamais une erreur bloquante.
"""
from django.utils import timezone
from django.db import transaction
from evenements.services import emettre_evenement
from .models import Reclamation


@transaction.atomic
def ouvrir_reclamation(commande, dossiers_concernes, description):
    """
    Ouvrir une reclamation ne necessite jamais de preuve prealable - le
    client n'a pas a apporter la preuve lui-meme pour etre entendu.
    """
    reclamation = Reclamation.objects.create(
        commande=commande, description=description,
    )
    reclamation.dossiers_concernes.set(dossiers_concernes)

    emettre_evenement(
        type_evenement="reclamation_ouverte",
        dossiers_concernes=dossiers_concernes,
        objet_source=reclamation,
        donnees={"description": description},
    )
    return reclamation


@transaction.atomic
def resoudre_reclamation(reclamation, decision, preuves=None, favorable_au_client=None, resolu_par=None):
    """
    BOS chapitre 4.2 applique ici :
    - Si des preuves existent, la decision (favorable_au_client) suit ce
      qui a ete determine par ailleurs (humain ou automatique).
    - Si AUCUNE preuve n'est fournie, la resolution est FORCEE en faveur
      du client, quelle que soit la valeur de favorable_au_client passee -
      jamais une erreur, toujours ce comportement protecteur par defaut.
    """
    a_des_preuves = bool(preuves)

    if not a_des_preuves:
        favorable_au_client_final = True  # force, quoi qu'il arrive
    else:
        favorable_au_client_final = favorable_au_client

    reclamation.statut = "resolue"
    reclamation.decision = decision
    reclamation.favorable_au_client = favorable_au_client_final
    reclamation.resolu_avec_preuve = a_des_preuves
    reclamation.resolu_par = resolu_par
    reclamation.resolved_at = timezone.now()
    reclamation.save(update_fields=[
        "statut", "decision", "favorable_au_client", "resolu_avec_preuve",
        "resolu_par", "resolved_at",
    ])

    emettre_evenement(
        type_evenement="reclamation_resolue",
        dossiers_concernes=list(reclamation.dossiers_concernes.all()),
        acteur_origine=resolu_par,
        objet_source=reclamation,
        donnees={
            "favorable_au_client": favorable_au_client_final,
            "resolu_avec_preuve": a_des_preuves,
        },
    )
    return reclamation
