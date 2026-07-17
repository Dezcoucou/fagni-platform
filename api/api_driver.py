"""
API endpoints pour les Drivers (Lot 1, Sprint 12).
GET /api/driver/missions - Missions du livreur (driver only)
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role


@api_view(['GET'])
@require_role("membre")
def api_driver_missions(request):
    """
    GET /api/driver/missions
    Missions du livreur connecté (livreur seulement).
    Authorization: Bearer <access_token> requis.
    """
    return Response({
        "livreur_id": request.compte_id,
        "email": request.email,
        "role": request.role,
        "total_missions": 0,
        "missions_en_cours": [],
        "missions_completees": [],
        "revenus_total": 0,
    }, status=status.HTTP_200_OK)
