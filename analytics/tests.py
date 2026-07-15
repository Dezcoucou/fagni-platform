"""
Tests unitaires du module analytics - FAGNI Platform (Lot 1, Sprint 13)
Le test le plus important de ce Sprint : verifie que le module observe
uniquement - aucune fonction ne doit jamais creer, modifier ou supprimer
un enregistrement dans un autre module.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from evenements.models import Evenement
from decisions.models import ReglaDecision, Decision
from decisions.services import enregistrer_decision
from reclamations.services import ouvrir_reclamation, resoudre_reclamation
from .services import (
    compter_evenements_par_type,
    repartition_decisions_par_niveau,
    taux_reclamations_favorables_client,
)


class ComptageEvenementsTests(TestCase):
    def test_comptage_par_type(self):
        d = ouvrir_dossier("client", "Rita", "0708963511")
        creer_commande(d, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}])
        creer_commande(d, [{"article": "Pantalon", "service": "lavage", "quantite": 1, "prix_unitaire": 400}])

        repartition = compter_evenements_par_type()
        self.assertEqual(repartition.get("commande_creee"), 2)

    def test_aucun_evenement_cree_par_lecture(self):
        """
        Limite centrale de ce Sprint : appeler cette fonction ne doit
        jamais creer d'Evenement - le module observe, il ne declenche
        jamais rien lui-meme (FOS-211 section 9.3).
        """
        d = ouvrir_dossier("client", "Test Observation", "0700000080")
        creer_commande(d, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}])

        nb_avant = Evenement.objects.count()
        compter_evenements_par_type()
        compter_evenements_par_type()  # appele deux fois, verification renforcee
        nb_apres = Evenement.objects.count()

        self.assertEqual(nb_avant, nb_apres)


class RepartitionDecisionsTests(TestCase):
    def test_repartition_correcte(self):
        ReglaDecision.objects.create(code="ecart_mineur", toujours_humaine=False)
        ReglaDecision.objects.create(code="exclusion", toujours_humaine=True)
        ceo = ouvrir_dossier("ops", "CEO", "0700000081")

        enregistrer_decision("ecart_mineur", "automatique")
        enregistrer_decision("ecart_mineur", "automatique")
        enregistrer_decision("exclusion", "humaine", decideur=ceo)

        repartition = repartition_decisions_par_niveau()
        self.assertAlmostEqual(repartition["automatique"], 66.7, delta=0.1)
        self.assertAlmostEqual(repartition["humaine"], 33.3, delta=0.1)

    def test_aucune_decision_retourne_dict_vide(self):
        """Aucune erreur, jamais - un dict vide en l'absence de donnees."""
        self.assertEqual(repartition_decisions_par_niveau(), {})

    def test_aucune_decision_creee_par_lecture(self):
        ReglaDecision.objects.create(code="test", toujours_humaine=False)
        nb_avant = Decision.objects.count()
        repartition_decisions_par_niveau()
        nb_apres = Decision.objects.count()
        self.assertEqual(nb_avant, nb_apres)


class TauxReclamationsFavorablesTests(TestCase):
    def test_taux_verifie_la_regle_bos_4_2_en_pratique(self):
        """
        Verifie indirectement, avec de vraies donnees, que la regle du
        BOS chapitre 4.2 (doute profite au client) se reflete dans les
        chiffres reels, pas seulement dans le code du module reclamations.
        """
        client = ouvrir_dossier("client", "Client Test", "0700000082")
        commande = creer_commande(
            client, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )

        r1 = ouvrir_reclamation(commande, [client], "Probleme 1")
        resoudre_reclamation(r1, decision="Resolu avec preuve", preuves=["preuve"], favorable_au_client=True)

        r2 = ouvrir_reclamation(commande, [client], "Probleme 2")
        resoudre_reclamation(r2, decision="Aucune preuve", preuves=None, favorable_au_client=False)

        # Les deux se retrouvent favorables : la seconde forcee par l'absence de preuve
        self.assertEqual(taux_reclamations_favorables_client(), 100.0)

    def test_aucune_reclamation_retourne_none(self):
        self.assertIsNone(taux_reclamations_favorables_client())
