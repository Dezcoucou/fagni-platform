"""
API endpoints pour les OPS (Lot 1, Sprint 12).
GET /api/ops/dashboard - Stats dashboard OPS (admin only)
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role


@api_view(['GET'])
@require_role("administrateur", "superviseur")
def api_ops_dashboard(request):
    """
    GET /api/ops/dashboard
    Stats globales pour OPS (admin/superviseur seulement).
    Authorization: Bearer <access_token> requis.
    """
    return Response({
        "ops_id": request.compte_id,
        "email": request.email,
        "role": request.role,
        "total_drivers": 0,
        "total_partners": 0,
        "total_orders": 0,
        "daily_revenue": 0,
    }, status=status.HTTP_200_OK)
