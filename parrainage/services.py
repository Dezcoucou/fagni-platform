"""
Services internes du module parrainage - FAGNI Platform (Lot 2, Sprint 18)

enregistrer_parrainage() applique les deux garde-fous anti-fraude retenus
du pilote V1 : pas d'auto-parrainage, un seul parrainage par filleul
(garanti structurellement par le OneToOneField).
crediter_si_eligible() ne credite jamais avant le delai de 48h - et
reutilise l'idempotence deja eprouvee de paiements.services.
"""
from django.utils import timezone
from paiements.services import crediter_wallet
from .models import Parrainage


class ParrainageInvalide(Exception):
    """Leve pour toute raison rendant un parrainage invalide."""
    pass


def enregistrer_parrainage(parrain, filleul, commande_declenchante):
    """
    Enregistre un Parrainage. Refuse explicitement l'auto-parrainage -
    lecon retenue directement du pilote V1.
    """
    if parrain.id == filleul.id:
        raise ParrainageInvalide(
            "Un Dossier ne peut pas se parrainer lui-meme (anti-fraude, pilote V1)."
        )

    if hasattr(filleul, "parrainage_recu"):
        raise ParrainageInvalide(
            f"{filleul.nom} a deja ete parraine - un seul parrainage par filleul."
        )

    return Parrainage.objects.create(
        parrain=parrain, filleul=filleul, commande_declenchante=commande_declenchante,
    )


def crediter_si_eligible(parrainage):
    """
    Credite le Wallet du parrain UNIQUEMENT si le delai de 48h est
    ecoule - jamais avant, quelle que soit la pression a accelerer.
    Idempotent via la cle d'idempotence deja eprouvee au Sprint 7.
    """
    if parrainage.statut == "credite":
        return parrainage  # deja traite, idempotent

    if timezone.now() < parrainage.eligible_a_partir_de:
        return parrainage  # trop tot, on ne fait rien, jamais d'exception bloquante

    crediter_wallet(
        parrainage.parrain, parrainage.montant_credit,
        raison=f"Parrainage de {parrainage.filleul.nom}",
        idempotency_key=f"parrainage-{parrainage.id}",
    )
    parrainage.statut = "credite"
    parrainage.save(update_fields=["statut"])
    return parrainage
