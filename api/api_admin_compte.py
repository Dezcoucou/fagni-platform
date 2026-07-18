"""
Endpoint d'administration pour creer un vrai Compte OPS avec mot de
passe correctement hache (contourne la faille de Django Admin qui
exposait mot_de_passe_hash en clair - corrigee dans accounts/admin.py).
Securise avec la meme cle secrete que api_seed.py (SEED_SECRET_KEY).
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from dossiers.models import Dossier
from accounts.models import Compte


@api_view(['POST'])
def api_admin_creer_compte_ops(request):
    """
    POST /api/admin/creer-compte-ops?key=<SEED_SECRET_KEY>
    Payload : {"nom": "...", "telephone": "...", "email": "...", "password": "...", "role": "administrateur"}
    Cree un Dossier type=ops + Compte avec mot de passe hache via
    definir_mot_de_passe() - jamais en clair.
    """
    secret_key = request.GET.get("key", "")
    expected_key = getattr(settings, "SEED_SECRET_KEY", "fagni_seed_dev_2025")
    if secret_key != expected_key:
        return Response({"error": "Cle secrete invalide ou absente"}, status=status.HTTP_403_FORBIDDEN)

    nom = request.data.get("nom", "").strip()
    telephone = request.data.get("telephone", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "").strip()
    role = request.data.get("role", "administrateur").strip()

    if not all([nom, email, password]):
        return Response({"error": "nom, email, password requis"}, status=status.HTTP_400_BAD_REQUEST)

    if role not in dict(Compte.ROLE_CHOICES):
        return Response({"error": f"role invalide, attendu: {list(dict(Compte.ROLE_CHOICES))}"}, status=status.HTTP_400_BAD_REQUEST)

    if Dossier.objects.filter(email=email).exists():
        return Response({"error": f"Un Dossier existe deja pour l'email '{email}'."}, status=status.HTTP_409_CONFLICT)

    dossier = Dossier.objects.create(
        type_acteur="ops", nom=nom, telephone=telephone, email=email,
    )
    compte = Compte.objects.create(dossier=dossier, role=role, actif=True)
    compte.definir_mot_de_passe(password)

    return Response({
        "message": "Compte OPS cree.",
        "dossier_id": dossier.id,
        "compte_id": compte.id,
        "email": email,
        "role": role,
    }, status=status.HTTP_201_CREATED)
