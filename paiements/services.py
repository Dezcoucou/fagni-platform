"""
Services internes du module paiements - FAGNI Platform (Lot 1, Sprint 7)

crediter_wallet() et debiter_wallet() sont les seuls points d'entree
legitimes. L'idempotence est garantie par la contrainte unique sur
idempotency_key (modele) - un appel rejoue avec la meme cle renvoie
la transaction existante, jamais un double effet.
"""
from decimal import Decimal
from django.db import transaction, IntegrityError
from evenements.services import emettre_evenement
from .models import Wallet, TransactionWallet, Paiement


class SoldeInsuffisant(Exception):
    """Leve quand un debit depasserait le solde disponible."""
    pass


def obtenir_ou_creer_wallet(dossier):
    wallet, _ = Wallet.objects.get_or_create(dossier=dossier)
    return wallet


@transaction.atomic
def crediter_wallet(dossier, montant, raison, idempotency_key):
    """
    Credite le Wallet d'un Dossier. Idempotent : un second appel avec la
    meme idempotency_key renvoie la transaction existante sans recrediter.
    """
    wallet = obtenir_ou_creer_wallet(dossier)

    existante = TransactionWallet.objects.filter(idempotency_key=idempotency_key).first()
    if existante:
        return existante  # deja effectuee, aucun double effet

    try:
        with transaction.atomic():
            tx = TransactionWallet.objects.create(
                wallet=wallet, type_transaction="credit", montant=montant,
                raison=raison, idempotency_key=idempotency_key,
            )
            wallet.solde = wallet.solde + Decimal(str(montant))
            wallet.save(update_fields=["solde"])
    except IntegrityError:
        # Course concurrente sur la meme cle - la transaction existe deja
        return TransactionWallet.objects.get(idempotency_key=idempotency_key)

    return tx


@transaction.atomic
def debiter_wallet(dossier, montant, raison, idempotency_key):
    """
    Debite le Wallet d'un Dossier. Refuse si solde insuffisant. Meme
    garantie d'idempotence que crediter_wallet().
    """
    wallet = obtenir_ou_creer_wallet(dossier)

    existante = TransactionWallet.objects.filter(idempotency_key=idempotency_key).first()
    if existante:
        return existante

    if wallet.solde < Decimal(str(montant)):
        raise SoldeInsuffisant(
            f"Solde insuffisant pour {dossier.nom} : {wallet.solde} FCFA "
            f"disponible, {montant} FCFA demande."
        )

    try:
        with transaction.atomic():
            tx = TransactionWallet.objects.create(
                wallet=wallet, type_transaction="debit", montant=montant,
                raison=raison, idempotency_key=idempotency_key,
            )
            wallet.solde = wallet.solde - Decimal(str(montant))
            wallet.save(update_fields=["solde"])
    except IntegrityError:
        return TransactionWallet.objects.get(idempotency_key=idempotency_key)

    return tx


def confirmer_paiement(commande, montant, mode):
    """Cree un Paiement confirme et emet l'evenement paiement_confirme."""
    paiement = Paiement.objects.create(
        commande=commande, montant=montant, mode=mode, statut="confirme",
    )

    emettre_evenement(
        type_evenement="paiement_confirme",
        dossiers_concernes=[commande.dossier_client],
        acteur_origine=commande.dossier_client,
        objet_source=paiement,
        donnees={"montant": str(montant), "mode": mode},
    )
    return paiement
