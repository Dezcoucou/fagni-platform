"""
JWT utilities pour l'auth Compte (Lot 1, Sprint 12).
Stateless, sans Redis - tokens auto-expirés.
"""
import jwt
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


class JWTHandler:
    """
    Encode/decode JWT pour les Comptes.
    Access token : 1h
    Refresh token : 7 jours
    """
    ACCESS_LIFETIME = timedelta(hours=1)
    REFRESH_LIFETIME = timedelta(days=7)
    ALGORITHM = "HS256"
    
    @classmethod
    def encode_access_token(cls, compte_id, email, role):
        """Crée un access token (1h)."""
        payload = {
            "compte_id": compte_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.utcnow() + cls.ACCESS_LIFETIME,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def encode_refresh_token(cls, compte_id):
        """Crée un refresh token (7j)."""
        payload = {
            "compte_id": compte_id,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),  # Identifiant unique du token
            "exp": datetime.utcnow() + cls.REFRESH_LIFETIME,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def decode_token(cls, token, token_type="access"):
        """
        Decode un token.
        token_type: "access" ou "refresh"
        Retourne le payload ou leve jwt.InvalidTokenError
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[cls.ALGORITHM])
            if payload.get("type") != token_type:
                raise jwt.InvalidTokenError(f"Token type mismatch: expected {token_type}")
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token expire")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Token invalide: {str(e)}")


def require_auth(token_type="access"):
    """
    Decorator pour verifier le JWT dans Authorization: Bearer <token>
    Injecte 'compte_id', 'email', 'role' dans request.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return Response(
                    {"error": "Authorization header manquant ou invalide"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            token = auth_header[7:]  # Retire "Bearer "
            try:
                payload = JWTHandler.decode_token(token, token_type=token_type)
                request.compte_id = payload.get("compte_id")
                request.email = payload.get("email")
                request.role = payload.get("role")
                return view_func(request, *args, **kwargs)
            except jwt.InvalidTokenError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return wrapper
    return decorator


def require_role(*allowed_roles):
    """
    Decorator pour vérifier le rôle de l'utilisateur.
    Usage: @require_role("administrateur", "superviseur")
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # D'abord vérifier l'auth via require_auth
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return Response(
                    {"error": "Authorization header manquant"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            token = auth_header[7:]
            try:
                payload = JWTHandler.decode_token(token, token_type="access")
                request.compte_id = payload.get("compte_id")
                request.email = payload.get("email")
                request.role = payload.get("role")
                
                # Vérifier le rôle
                if request.role not in allowed_roles:
                    return Response(
                        {"error": f"Accès refusé. Rôle requis: {', '.join(allowed_roles)}"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                return view_func(request, *args, **kwargs)
            except jwt.InvalidTokenError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return wrapper
    return decorator
