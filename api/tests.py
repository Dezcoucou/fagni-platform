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


class ApiDriverMissionWorkflowTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963514")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404889")
        self.livreur.email = "youande@fagni.test"
        self.livreur.save(update_fields=["email"])
        self.autre_livreur = ouvrir_dossier("livreur", "Ange", "0799404890")
        self.autre_livreur.email = "ange@fagni.test"
        self.autre_livreur.save(update_fields=["email"])
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage_driver_test", "quantite": 1, "prix_unitaire": 500}],
        )
        creer_workflow(
            "pressing_driver_test", "lavage_driver_test",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "mission_creee"}],
        )
        self.mission = orchestrer_mission(
            "collecte", self.commande, "lavage_driver_test", acteur_assigne=self.livreur,
        )
        self.token = JWTHandler.encode_access_token(compte_id=1, email="youande@fagni.test", role="membre")
        self.token_autre = JWTHandler.encode_access_token(compte_id=2, email="ange@fagni.test", role="membre")

    def _url(self, mission_id):
        return f"/api/driver/missions/{mission_id}/workflow"

    def test_livreur_voit_sa_propre_mission(self):
        response = self.client.get(self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"], "pressing_driver_test")

    def test_autre_livreur_ne_voit_pas_la_mission(self):
        response = self.client.get(self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {self.token_autre}")
        self.assertEqual(response.status_code, 404)


class ApiPartnerMissionWorkflowTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963515")
        self.partenaire = ouvrir_dossier("partenaire", "Atelier Test", "0700000200")
        self.partenaire.email = "atelier@fagni.test"
        self.partenaire.save(update_fields=["email"])
        self.autre_partenaire = ouvrir_dossier("partenaire", "Atelier Autre", "0700000201")
        self.autre_partenaire.email = "autre@fagni.test"
        self.autre_partenaire.save(update_fields=["email"])
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage_partner_test", "quantite": 1, "prix_unitaire": 500}],
        )
        creer_workflow(
            "pressing_partner_test", "lavage_partner_test",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "mission_creee"}],
        )
        self.mission = orchestrer_mission(
            "collecte", self.commande, "lavage_partner_test", acteur_assigne=self.partenaire,
        )
        self.token = JWTHandler.encode_access_token(compte_id=3, email="atelier@fagni.test", role="membre")
        self.token_autre = JWTHandler.encode_access_token(compte_id=4, email="autre@fagni.test", role="membre")

    def _url(self, mission_id):
        return f"/api/partner/missions/{mission_id}/workflow"

    def test_partenaire_voit_sa_propre_mission(self):
        response = self.client.get(self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"], "pressing_partner_test")

    def test_autre_partenaire_ne_voit_pas_la_mission(self):
        response = self.client.get(self._url(self.mission.id), HTTP_AUTHORIZATION=f"Bearer {self.token_autre}")
        self.assertEqual(response.status_code, 404)
