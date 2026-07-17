"""
Endpoint d'administration pour initialiser la base (développement/démo).
Sécurisé avec une clé secrète dans SEED_SECRET_KEY (env).
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from dossiers.models import Dossier
from accounts.models import Compte


@api_view(['POST'])
def api_seed_test_comptes(request):
    """
    POST /api/admin/seed?key=<SEED_SECRET_KEY>
    Crée les Comptes de test. Idempotent.
    """
    secret_key = request.GET.get("key", "")
    # Fallback pour développement si la var d'env n'est pas définie
    expected_key = getattr(settings, "SEED_SECRET_KEY", "fagni_seed_dev_2025")
    
    if secret_key != expected_key:
        return Response(
            {"error": "Clé secrète invalide ou absente"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Évite les doublons
    if Dossier.objects.filter(email="admin@fagni.test").exists():
        return Response(
            {"message": "Comptes de test existent déjà"},
            status=status.HTTP_200_OK
        )
    
    try:
        # Admin OPS
        dossier_admin = Dossier.objects.create(
            type_acteur="ops",
            nom="Admin OPS",
            telephone="225 01 42 29 99 49",
            email="admin@fagni.test",
        )
        compte_admin = Compte.objects.create(
            dossier=dossier_admin,
            role="administrateur",
            actif=True,
        )
        compte_admin.definir_mot_de_passe("fagni2025")
        
        # Driver test
        dossier_driver = Dossier.objects.create(
            type_acteur="livreur",
            nom="Youande Bonao",
            telephone="225 01 23 45 67",
            email="driver@fagni.test",
        )
        compte_driver = Compte.objects.create(
            dossier=dossier_driver,
            role="membre",
            actif=True,
        )
        compte_driver.definir_mot_de_passe("driver2025")
        
        return Response({
            "message": "Seed complet",
            "comptes": [
                {"email": "admin@fagni.test", "role": "administrateur"},
                {"email": "driver@fagni.test", "role": "membre"},
            ]
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
