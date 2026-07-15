"""
Tests unitaires du module missions - FAGNI Platform (Lot 1, Sprint 4)
Verifie en particulier une regle posee au Sprint 1 (dossiers.est_utilisable())
mais jamais encore testee en integration reelle avant ce module.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier, suspendre_dossier, exclure_dossier
from commandes.services import creer_commande
from evenements.models import Evenement
from .models import Mission
from .services import (
    proposer_mission,
    accepter_mission,
    refuser_mission,
    terminer_mission,
    ActeurNonUtilisable,
)


class PropositionMissionTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404886")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500}],
        )

    def test_proposition_normale(self):
        """Une Mission peut etre proposee a un acteur actif."""
        mission = proposer_mission("collecte", self.commande, self.livreur)
        self.assertEqual(mission.statut, "proposee")
        self.assertEqual(mission.acteur_assigne, self.livreur)

    def test_mission_emet_evenement(self):
        """Chaque Mission proposee emet un evenement mission_creee."""
        nb_avant = Evenement.objects.count()
        mission = proposer_mission("collecte", self.commande, self.livreur)
        self.assertEqual(Evenement.objects.count(), nb_avant + 1)

        evt = Evenement.objects.filter(type_evenement="mission_creee").latest("horodatage")
        self.assertEqual(evt.objet_source, mission)
        self.assertIn(self.livreur, evt.dossiers_concernes.all())
        self.assertIn(self.client_dossier, evt.dossiers_concernes.all())


class ActeurNonUtilisableTests(TestCase):
    """
    Verification reelle, pour la premiere fois, de la regle du Sprint 1 :
    un Dossier suspendu ou exclu ne peut jamais recevoir de nouvelle Mission
    (BOS chapitre 7.2).
    """
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Test", "0700000020")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Pantalon", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )

    def test_mission_refusee_si_livreur_suspendu(self):
        livreur = ouvrir_dossier("livreur", "Livreur Suspendu", "0700000021")
        suspendre_dossier(livreur, "Retards repetes")

        with self.assertRaises(ActeurNonUtilisable):
            proposer_mission("collecte", self.commande, livreur)

        # Aucune Mission ne doit avoir ete creee
        self.assertEqual(Mission.objects.filter(acteur_assigne=livreur).count(), 0)

    def test_mission_refusee_si_partenaire_exclu(self):
        partenaire = ouvrir_dossier("partenaire", "Partenaire Exclu", "0700000022")
        exclure_dossier(partenaire, "Fraude averee", valide_par="CEO")

        with self.assertRaises(ActeurNonUtilisable):
            proposer_mission("transport_intermediaire", self.commande, partenaire)


class CycleDeVieMissionTests(TestCase):
    def setUp(self):
        client_dossier = ouvrir_dossier("client", "Client Cycle", "0700000023")
        self.livreur = ouvrir_dossier("livreur", "Livreur Cycle", "0700000024")
        commande = creer_commande(
            client_dossier,
            [{"article": "Robe", "service": "lavage", "quantite": 1, "prix_unitaire": 800}],
        )
        self.mission = proposer_mission("collecte", commande, self.livreur)

    def test_acceptation(self):
        accepter_mission(self.mission)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "acceptee")

    def test_refus_reste_trace(self):
        """Une Mission refusee n'est jamais supprimee - elle reste dans l'historique."""
        refuser_mission(self.mission, raison="Zone trop eloignee")
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "refusee")
        self.assertTrue(Mission.objects.filter(id=self.mission.id).exists())

    def test_terminaison(self):
        accepter_mission(self.mission)
        terminer_mission(self.mission)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "terminee")
