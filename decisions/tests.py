"""
Tests unitaires du module decisions - FAGNI Platform (Lot 1, Sprint 10)
Le test le plus important : une regle marquee toujours_humaine=True doit
retourner 'humaine' MEME QUAND les trois conditions d'automatisation sont
toutes reunies - la garantie la plus stricte du BOS chapitre 7.2.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from .models import ReglaDecision, Decision
from .services import evaluer_niveau_decision, enregistrer_decision, DecideurManquant


class EvaluationConditionsAutomatisationTests(TestCase):
    """Verifie la logique standard des trois conditions (BOS chapitre 12.3)."""

    def setUp(self):
        self.regle = ReglaDecision.objects.create(
            code="ecart_quantite_mineur", toujours_humaine=False,
        )

    def test_trois_conditions_reunies_donne_automatique(self):
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=True, preuve_disponible=True, reversible=True,
        )
        self.assertEqual(niveau, "automatique")

    def test_regle_inconnue_empeche_automatique(self):
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=False, preuve_disponible=True, reversible=True,
        )
        self.assertEqual(niveau, "assistee")

    def test_preuve_absente_empeche_automatique(self):
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=True, preuve_disponible=False, reversible=True,
        )
        self.assertEqual(niveau, "assistee")

    def test_erreur_irreversible_empeche_automatique(self):
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=True, preuve_disponible=True, reversible=False,
        )
        self.assertEqual(niveau, "assistee")


class ToujoursHumaineTests(TestCase):
    """
    Le test le plus strict de ce Sprint : verifie que toujours_humaine
    (BOS chapitre 7.2) l'emporte INCONDITIONNELLEMENT, meme quand les
    trois conditions d'automatisation sont parfaitement reunies.
    """
    def setUp(self):
        self.regle = ReglaDecision.objects.create(
            code="exclusion_dossier", toujours_humaine=True,
        )

    def test_toujours_humaine_meme_avec_toutes_conditions_reunies(self):
        """
        Cas central : meme avec regle_connue=True, preuve_disponible=True,
        reversible=True (les trois conditions d'automatisation parfaitement
        reunies), le resultat doit rester 'humaine' - jamais 'automatique'.
        """
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=True, preuve_disponible=True, reversible=True,
        )
        self.assertEqual(niveau, "humaine")

    def test_toujours_humaine_avec_conditions_absentes_aussi(self):
        niveau = evaluer_niveau_decision(
            self.regle, regle_connue=False, preuve_disponible=False, reversible=False,
        )
        self.assertEqual(niveau, "humaine")


class EnregistrementDecisionTests(TestCase):
    def setUp(self):
        ReglaDecision.objects.create(code="exclusion_dossier", toujours_humaine=True)
        ReglaDecision.objects.create(code="ecart_mineur", toujours_humaine=False)
        self.ceo = ouvrir_dossier("ops", "CEO", "0700000060")

    def test_decision_humaine_sans_decideur_refusee(self):
        with self.assertRaises(DecideurManquant):
            enregistrer_decision("exclusion_dossier", "humaine", decideur=None)

    def test_decision_humaine_avec_decideur_enregistree(self):
        decision = enregistrer_decision(
            "exclusion_dossier", "humaine", decideur=self.ceo,
            justification="Fraude averee, preuves multiples",
        )
        self.assertEqual(decision.decideur, self.ceo)
        self.assertEqual(decision.niveau_applique, "humaine")

    def test_decision_automatique_sans_decideur_autorisee(self):
        """Une decision automatique n'exige jamais de decideur identifie."""
        decision = enregistrer_decision("ecart_mineur", "automatique", decideur=None)
        self.assertIsNone(decision.decideur)
