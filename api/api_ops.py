"""
API endpoints pour les OPS (Lot 1, Sprint 12).
GET /api/ops/dashboard - Stats dashboard OPS
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_auth


@api_view(['GET'])
@require_auth(token_type="access")
def api_ops_dashboard(request):
    """GET /api/ops/dashboard - Stats globales pour OPS"""
    return Response({
        "ops_id": request.compte_id,
        "email": request.email,
        "total_drivers": 0,
        "total_partners": 0,
        "total_orders": 0,
        "daily_revenue": 0,
        "stats": {}
    }, status=status.HTTP_200_OK)
