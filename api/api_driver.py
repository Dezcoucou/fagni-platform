"""
API endpoints pour les Drivers (Lot 1, Sprint 12).
GET /api/driver/missions - Missions du livreur connecté
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_auth


@api_view(['GET'])
@require_auth(token_type="access")
def api_driver_missions(request):
    """
    GET /api/driver/missions
    Retourne les missions du livreur connecté.
    Authorization: Bearer <access_token> requis.
    """
    try:
        # Pour le pilot, on retourne une structure simple
        # En production, on queryrait la DB via request.compte_id
        missions = {
            "livreur_id": request.compte_id,
            "email": request.email,
            "total_missions": 0,
            "missions_en_cours": [],
            "missions_completees": [],
            "revenus_total": 0,
        }
        
        return Response(missions, status=status.HTTP_200_OK)
    
    except Exception as err:
        return Response(
            {"error": str(err)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
