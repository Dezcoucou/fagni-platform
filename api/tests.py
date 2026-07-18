"""
Tests des endpoints API (Lot 3, suite Sprint 19).
Premiere couverture de test pour les endpoints REST du dossier api/ -
jusqu'ici jamais testes directement, seulement les services sous-jacents.
"""
from django.test import TestCase
from django.urls import reverse
from accounts.jwt_utils import JWTHandler
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from orchestrateur.services import orchestrer_mission
from workflows.services import creer_workflow


class ApiMissionWorkflowTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963513")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404888")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage_api_test", "quantite": 1, "prix_unitaire": 500}],
        )
        creer_workflow(
            "pressing_api_test", "lavage_api_test",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "mission_creee"}, {"type_evenement": "cloture"}],
        )
        self.mission = orchestrer_mission(
            "collecte", self.commande, "lavage_api_test", acteur_assigne=self.livreur,
        )
        self.token = JWTHandler.encode_access_token(compte_id=1, email="ops@fagni.test", role="administrateur")

    def _url(self, mission_id):
        return f"/api/ops/missions/{mission_id}/workflow"

    def test_sans_token_refuse(self):
        response = self.client.get(self._url(self.mission.id))
        self.assertEqual(response.status_code, 401)

    def test_role_non_autorise_refuse(self):
        token_client = JWTHandler.encode_access_token(compte_id=2, email="client@fagni.test", role="membre")
        response = self.client.get(
            self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {token_client}",
        )
        self.assertEqual(response.status_code, 403)

    def test_mission_inexistante_404(self):
        response = self.client.get(
            self._url(999999), HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_etat_execution_retourne_les_etapes(self):
        response = self.client.get(
            self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["workflow"], "pressing_api_test")
        self.assertFalse(data["termine"])
        self.assertEqual(data["etape_courante"], "mission_creee")
        self.assertEqual(data["prochaine_etape"], "cloture")
        self.assertEqual(len(data["etapes"]), 3)
