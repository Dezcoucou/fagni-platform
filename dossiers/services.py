"""
Services internes du module dossiers - FAGNI Platform (Lot 1, Sprint 1)

Ces fonctions sont le seul point d'entree autorise pour creer ou modifier un
Dossier. Aucune vue API n'ecrit jamais directement sur le modele Dossier -
c'est la garantie que les regles du BOS (chapitre 4) sont toujours appliquees,
jamais contournees par un appel direct.
"""
from django.db import transaction
from .models import Dossier, EntreeHistoriqueConfiance


class DossierDejaExistant(Exception):
    """Leve quand une tentative d'ouverture de Dossier creerait un doublon actif."""
    pass


def normaliser_telephone_ci(telephone: str) -> str:
    """
    Normalise un numero ivoirien vers un format canonique unique - "0748643892",
    "+225 07 48 64 38 92", "225-0748643892" doivent tous produire la meme
    valeur normalisee. Necessaire pour toute comparaison d'identite (FOS-213
    v1.3 point 3 : idempotence de reservation), et pour eviter des doublons
    de Dossier bases sur un simple format different du meme numero.

    Format canonique retenu : 10 chiffres locaux, sans indicatif ni espace
    (ex: "0748643892") - coherent avec le format deja stocke sur Dossier.telephone
    dans le reste du codebase (aucun indicatif +225 observe dans les Dossier existants).
    """
    if not telephone:
        return ""

    chiffres = "".join(c for c in telephone if c.isdigit())

    # Retire l'indicatif pays si present (225XXXXXXXXXX -> XXXXXXXXXX,
    # en preservant le 0 initial local s'il existe deja apres l'indicatif)
    if chiffres.startswith("225") and len(chiffres) > 10:
        chiffres = chiffres[3:]

    # Garantit le 0 initial local (reforme numerotation CI 2021 - meme
    # convention deja appliquee cote V1, cf. fix du 0e6633e sur l'annuaire OPS)
    if chiffres and not chiffres.startswith("0"):
        chiffres = "0" + chiffres

    return chiffres


def ouvrir_dossier(type_acteur, nom, telephone=""):
    """
    Ouvre un nouveau Dossier. Refuse explicitement la creation d'un doublon
    actif pour le meme type d'acteur et le meme telephone - lecon retenue
    d'un incident reel corrige en session pilote V1 (doublon partenaire "L&O").
    """
    if telephone:
        doublon = Dossier.objects.filter(
            type_acteur=type_acteur, telephone=telephone, statut="actif",
        ).exists()
        if doublon:
            raise DossierDejaExistant(
                f"Un Dossier actif existe deja pour ce telephone ({telephone}) "
                f"et ce type d'acteur ({type_acteur})."
            )

    return Dossier.objects.create(
        type_acteur=type_acteur, nom=nom, telephone=telephone,
    )


@transaction.atomic
def modifier_niveau_confiance(dossier, nouveau_niveau, raison):
    """
    Seule fonction autorisee a modifier niveau_confiance. Cree systematiquement
    une EntreeHistoriqueConfiance - coherent avec l'immutabilite des Evenements
    (BOS chapitre 9) : le changement lui-meme reste trace, jamais silencieux.
    """
    ancien_niveau = dossier.niveau_confiance
    dossier.niveau_confiance = nouveau_niveau
    dossier.save(update_fields=["niveau_confiance", "updated_at"])

    EntreeHistoriqueConfiance.objects.create(
        dossier=dossier,
        ancien_niveau=ancien_niveau,
        nouveau_niveau=nouveau_niveau,
        raison=raison,
    )
    return dossier


def suspendre_dossier(dossier, raison):
    """
    Suspension - reversible, contrairement a l'exclusion. Peut a terme etre
    automatique selon des regles claires (BOS chapitre 12.3), contrairement
    a l'exclusion qui reste toujours une decision humaine (BOS chapitre 7.2).
    """
    dossier.statut = "suspendu"
    dossier.save(update_fields=["statut", "updated_at"])
    return dossier


def exclure_dossier(dossier, raison, valide_par):
    """
    Exclusion definitive - TOUJOURS une decision humaine explicite (BOS
    chapitre 7.2, FOS-210 section 2.5). Le parametre valide_par est
    obligatoire et non technique - il documente qui a pris la decision,
    jamais un simple seuil automatique.
    """
    if not valide_par:
        raise ValueError(
            "L'exclusion d'un Dossier exige une decision humaine identifiee "
            "(BOS chapitre 7.2) - valide_par ne peut pas etre vide."
        )
    dossier.statut = "exclu"
    dossier.save(update_fields=["statut", "updated_at"])
    return dossier
