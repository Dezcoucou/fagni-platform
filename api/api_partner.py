"""
API endpoints pour les Partners (Lot 1, Sprint 12).
GET /api/partner/orders - Commandes du partenaire (partner only)
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role


@api_view(['GET'])
@require_role("membre")
def api_partner_orders(request):
    """
    GET /api/partner/orders
    Commandes du partenaire connecté (partenaire seulement).
    Authorization: Bearer <access_token> requis.
    """
    return Response({
        "partenaire_id": request.compte_id,
        "email": request.email,
        "role": request.role,
        "total_orders": 0,
        "pending_orders": [],
        "completed_orders": [],
        "revenus_total": 0,
    }, status=status.HTTP_200_OK)
