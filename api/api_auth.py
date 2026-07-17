"""
API endpoints d'authentification (Lot 1, Sprint 12).
POST /api/auth/login - email + password -> access_token + refresh_token
POST /api/auth/refresh - refresh_token -> nouveau access_token
POST /api/auth/logout - invalide (optionnel, tokens stateless)
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.http import require_http_methods
from accounts.models import Compte
from accounts.jwt_utils import JWTHandler, require_auth
import jwt


@api_view(['POST'])
@require_http_methods(['POST'])
def api_auth_login(request):
    """Login : email + password -> access_token + refresh_token"""
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "").strip()
    
    if not email or not password:
        return Response(
            {"error": "email et password requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        compte = Compte.objects.select_related("dossier").get(
            dossier__email=email, actif=True
        )
    except Compte.DoesNotExist:
        return Response(
            {"error": "Identifiants invalides"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not compte.verifier_mot_de_passe(password):
        return Response(
            {"error": "Identifiants invalides"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    access_token = JWTHandler.encode_access_token(
        compte.id, compte.dossier.email, compte.role
    )
    refresh_token = JWTHandler.encode_refresh_token(compte.id)
    
    return Response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "compte": {
            "id": compte.id,
            "email": compte.dossier.email,
            "nom": compte.dossier.nom,
            "role": compte.role,
            "type_acteur": compte.dossier.type_acteur,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@require_http_methods(['POST'])
def api_auth_refresh(request):
    """Refresh : refresh_token -> nouveau access_token"""
    refresh_token = request.data.get("refresh_token", "").strip()
    
    if not refresh_token:
        return Response(
            {"error": "refresh_token requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        payload = JWTHandler.decode_token(refresh_token, token_type="refresh")
        compte_id = payload.get("compte_id")
        compte = Compte.objects.select_related("dossier").get(
            id=compte_id, actif=True
        )
        
        access_token = JWTHandler.encode_access_token(
            compte.id, compte.dossier.email, compte.role
        )
        
        return Response({
            "access_token": access_token,
        }, status=status.HTTP_200_OK)
    
    except jwt.InvalidTokenError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Compte.DoesNotExist:
        return Response(
            {"error": "Compte introuvable ou inactif"},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@require_auth(token_type="access")
@require_http_methods(['POST'])
def api_auth_logout(request):
    """Logout (optionnel - tokens JWT sont stateless)"""
    return Response({
        "message": "Déconnexion réussie"
    }, status=status.HTTP_200_OK)
