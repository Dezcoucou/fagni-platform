"""
Tests d'authentification (Lot 1, Sprint 12)
"""
import pytest
from django.test import Client
from dossiers.models import Dossier
from accounts.models import Compte


@pytest.mark.django_db
class TestAuth:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Crée un Compte de test."""
        self.client = Client()
        
        dossier = Dossier.objects.create(
            type_acteur="ops",
            nom="Test Admin",
            email="test@fagni.local",
        )
        
        self.compte = Compte.objects.create(
            dossier=dossier,
            role="administrateur",
            actif=True,
        )
        self.compte.definir_mot_de_passe("password123")
    
    def test_login_success(self):
        """Login avec credentials valides."""
        response = self.client.post(
            "/api/auth/login",
            {"email": "test@fagni.local", "password": "password123"},
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["compte"]["email"] == "test@fagni.local"
    
    def test_login_invalid_password(self):
        """Login avec password faux."""
        response = self.client.post(
            "/api/auth/login",
            {"email": "test@fagni.local", "password": "wrongpass"},
            content_type="application/json"
        )
        assert response.status_code == 401
    
    def test_login_nonexistent_email(self):
        """Login avec email qui n'existe pas."""
        response = self.client.post(
            "/api/auth/login",
            {"email": "ghost@fagni.local", "password": "password123"},
            content_type="application/json"
        )
        assert response.status_code == 401
    
    def test_refresh_success(self):
        """Refresh token valide."""
        # D'abord login
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "test@fagni.local", "password": "password123"},
            content_type="application/json"
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Ensuite refresh
        response = self.client.post(
            "/api/auth/refresh",
            {"refresh_token": refresh_token},
            content_type="application/json"
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_logout_with_valid_token(self):
        """Logout avec un token valide."""
        # D'abord login
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "test@fagni.local", "password": "password123"},
            content_type="application/json"
        )
        access_token = login_response.json()["access_token"]
        
        # Ensuite logout
        response = self.client.post(
            "/api/auth/logout",
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        assert response.status_code == 200
        assert "Déconnexion" in response.json()["message"]
