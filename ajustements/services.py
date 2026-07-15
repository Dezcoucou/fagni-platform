"""
Services internes du module ajustements - FAGNI Platform (Lot 2, Sprint 16)

traiter_ecart_quantite() applique directement la regle BOS chapitre 4.1 :
un deficit se rembourse automatiquement (jamais besoin d'accord), un
excedent attend toujours une confirmation explicite avant tout paiement
supplementaire - jamais facture automatiquement.
"""
from django.db import transaction
from paiements.services import crediter_wallet
from .models import AjustementCommande


def traiter_ecart_quantite(ligne_commande, quantite_reelle):
    """
    Compare la quantite reelle constatee a la collecte avec la quantite
    declaree. Idempotent : si un ajustement existe deja pour cette
    ligne (OneToOneField), le renvoie sans en recreer un second.
    Retourne None si aucun ecart.
    """
    ajustement_existant = getattr(ligne_commande, "ajustement", None)
    if ajustement_existant:
        return ajustement_existant

    quantite_declaree = ligne_commande.quantite

    if quantite_reelle == quantite_declaree:
        return None

    if quantite_reelle < quantite_declaree:
        return _traiter_deficit(ligne_commande, quantite_declaree, quantite_reelle)
    return _traiter_excedent(ligne_commande, quantite_declaree, quantite_reelle)


@transaction.atomic
def _traiter_deficit(ligne_commande, quantite_declaree, quantite_reelle):
    """
    Deficit : rembourse automatiquement, jamais besoin d'accord du
    client - le doute profite au client (meme principe que BOS 4.2,
    applique ici a un ecart de quantite plutot qu'a une reclamation).
    """
    manquant = quantite_declaree - quantite_reelle
    montant = manquant * ligne_commande.prix_unitaire

    ajustement = AjustementCommande.objects.create(
        commande=ligne_commande.commande,
        ligne_commande=ligne_commande,
        type_ajustement="deficit",
        quantite_declaree=quantite_declaree,
        quantite_reelle=quantite_reelle,
        montant_ajustement=montant,
        statut="automatique_applique",
    )

    dossier_client = ligne_commande.commande.dossier_client
    crediter_wallet(
        dossier_client, montant,
        raison=f"Deficit constate - Ligne #{ligne_commande.id}",
        idempotency_key=f"ajustement-deficit-{ajustement.id}",
    )

    return ajustement


def _traiter_excedent(ligne_commande, quantite_declaree, quantite_reelle):
    """
    Excedent : jamais facture automatiquement - attend une confirmation
    explicite du client (BOS chapitre 4.1, une hausse n'est jamais
    imposee sans accord).
    """
    surplus = quantite_reelle - quantite_declaree
    montant = surplus * ligne_commande.prix_unitaire

    return AjustementCommande.objects.create(
        commande=ligne_commande.commande,
        ligne_commande=ligne_commande,
        type_ajustement="excedent",
        quantite_declaree=quantite_declaree,
        quantite_reelle=quantite_reelle,
        montant_ajustement=montant,
        statut="en_attente_complement",
    )


def confirmer_complement(ajustement, accepte):
    """
    Le client confirme ou refuse le complement d'un excedent - jamais
    facture avant cette confirmation explicite.
    """
    if ajustement.type_ajustement != "excedent":
        raise ValueError("Seul un ajustement de type excedent necessite une confirmation.")

    ajustement.statut = "complement_paye" if accepte else "complement_refuse"
    ajustement.save(update_fields=["statut"])
    return ajustement
