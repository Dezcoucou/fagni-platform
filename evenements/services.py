"""
Services internes du module evenements - FAGNI Platform (Lot 1, Sprint 3)

emettre_evenement() est le SEUL point d'entree legitime pour creer un
Evenement. Aucun autre module ne doit jamais appeler Evenement.objects.create()
directement - c'est cette fonction qui garantit que dossiers_concernes est
toujours renseigne (FOS-211 section 2.4), condition non verifiee par le
modele lui-meme.
"""
from .models import Evenement


def emettre_evenement(type_evenement, dossiers_concernes, acteur_origine=None,
                       objet_source=None, donnees=None):
    """
    Emet un evenement immuable.

    dossiers_concernes : liste non vide de Dossier - obligatoire (FOS-211
    section 2.4, un Evenement est toujours rattache a au moins un Dossier).
    """
    if not dossiers_concernes:
        raise ValueError(
            "Un Evenement doit toujours etre rattache a au moins un Dossier "
            "(FOS-211 section 2.4) - dossiers_concernes ne peut pas etre vide."
        )

    evenement = Evenement.objects.create(
        type_evenement=type_evenement,
        acteur_origine=acteur_origine,
        objet_source=objet_source,
        donnees=donnees or {},
    )
    evenement.dossiers_concernes.set(dossiers_concernes)
    return evenement
