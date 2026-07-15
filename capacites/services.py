"""
Services internes du module capacites - FAGNI Platform (Lot 1, Sprint 8)

est_compatible() est la fonction destinee a etre appelee par l'orchestrateur
(module missions) une fois activee - PAS ENCORE BRANCHEE, conformement a
la decision de gouvernance (FOS-212) de ne pas contraindre les Missions
tant qu'un seul service est officiellement propose.
"""
from .models import Capacite


def declarer_capacite(dossier, service, volume_disponible=0, niveau_confiance_service=50):
    """
    Cree ou met a jour la Capacite d'un Dossier sur un Service precis.
    Idempotent au sens metier - redeclarer met simplement a jour.
    """
    capacite, _ = Capacite.objects.update_or_create(
        dossier=dossier, service=service,
        defaults={
            "volume_disponible": volume_disponible,
            "niveau_confiance_service": niveau_confiance_service,
            "active": True,
        },
    )
    return capacite


def desactiver_capacite(dossier, service):
    """Desactive sans supprimer - garde l'historique du niveau de confiance atteint."""
    Capacite.objects.filter(dossier=dossier, service=service).update(active=False)


def est_compatible(dossier, service):
    """
    Regle centrale (FOS-210 section 11.2) : un Dossier sans Capacite
    declaree et active sur ce Service precis n'est jamais compatible -
    aucune compatibilite par defaut, jamais supposee.
    """
    return Capacite.objects.filter(
        dossier=dossier, service=service, active=True,
    ).exists()


def lister_partenaires_compatibles(service):
    """Retourne les Dossiers ayant une Capacite active sur ce Service."""
    return Capacite.objects.filter(
        service=service, active=True,
    ).select_related("dossier")
