"""
API endpoints pour les Comptes (Lot 1, Sprint 12).
GET /api/compte/me - Infos du compte connecté
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.models import Compte
from accounts.jwt_utils import require_auth


@api_view(['GET'])
@require_auth(token_type="access")
def api_compte_me(request):
    """
    GET /api/compte/me
    Retourne les infos du compte connecté (vérifié via JWT).
    Authorization: Bearer <access_token> requis.
    """
    try:
        compte = Compte.objects.select_related("dossier").get(
            id=request.compte_id
        )
        
        return Response({
            "compte": {
                "id": compte.id,
                "email": compte.dossier.email,
                "nom": compte.dossier.nom,
                "telephone": compte.dossier.telephone,
                "role": compte.role,
                "type_acteur": compte.dossier.type_acteur,
                "actif": compte.actif,
                "created_at": compte.created_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
    
    except Compte.DoesNotExist:
        return Response(
            {"error": "Compte introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )
