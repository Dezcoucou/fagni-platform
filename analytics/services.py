"""
Services internes du module analytics - FAGNI Platform (Lot 1, Sprint 13)
Derive de FOS-211 v1.1 (section 9.3, exploitation des evenements) et de
l'Annexe C du BOS (indicateurs de sante).

Limite volontaire, appliquee strictement : ce module OBSERVE, il ne
decide et ne declenche jamais rien lui-meme. Aucune fonction ici ne
cree, ne modifie ni ne supprime le moindre enregistrement dans un autre
module - uniquement des lectures agregees.
"""
from django.db.models import Count
from evenements.models import Evenement
from decisions.models import Decision
from reclamations.models import Reclamation


def compter_evenements_par_type():
    """Repartition du nombre d'evenements par type - lecture seule."""
    return dict(
        Evenement.objects.values_list("type_evenement")
        .annotate(total=Count("id"))
        .values_list("type_evenement", "total")
    )


def repartition_decisions_par_niveau():
    """
    Proportion automatique/assistee/humaine (BOS chapitre 12, Annexe C
    du BOS). Retourne un dict vide si aucune Decision n'existe encore -
    jamais une erreur.
    """
    total = Decision.objects.count()
    if total == 0:
        return {}

    repartition = {}
    for niveau, _ in Decision.NIVEAU_CHOICES:
        count = Decision.objects.filter(niveau_applique=niveau).count()
        repartition[niveau] = round(count / total * 100, 1)
    return repartition


def taux_reclamations_favorables_client():
    """
    Verifie indirectement, en pratique et pas seulement en theorie, que
    le doute profite reellement au client (BOS chapitre 4.2) sur
    l'ensemble des reclamations deja resolues.
    """
    resolues = Reclamation.objects.filter(statut="resolue")
    total = resolues.count()
    if total == 0:
        return None

    favorables = resolues.filter(favorable_au_client=True).count()
    return round(favorables / total * 100, 1)
