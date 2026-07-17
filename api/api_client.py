"""
API endpoints pour les Clients (Lot 1, Sprint 12).
GET /api/client/orders - Commandes du client
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_auth


@api_view(['GET'])
@require_auth(token_type="access")
def api_client_orders(request):
    """GET /api/client/orders - Commandes du client connecté"""
    return Response({
        "client_id": request.compte_id,
        "email": request.email,
        "total_orders": 0,
        "pending_orders": [],
        "completed_orders": [],
        "total_spent": 0,
    }, status=status.HTTP_200_OK)
