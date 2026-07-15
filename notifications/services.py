"""
Services internes du module notifications - FAGNI Platform (Lot 1, Sprint 14)

envoyer_notification() est idempotent grace a la contrainte du modele -
rejouer le meme envoi (meme destinataire, meme canal, meme evenement)
renvoie la notification existante, jamais un doublon.
"""
from django.db import IntegrityError, transaction
from .models import Notification


def envoyer_notification(dossier_destinataire, canal, evenement_declencheur, contenu):
    """
    Cree une Notification en_attente. Idempotent : si une notification
    identique (meme dossier, meme canal, meme evenement) existe deja,
    la renvoie sans en creer une seconde - lecon retenue directement
    du pilote V1 (tag anti-doublon ajoute a posteriori sur l'app driver).
    """
    existante = Notification.objects.filter(
        dossier_destinataire=dossier_destinataire,
        canal=canal,
        evenement_declencheur=evenement_declencheur,
    ).first()
    if existante:
        return existante

    try:
        with transaction.atomic():
            return Notification.objects.create(
                dossier_destinataire=dossier_destinataire,
                canal=canal,
                evenement_declencheur=evenement_declencheur,
                contenu=contenu,
            )
    except IntegrityError:
        # Course concurrente sur la meme combinaison - deja creee entre-temps
        return Notification.objects.get(
            dossier_destinataire=dossier_destinataire,
            canal=canal,
            evenement_declencheur=evenement_declencheur,
        )


def marquer_envoyee(notification):
    notification.statut_envoi = "envoyee"
    notification.save(update_fields=["statut_envoi"])
    return notification


def marquer_echouee(notification):
    notification.statut_envoi = "echouee"
    notification.save(update_fields=["statut_envoi"])
    return notification
