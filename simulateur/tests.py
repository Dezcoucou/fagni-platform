"""
Tests unitaires du module simulateur - FAGNI Platform (FOS-213 v1.3).
"""
from django.test import TestCase
from configuration.services import definir_parametre
from .etats import transitionner, TransitionInterdite, TRANSITIONS_AUTORISEES, STATUTS_EXPIRABLES
from .strategies import SimulationEngine, PressingStrategy, OffreNonDisponible
from .services import generer_sim_id, zone_disponible, verifier_offre_active
from .models import Simulation
from abonnements.services import obtenir_prix_pack_avec_version


def _creer_simulation_test(**overrides):
    definir_parametre("abonnement_prix_confort_M", "10900")
    prix, version = obtenir_prix_pack_avec_version("confort", "M")
    defaults = dict(
        sim_id="FG-2026-00001",
        service="pressing",
        zone_code="RIVIERA_3",
        taille_sac="M",
        pack="confort",
        prix_calcule=prix,
        version_parametre_prix=version,
    )
    defaults.update(overrides)
    return Simulation.objects.create(**defaults)


class TransitionsEtatsTests(TestCase):
    def test_transition_valide_autorisee(self):
        sim = _creer_simulation_test(statut="en_cours")
        transitionner(sim, "resultat_affiche")
        sim.refresh_from_db()
        self.assertEqual(sim.statut, "resultat_affiche")

    def test_transition_invalide_refusee(self):
        sim = _creer_simulation_test(statut="commande_creee")
        with self.assertRaises(TransitionInterdite):
            transitionner(sim, "en_cours")

    def test_transition_depuis_etat_terminal_refusee(self):
        sim = _creer_simulation_test(statut="expiree")
        with self.assertRaises(TransitionInterdite):
            transitionner(sim, "reservee")

    def test_toutes_les_transitions_du_graphe_fonctionnent(self):
        """Verifie exhaustivement chaque transition declaree comme autorisee."""
        compteur = 0
        for statut_depart, statuts_arrivee in TRANSITIONS_AUTORISEES.items():
            for statut_arrivee in statuts_arrivee:
                compteur += 1
                sim = _creer_simulation_test(
                    sim_id=f"FG-2026-{compteur:05d}", statut=statut_depart,
                )
                transitionner(sim, statut_arrivee)
                sim.refresh_from_db()
                self.assertEqual(sim.statut, statut_arrivee)

    def test_statuts_expirables_ne_comprend_pas_reservee_ni_commande_creee(self):
        """FOS-213 v1.3 : une reservation deja realisee ne doit jamais expirer."""
        self.assertNotIn("reservee", STATUTS_EXPIRABLES)
        self.assertNotIn("commande_creee", STATUTS_EXPIRABLES)
        self.assertIn("resultat_affiche", STATUTS_EXPIRABLES)
        self.assertIn("envoyee_whatsapp", STATUTS_EXPIRABLES)


class SimulationEngineTests(TestCase):
    def test_service_connu_retourne_la_bonne_strategie(self):
        strategy = SimulationEngine.get_strategy("pressing")
        self.assertIsInstance(strategy, PressingStrategy)

    def test_service_inconnu_leve_erreur(self):
        with self.assertRaises(ValueError):
            SimulationEngine.get_strategy("service_inexistant")


class PressingStrategyTests(TestCase):
    def test_valider_params_refuse_taille_sac_invalide(self):
        strategy = PressingStrategy()
        with self.assertRaises(ValueError):
            strategy.valider_params(taille_sac="L", pack="confort")

    def test_valider_params_refuse_pack_invalide(self):
        strategy = PressingStrategy()
        with self.assertRaises(ValueError):
            strategy.valider_params(taille_sac="M", pack="premium")

    def test_estimer_retourne_prix_version_et_strategy_version(self):
        definir_parametre("abonnement_prix_confort_M", "10900")
        strategy = PressingStrategy()
        resultat = strategy.estimer(taille_sac="M", pack="confort")

        self.assertEqual(resultat["prix"], 10900.0)
        self.assertEqual(resultat["strategy_version"], "pressing-v1")
        self.assertIsNotNone(resultat["version_parametre"])


class GenererSimIdTests(TestCase):
    def test_format_correct(self):
        sim_id = generer_sim_id()
        self.assertRegex(sim_id, r"^FG-\d{4}-\d{5}$")

    def test_unicite_garantie(self):
        """Deux appels successifs ne doivent jamais produire le meme sim_id une fois utilise."""
        id1 = generer_sim_id()
        _creer_simulation_test(sim_id=id1)
        id2 = generer_sim_id()
        self.assertNotEqual(id1, id2)


class ZoneDisponibleTests(TestCase):
    def test_zone_non_configuree_retourne_false(self):
        """Jamais suppose active par defaut - meme principe que capacites_activees()."""
        self.assertFalse(zone_disponible("ZONE_INCONNUE"))

    def test_zone_configuree_active(self):
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        self.assertTrue(zone_disponible("RIVIERA_3"))

    def test_zone_configuree_inactive(self):
        definir_parametre("simulateur_zone_RIVIERA_4_active", "false")
        self.assertFalse(zone_disponible("RIVIERA_4"))


class VerifierOffreActiveTests(TestCase):
    def test_offre_non_configuree_refusee(self):
        """Jamais suppose actif par defaut."""
        with self.assertRaises(OffreNonDisponible):
            verifier_offre_active("pressing", "essentiel")

    def test_offre_configuree_active_ne_leve_rien(self):
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        verifier_offre_active("pressing", "confort")  # ne doit lever aucune exception

    def test_offre_explicitement_inactive_refusee(self):
        """
        FOS-213 v1.3 point 2 : meme si l'offre existe techniquement
        (Essentiel est un pack valide du modele Abonnement), un appel API
        direct doit etre bloque tant qu'elle n'est pas commercialement
        activee - defense independante de ce que le frontend expose.
        """
        definir_parametre("simulateur_offre_pressing_essentiel_active", "false")
        with self.assertRaises(OffreNonDisponible):
            verifier_offre_active("pressing", "essentiel")
