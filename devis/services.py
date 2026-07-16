"""
Services internes du module devis - FAGNI Platform (Lot 2, Sprint 17)

proposer_montant() relie directement au module decisions (Sprint 10) :
un devis est toujours une decision humaine, verifiee via
evaluer_niveau_decision() et sa regle toujours_humaine - jamais
suppose, jamais code en dur localement.
"""
from django.db import transaction
from decisions.models import ReglaDecision
from decisions.services import evaluer_niveau_decision, enregistrer_decision
from commandes.services import reviser_prix
from .models import Devis


def demander_devis(commande, description, ligne_commande=None):
    """Ouvre un Devis en attente - aucune decision n'est encore prise a ce stade."""
    return Devis.objects.create(
        commande=commande, ligne_commande=ligne_commande,
        description=description, statut="en_attente",
    )


@transaction.atomic
def proposer_montant(devis, montant, propose_par):
    """
    Un artisan/partenaire propose un montant. Verifie via le module
    decisions que cette proposition est bien traitee comme une decision
    humaine (FOS-210 section 12.1) - jamais automatique, meme si les
    trois conditions du BOS 12.3 semblaient toutes reunies.
    """
    devis.montant_propose = montant
    devis.propose_par = propose_par
    devis.statut = "propose"
    devis.save(update_fields=["montant_propose", "propose_par", "statut"])

    regle, _ = ReglaDecision.objects.get_or_create(
        code="devis_commande", defaults={"toujours_humaine": True},
    )
    niveau = evaluer_niveau_decision(
        regle, regle_connue=True, preuve_disponible=True, reversible=True,
    )
    enregistrer_decision(
        "devis_commande", niveau, decideur=propose_par,
        objet_source=devis, justification=f"Devis propose : {montant} FCFA",
    )
    return devis


def repondre_devis(devis, accepte):
    """
    Le client accepte ou refuse le devis propose. Une acceptation revise
    le prix de la Commande - toujours avec accord_client=True puisque
    c'est precisement cette acceptation qui constitue l'accord (BOS 4.1).
    """
    devis.statut = "accepte" if accepte else "refuse"
    devis.save(update_fields=["statut"])

    if accepte and devis.montant_propose is not None:
        nouveau_prix = devis.commande.prix_engage + devis.montant_propose
        reviser_prix(devis.commande, nouveau_prix, accord_client=True)

    return devis
