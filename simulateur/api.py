"""
API endpoints du module simulateur - FAGNI Platform (FOS-213 v1.3).
Tous AllowAny : visiteurs anonymes par construction (avant tout compte).
"""
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from configuration.services import obtenir_valeur_courante, ParametreInconnu
from .models import Simulation
from .strategies import SimulationEngine, OffreNonDisponible
from .services import generer_sim_id, zone_disponible, verifier_offre_active, reserver, ConflitReservation
from .throttling import EstimerThrottle, ReserverThrottle
from .etats import transitionner, STATUTS_EXPIRABLES
from abonnements.services import PrixAbonnementNonConfigure


def _delai_collecte(zone_code):
    try:
        return obtenir_valeur_courante(f"simulateur_zone_{zone_code}_delai_estime")
    except ParametreInconnu:
        return "Delai a confirmer par OPS"


def _nb_partenaires(zone_code):
    try:
        return int(obtenir_valeur_courante(f"simulateur_zone_{zone_code}_nb_partenaires"))
    except (ParametreInconnu, ValueError):
        return 0


@api_view(['POST'])
@throttle_classes([EstimerThrottle])
def api_estimer(request):
    """
    POST /api/simulateur/estimer
    Payload : {"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"}
    """
    service = request.data.get("service", "pressing")
    zone_code = request.data.get("zone_code", "").strip()
    taille_sac = request.data.get("taille_sac", "").strip()
    pack = request.data.get("pack", "").strip()

    if not zone_code or not taille_sac or not pack:
        return Response({"error": "zone_code, taille_sac, pack requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        strategy = SimulationEngine.get_strategy(service)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Zone verifiee AVANT tout calcul de prix (FOS-213 v1.3 : capacite/disponibilite
    # avant prix, jamais l'inverse)
    if not zone_disponible(zone_code):
        return Response({
            "disponible": False,
            "message": "FAGNI n'est pas encore disponible dans cette zone.",
        }, status=status.HTTP_200_OK)

    try:
        verifier_offre_active(service, pack)
    except OffreNonDisponible:
        return Response({"error": "Cette offre n'est pas actuellement proposee."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    try:
        resultat = strategy.estimer(taille_sac=taille_sac, pack=pack)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except PrixAbonnementNonConfigure:
        return Response({"error": "Cette offre n'est pas encore disponible, reessayez plus tard."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    simulation = Simulation.objects.create(
        sim_id=generer_sim_id(),
        service=service,
        strategy_version=resultat["strategy_version"],
        zone_code=zone_code,
        taille_sac=taille_sac,
        pack=pack,
        prix_calcule=resultat["prix"],
        version_parametre_prix=resultat["version_parametre"],
        nb_partenaires_disponibles=_nb_partenaires(zone_code),
    )
    transitionner(simulation, "resultat_affiche")

    return Response({
        "sim_id": simulation.sim_id,
        "resume_token": simulation.resume_token,
        "disponible": True,
        "delai_premiere_collecte": _delai_collecte(zone_code),
        "nb_partenaires_disponibles": simulation.nb_partenaires_disponibles,
        "prix": float(simulation.prix_calcule),
        "prix_quotidien_equivalent": round(float(simulation.prix_calcule) / 7, 0),
        "offre_lancement": True,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def api_reprendre(request, resume_token):
    """
    GET /api/simulateur/reprendre/{resume_token}
    v1.3 : parametre d'URL = resume_token, jamais sim_id.
    """
    try:
        simulation = Simulation.objects.get(resume_token=resume_token)
    except Simulation.DoesNotExist:
        return Response({"error": "Simulation introuvable."}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    from datetime import timedelta

    expire = (
        simulation.statut in STATUTS_EXPIRABLES
        and simulation.created_at < timezone.now() - timedelta(days=7)
    )

    if not expire:
        return Response({
            "sim_id": simulation.sim_id,
            "resume_token": simulation.resume_token,
            "disponible": True,
            "delai_premiere_collecte": _delai_collecte(simulation.zone_code),
            "nb_partenaires_disponibles": simulation.nb_partenaires_disponibles,
            "prix": float(simulation.prix_calcule),
            "prix_quotidien_equivalent": round(float(simulation.prix_calcule) / 7, 0),
            "offre_lancement": True,
            "prix_recalcule": False,
        }, status=status.HTTP_200_OK)

    # Expiree : nouvelle Simulation creee, l'originale JAMAIS modifiee au-dela
    # de son passage a "expiree" (FOS-213 v1.3 point 4 - 200, pas 410)
    transitionner(simulation, "expiree")

    try:
        strategy = SimulationEngine.get_strategy(simulation.service)
        resultat = strategy.estimer(taille_sac=simulation.taille_sac, pack=simulation.pack)
    except (ValueError, PrixAbonnementNonConfigure):
        return Response({"error": "Cette offre n'est plus disponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    nouvelle = Simulation.objects.create(
        sim_id=generer_sim_id(),
        service=simulation.service,
        strategy_version=resultat["strategy_version"],
        zone_code=simulation.zone_code,
        taille_sac=simulation.taille_sac,
        pack=simulation.pack,
        prix_calcule=resultat["prix"],
        version_parametre_prix=resultat["version_parametre"],
        nb_partenaires_disponibles=_nb_partenaires(simulation.zone_code),
        simulation_precedente=simulation,
    )
    transitionner(nouvelle, "resultat_affiche")

    return Response({
        "prix_recalcule": True,
        "ancienne_reference": simulation.sim_id,
        "sim_id": nouvelle.sim_id,
        "resume_token": nouvelle.resume_token,
        "prix": float(nouvelle.prix_calcule),
        "message": "Votre precedente estimation avait expire. Elle a ete actualisee selon les tarifs en vigueur.",
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@throttle_classes([ReserverThrottle])
def api_reserver(request):
    """
    POST /api/simulateur/reserver
    Payload : {"resume_token": "...", "telephone": "...", "nom": "..."}
    v1.3 : resume_token, jamais sim_id.
    """
    resume_token = request.data.get("resume_token", "").strip()
    telephone = request.data.get("telephone", "").strip()
    nom = request.data.get("nom", "").strip()

    if not resume_token or not telephone or not nom:
        return Response({"error": "resume_token, telephone, nom requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        resultat = reserver(resume_token, telephone, nom)
    except Simulation.DoesNotExist:
        return Response({"error": "Simulation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    except ConflitReservation as e:
        return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

    return Response(resultat, status=status.HTTP_200_OK)


@api_view(['POST'])
def api_reserver(request):
    """
    POST /api/simulateur/reserver
    Payload : {"resume_token": "...", "telephone": "...", "nom": "..."}
    v1.3 : resume_token, jamais sim_id.
    """
    resume_token = request.data.get("resume_token", "").strip()
    telephone = request.data.get("telephone", "").strip()
    nom = request.data.get("nom", "").strip()

    if not resume_token or not telephone or not nom:
        return Response({"error": "resume_token, telephone, nom requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        resultat = reserver(resume_token, telephone, nom)
    except Simulation.DoesNotExist:
        return Response({"error": "Simulation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    except ConflitReservation as e:
        return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

    return Response(resultat, status=status.HTTP_200_OK)


# Allowlist stricte (FOS-213 v1.3 section 11) : seuls ces types sont
# acceptes, coherent avec EvenementSimulation.TYPE_EVENEMENT_CHOICES.
_TYPES_EVENEMENT_AUTORISES = {
    "arrivee", "etape_1", "etape_2", "resultat_affiche",
    "whatsapp_ouvert", "reservation", "commande_creee",
}
_CLES_DONNEES_INTERDITES = {"telephone", "nom", "resume_token"}
_TAILLE_MAX_DONNEES = 1024  # octets, JSON serialise


@api_view(['POST'])
def api_evenement(request):
    """
    POST /api/simulateur/evenement
    Payload : {"resume_token": "...", "type_evenement": "...", "donnees": {}}
    Fire-and-forget cote frontend - ne bloque jamais le parcours si
    l'appel echoue. Allowlist stricte + exclusion des donnees
    personnelles de la telemetrie (FOS-213 v1.3 section 11).
    """
    import json
    from .models import Simulation, EvenementSimulation

    resume_token = request.data.get("resume_token", "").strip()
    type_evenement = request.data.get("type_evenement", "").strip()
    donnees = request.data.get("donnees", {})

    if type_evenement not in _TYPES_EVENEMENT_AUTORISES:
        return Response(status=status.HTTP_204_NO_CONTENT)  # echec silencieux, jamais bloquant

    if not isinstance(donnees, dict):
        donnees = {}

    # Exclusion stricte des donnees personnelles - meme par erreur de dev cote frontend
    donnees_filtrees = {k: v for k, v in donnees.items() if k not in _CLES_DONNEES_INTERDITES}

    try:
        if len(json.dumps(donnees_filtrees)) > _TAILLE_MAX_DONNEES:
            donnees_filtrees = {}
    except (TypeError, ValueError):
        donnees_filtrees = {}

    try:
        simulation = Simulation.objects.get(resume_token=resume_token)
    except Simulation.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)  # jamais reveler si un token existe

    EvenementSimulation.objects.create(
        simulation=simulation, type_evenement=type_evenement, donnees=donnees_filtrees,
    )
    return Response(status=status.HTTP_201_CREATED)


@api_view(['GET'])
def api_mon_abonnement(request):
    """
    GET /api/simulateur/mon-abonnement?telephone=...
    Retourne le statut de l'abonnement le plus recent pour ce numero -
    permet au client (app V1) de voir son engagement, invisible jusqu'ici
    (aucun ecran cote V1 ne montrait cette info, decouvert le 19 juillet).
    """
    from dossiers.services import normaliser_telephone_ci
    from dossiers.models import Dossier
    from abonnements.models import Abonnement

    telephone = request.GET.get('telephone', '').strip()
    if not telephone:
        return Response({"error": "telephone requis"}, status=status.HTTP_400_BAD_REQUEST)

    telephone_norm = normaliser_telephone_ci(telephone)

    try:
        dossier = Dossier.objects.get(type_acteur="client", telephone=telephone_norm)
    except Dossier.DoesNotExist:
        return Response({"abonnement": None}, status=status.HTTP_200_OK)

    abonnement = Abonnement.objects.filter(dossier_client=dossier).order_by("-created_at").first()
    if not abonnement:
        return Response({"abonnement": None}, status=status.HTTP_200_OK)

    return Response({
        "abonnement": {
            "pack": abonnement.get_pack_display(),
            "taille_sac": abonnement.get_taille_sac_display(),
            "statut": abonnement.get_statut_display(),
            "cree_le": abonnement.created_at.strftime("%d/%m/%Y"),
        }
    }, status=status.HTTP_200_OK)
