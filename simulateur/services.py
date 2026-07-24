"""
Services internes du module simulateur - FAGNI Platform (FOS-213 v1.3).
"""
import secrets
from django.db import transaction
from configuration.services import obtenir_valeur_courante
from configuration.models import Parametre
from .strategies import OffreNonDisponible
from .etats import transitionner


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


class ConflitReservation(Exception):
    """
    Levee quand une reservation est tentee sur une Simulation deja
    reservee, avec des donnees DIFFERENTES du premier appel - un vrai
    conflit, distinct d'un simple rejeu reseau (FOS-213 v1.3 point 3).
    """
    pass


@transaction.atomic
def reserver(resume_token, telephone, nom):
    """
    Vraie idempotence : un rejeu du meme resume_token avec les memes
    donnees (telephone normalise + nom) retourne la reservation
    existante (already_reserved=True), jamais une erreur - essentiel en
    contexte mobile ou une reponse peut se perdre alors que la
    reservation a reussi cote serveur.

    select_for_update() empeche deux creations concurrentes du meme
    Abonnement en cas de double appel quasi-simultane (ex. double-tap
    reseau instable).
    """
    from django.db import transaction as django_transaction
    from dossiers.services import normaliser_telephone_ci, ouvrir_dossier, DossierDejaExistant
    from dossiers.models import Dossier
    from abonnements.services import creer_abonnement
    from .models import Simulation

    try:
        simulation = Simulation.objects.select_for_update().get(resume_token=resume_token)
    except Simulation.DoesNotExist:
        raise Simulation.DoesNotExist(f"Aucune simulation pour ce resume_token.")

    telephone_norm = normaliser_telephone_ci(telephone)
    nom_norm = " ".join((nom or "").strip().split())

    if simulation.statut in ("reservee", "commande_creee"):
        meme_telephone = normaliser_telephone_ci(simulation.telephone) == telephone_norm
        meme_nom = " ".join((simulation.nom or "").strip().split()) == nom_norm
        if meme_telephone and meme_nom:
            return {
                "already_reserved": True,
                "sim_id": simulation.sim_id,
                "status": simulation.statut,
            }
        raise ConflitReservation(
            "Cette simulation a deja ete reservee avec des informations differentes."
        )

    # premiere reservation reelle
    try:
        dossier = Dossier.objects.get(
            type_acteur="client", telephone=telephone_norm, statut="actif",
        )
    except Dossier.DoesNotExist:
        dossier = ouvrir_dossier("client", nom_norm, telephone_norm)

    abonnement = creer_abonnement(
        dossier, simulation.pack, simulation.taille_sac,
        jour_collecte=0, jour_livraison=3,  # valeurs par defaut MVP - ajustable par OPS ensuite
    )

    simulation.telephone = telephone_norm
    simulation.nom = nom_norm
    simulation.dossier = dossier
    simulation.abonnement = abonnement
    simulation.save(update_fields=["telephone", "nom", "dossier", "abonnement", "updated_at"])

    transitionner(simulation, "reservee")

    # Notification OPS via V1 (FCM deja fonctionnel) - fire-and-forget,
    # jamais bloquant. Exception consciente au principe "pas de pont
    # automatique V1/V2" (FOS-213 section 0), justifiee car non-critique :
    # un echec ici n'affecte jamais la reservation deja actee.
    _notifier_ops_v1(simulation, telephone_norm, nom_norm)

    return {
        "already_reserved": False,
        "sim_id": simulation.sim_id,
        "status": "reservee",
    }


def _notifier_ops_v1(simulation, telephone, nom):
    import os
    import requests

    try:
        requests.post(
            "https://dezcoucou80.pythonanywhere.com/api/simulateur/notify/",
            params={"key": os.getenv("SIMULATEUR_NOTIFY_KEY", "")},
            json={
                "sim_id": simulation.sim_id,
                "nom": nom,
                "telephone": telephone,
                "prix": float(simulation.prix_calcule),
            },
            timeout=5,
        )
    except Exception:
        pass  # fire-and-forget : jamais d'impact sur la reservation si V1 est indisponible/lent
