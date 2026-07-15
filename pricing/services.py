"""
Services internes du module pricing - FAGNI Platform (Lot 2, Sprint 15)

valider_et_appliquer_coupon() est le seul point d'entree legitime.
Verifie toutes les conditions avant application, puis modifie le prix
engage de la Commande via commandes.services.reviser_prix() - jamais
une modification directe du champ, toujours par le service officiel
du module commandes (BOS chapitre 4.1).
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from commandes.services import reviser_prix
from .models import Coupon, CouponUsage


class CouponInvalide(Exception):
    """Leve pour toute raison rendant un coupon inutilisable sur cette Commande."""
    pass


@transaction.atomic
def valider_et_appliquer_coupon(commande, code, dossier_client, est_premiere_commande):
    """
    Valide puis applique un Coupon a une Commande. Refuse explicitement
    si la Commande a deja un coupon applique (OneToOneField sur commande
    empeche structurellement le doublon, verifie ici avant meme d'essayer).
    """
    if hasattr(commande, "coupon_usage"):
        raise CouponInvalide(
            f"La Commande #{commande.id} a deja un coupon applique "
            f"({commande.coupon_usage.coupon.code}) - un seul coupon par commande."
        )

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        raise CouponInvalide(f"Le code coupon '{code}' n'existe pas.")

    if not coupon.actif:
        raise CouponInvalide(f"Le coupon '{code}' n'est plus actif.")

    if coupon.valide_jusqu_a and timezone.now() > coupon.valide_jusqu_a:
        raise CouponInvalide(f"Le coupon '{code}' a expire.")

    if coupon.usage_max is not None and coupon.usage_actuel >= coupon.usage_max:
        raise CouponInvalide(f"Le coupon '{code}' a atteint son nombre d'utilisations maximum.")

    if coupon.premiere_commande_uniquement and not est_premiere_commande:
        raise CouponInvalide(
            f"Le coupon '{code}' est reserve a la premiere commande du client."
        )

    montant_reduction = (commande.prix_engage * Decimal(str(coupon.pourcentage_reduction)) / 100).quantize(Decimal("1"))
    nouveau_prix = commande.prix_engage - montant_reduction

    CouponUsage.objects.create(
        coupon=coupon, dossier_client=dossier_client, commande=commande,
        montant_reduction=montant_reduction,
    )
    coupon.usage_actuel += 1
    coupon.save(update_fields=["usage_actuel"])

    # Une reduction est toujours une baisse - jamais besoin d'accord_client (BOS 4.1)
    reviser_prix(commande, nouveau_prix, accord_client=False)

    return montant_reduction


def calculer_repartition_articles(prix_articles, commission_pct):
    """
    Repartit le prix des articles entre le partenaire et FAGNI, selon
    le pourcentage de commission (typiquement lu depuis configuration).
    """
    commission_pct = Decimal(str(commission_pct))
    part_fagni = (prix_articles * commission_pct / 100).quantize(Decimal("1"))
    part_partenaire = prix_articles - part_fagni
    return {"part_partenaire": part_partenaire, "part_fagni": part_fagni}


def calculer_repartition_livraison(frais_livraison, part_livreur_pct):
    """Repartit les frais de livraison entre le livreur et FAGNI."""
    part_livreur_pct = Decimal(str(part_livreur_pct))
    part_livreur = (frais_livraison * part_livreur_pct / 100).quantize(Decimal("1"))
    part_fagni = frais_livraison - part_livreur
    return {"part_livreur": part_livreur, "part_fagni": part_fagni}
