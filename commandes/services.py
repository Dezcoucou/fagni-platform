"""
Services internes du module commandes - FAGNI Platform (Lot 1, Sprint 3)

creer_commande() est le seul point d'entree legitime pour creer une
Commande. Elle emet systematiquement un evenement "commande_creee" via
evenements.services - jamais une application externe ne cree cet
evenement elle-meme (FOS-211 section 4.3).
"""
from django.db import transaction
from evenements.services import emettre_evenement
from .models import Commande, LigneCommande


class RevisionPrixInterdite(Exception):
    """Leve quand une revision de prix a la hausse est tentee sans accord client."""
    pass


@transaction.atomic
def creer_commande(dossier_client, lignes_data, delai_annonce=""):
    """
    Cree une Commande avec ses lignes, calcule le prix engage comme la
    somme des lignes, et emet l'evenement commande_creee.

    lignes_data : liste de dict {article, service, niveau_service, quantite, prix_unitaire}
    """
    if not lignes_data:
        raise ValueError("Une Commande doit contenir au moins une ligne.")

    prix_total = sum(
        ligne["prix_unitaire"] * ligne.get("quantite", 1) for ligne in lignes_data
    )

    commande = Commande.objects.create(
        dossier_client=dossier_client,
        prix_engage=prix_total,
        delai_annonce=delai_annonce,
    )

    for ligne in lignes_data:
        LigneCommande.objects.create(
            commande=commande,
            article=ligne["article"],
            service=ligne["service"],
            niveau_service=ligne.get("niveau_service", "complet"),
            quantite=ligne.get("quantite", 1),
            prix_unitaire=ligne["prix_unitaire"],
        )

    emettre_evenement(
        type_evenement="commande_creee",
        dossiers_concernes=[dossier_client],
        acteur_origine=dossier_client,
        objet_source=commande,
        donnees={"prix_engage": str(commande.prix_engage), "nb_lignes": len(lignes_data)},
    )

    return commande


def reviser_prix(commande, nouveau_prix, accord_client=False):
    """
    BOS chapitre 4.1 : un prix engage ne peut jamais etre revise a la
    hausse sans accord explicite du client. Une baisse reste toujours
    possible sans condition (favorable au client, jamais un risque).
    """
    if nouveau_prix > commande.prix_engage and not accord_client:
        raise RevisionPrixInterdite(
            f"Le prix engage ({commande.prix_engage} FCFA) ne peut pas etre "
            f"revise a la hausse ({nouveau_prix} FCFA) sans accord explicite "
            f"du client (BOS chapitre 4.1)."
        )
    commande.prix_engage = nouveau_prix
    commande.save(update_fields=["prix_engage", "updated_at"])
    return commande


def changer_statut_ligne(ligne, nouveau_statut):
    """
    Chaque ligne progresse independamment - changer le statut d'une ligne
    n'affecte jamais les autres lignes de la meme Commande (decision
    ouverte tranchee : statut par ligne, pas global).
    """
    ligne.statut = nouveau_statut
    ligne.save(update_fields=["statut"])
    return ligne
