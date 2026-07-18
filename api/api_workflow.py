"""
API endpoints pour l'etat d'execution des workflows (Lot 3, suite Sprint 19).
GET /api/ops/missions/<id>/workflow - Etat d'avancement d'une mission dans son workflow trace
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role
from missions.models import Mission
from orchestrateur.services import etat_execution


@api_view(['GET'])
@require_role("administrateur", "superviseur")
def api_mission_workflow(request, mission_id):
    """
    GET /api/ops/missions/<mission_id>/workflow
    Etat d'avancement derive (etapes realisees, prochaine etape, si termine)
    - jamais un etat stocke, toujours deduit des Evenement deja emis
    (orchestrateur.services.etat_execution).
    Authorization: Bearer <access_token> requis (OPS uniquement).
    """
    try:
        mission = Mission.objects.select_related("commande", "workflow").get(id=mission_id)
    except Mission.DoesNotExist:
        return Response({"detail": "Mission introuvable."}, status=status.HTTP_404_NOT_FOUND)

    etat = etat_execution(mission)
    if etat is None:
        return Response({
            "mission_id": mission.id,
            "workflow": None,
            "detail": "Aucun workflow trace sur cette mission.",
        }, status=status.HTTP_200_OK)

    return Response({
        "mission_id": mission.id,
        "workflow": etat["workflow"].nom,
        "termine": etat["termine"],
        "etape_courante": etat["etape_courante"].type_evenement if etat["etape_courante"] else None,
        "prochaine_etape": etat["prochaine_etape"].type_evenement if etat["prochaine_etape"] else None,
        "etapes": [
            {
                "ordre": item["etape"].ordre,
                "type_evenement": item["etape"].type_evenement,
                "obligatoire": item["etape"].obligatoire,
                "realisee": item["realisee"],
            }
            for item in etat["etapes"]
        ],
    }, status=status.HTTP_200_OK)
