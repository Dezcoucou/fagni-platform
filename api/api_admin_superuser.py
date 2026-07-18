"""
Endpoint d'administration pour creer un superutilisateur Django (acces
a /admin), utile faute d'acces Shell sur le plan gratuit Render.
Securise avec la meme cle secrete que les autres endpoints admin.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth.models import User


@api_view(['POST'])
def api_admin_creer_superuser(request):
    """
    POST /api/admin/creer-superuser?key=<SEED_SECRET_KEY>
    Payload : {"username": "...", "email": "...", "password": "..."}
    """
    secret_key = request.GET.get("key", "")
    expected_key = getattr(settings, "SEED_SECRET_KEY", "fagni_seed_dev_2025")
    if secret_key != expected_key:
        return Response({"error": "Cle secrete invalide ou absente"}, status=status.HTTP_403_FORBIDDEN)

    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "").strip()

    if not all([username, password]):
        return Response({"error": "username et password requis"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": f"Un utilisateur '{username}' existe deja."}, status=status.HTTP_409_CONFLICT)

    User.objects.create_superuser(username=username, email=email, password=password)

    return Response({"message": "Superutilisateur cree.", "username": username}, status=status.HTTP_201_CREATED)
