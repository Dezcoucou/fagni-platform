"""
Services internes du module simulateur - FAGNI Platform (FOS-213 v1.3).
"""
import secrets
from configuration.services import obtenir_valeur_courante
from configuration.models import Parametre
from .strategies import OffreNonDisponible


def generer_sim_id() -> str:
    """
    Format FG-{annee}-{5 chiffres} - identifiant d'AFFICHAGE/SUPPORT
    uniquement (FOS-213 v1.2, jamais un jeton d'acces). Unicite verifiee
    en base avant retour - meme rigueur anti-doublon que WithdrawalRequest,
    Abonnement.
    """
    from django.utils import timezone
    from .models import Simulation

    annee = timezone.now().year
    while True:
        candidat = f"FG-{annee}-{secrets.randbelow(100000):05d}"
        if not Simulation.objects.filter(sim_id=candidat).exists():
            return candidat


def zone_disponible(zone_code: str) -> bool:
    """
    Lit simulateur_zone_{zone_code}_active depuis configuration. Une zone
    absente de la configuration est traitee comme NON desservie - jamais
    supposee active par defaut (FOS-213 v1.3 section 1.4, meme principe
    que capacites_activees()).
    """
    try:
        valeur = obtenir_valeur_courante(f"simulateur_zone_{zone_code}_active")
        return valeur.lower() == "true"
    except Exception:
        return False


def verifier_offre_active(service: str, pack: str, taille_sac: str = None) -> None:
    """
    Leve OffreNonDisponible si l'offre est techniquement valide mais pas
    commercialement active - defense en profondeur, independante de ce
    que le frontend affiche ou masque (v1.2 UX ne propose que Confort,
    rien n'empechait un appel API direct sur Essentiel). Jamais suppose
    actif par defaut si la cle n'existe pas.
    """
    cle = f"simulateur_offre_{service}_{pack}_active"
    try:
        active = obtenir_valeur_courante(cle).lower() == "true"
    except Exception:
        active = False
    if not active:
        raise OffreNonDisponible(f"L'offre '{pack}' n'est pas actuellement proposee.")
