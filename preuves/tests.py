"""
Tests unitaires du module preuves - FAGNI Platform (Lot 1, Sprint 5)
Reutilise directement les tests d'immutabilite du Sprint 2 (module
evenements), y compris la protection QuerySet - la meme faile ne doit
jamais reapparaitre non testee.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from missions.services import proposer_mission
from evenements.services import emettre_evenement
from .models import Preuve
from .services import capturer_preuve


class CaptureBase(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404886")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500}],
        )
        self.mission = proposer_mission("collecte", self.commande, self.livreur)
        self.evenement = emettre_evenement(
            type_evenement="collecte_terminee",
            dossiers_concernes=[self.client_dossier, self.livreur],
            acteur_origine=self.livreur,
            objet_source=self.mission,
        )


class CapturePreuveTests(CaptureBase):
    def test_capture_normale(self):
        """Une Preuve peut etre capturee, rattachee a une Mission et un Evenement."""
        preuve = capturer_preuve(
            "photo", self.mission, self.evenement, self.livreur,
            contenu_texte="Photo prise a la collecte",
        )
        self.assertIsNotNone(preuve.id)
        self.assertEqual(preuve.mission, self.mission)
        self.assertEqual(preuve.evenement, self.evenement)
        self.assertEqual(preuve.dossier_capturant, self.livreur)


class ImmutabilitePreuveTests(CaptureBase):
    def test_modification_instance_bloquee(self):
        preuve = capturer_preuve("photo", self.mission, self.evenement, self.livreur)
        preuve.contenu_texte = "Modification tentee"
        with self.assertRaises(ValueError):
            preuve.save()

    def test_suppression_instance_bloquee(self):
        preuve = capturer_preuve("photo", self.mission, self.evenement, self.livreur)
        with self.assertRaises(ValueError):
            preuve.delete()

    def test_suppression_masse_queryset_bloquee(self):
        """
        Regle apprise au Sprint 2 (module evenements), appliquee ici des
        la premiere version - pas decouverte a posteriori cette fois.
        """
        preuve = capturer_preuve("photo", self.mission, self.evenement, self.livreur)
        with self.assertRaises(ValueError):
            Preuve.objects.filter(id=preuve.id).delete()

        self.assertTrue(Preuve.objects.filter(id=preuve.id).exists())
