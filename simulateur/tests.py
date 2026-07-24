"""
Tests unitaires du module simulateur - FAGNI Platform (FOS-213 v1.3).
"""
from django.test import TestCase
from unittest.mock import patch
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


class ApiEstimerTests(TestCase):
    def setUp(self):
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")

    def _payload(self, **overrides):
        base = {"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"}
        base.update(overrides)
        return base

    def test_estimation_reussie(self):
        response = self.client.post("/api/simulateur/estimer", data=self._payload(), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["disponible"])
        self.assertEqual(data["prix"], 10900.0)
        self.assertIn("sim_id", data)
        self.assertIn("resume_token", data)

    def test_zone_non_desservie_retourne_disponible_false(self):
        response = self.client.post(
            "/api/simulateur/estimer",
            data=self._payload(zone_code="ZONE_INEXISTANTE"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["disponible"])

    def test_offre_non_active_refusee(self):
        response = self.client.post(
            "/api/simulateur/estimer",
            data=self._payload(pack="essentiel"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)

    def test_champ_manquant_refuse(self):
        response = self.client.post(
            "/api/simulateur/estimer",
            data={"service": "pressing"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class ApiReprendreTests(TestCase):
    def setUp(self):
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")
        r = self.client.post(
            "/api/simulateur/estimer",
            data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
            content_type="application/json",
        )
        self.resume_token = r.json()["resume_token"]

    def test_reprise_non_expiree_retourne_meme_prix(self):
        response = self.client.get(f"/api/simulateur/reprendre/{self.resume_token}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["prix"], 10900.0)
        self.assertFalse(data["prix_recalcule"])

    def test_token_inconnu_404(self):
        response = self.client.get("/api/simulateur/reprendre/token-inexistant")
        self.assertEqual(response.status_code, 404)

    def test_reprise_expiree_cree_nouvelle_simulation(self):
        """FOS-213 v1.3 point 4 : l'originale n'est jamais modifiee au-dela de 'expiree'."""
        from .models import Simulation
        from django.utils import timezone
        from datetime import timedelta

        sim = Simulation.objects.get(resume_token=self.resume_token)
        Simulation.objects.filter(pk=sim.pk).update(created_at=timezone.now() - timedelta(days=8))

        response = self.client.get(f"/api/simulateur/reprendre/{self.resume_token}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["prix_recalcule"])
        self.assertEqual(data["ancienne_reference"], sim.sim_id)
        self.assertNotEqual(data["sim_id"], sim.sim_id)

        sim.refresh_from_db()
        self.assertEqual(sim.statut, "expiree")


@patch('simulateur.services._notifier_ops_v1')
class ApiReserverTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")
        r = self.client.post(
            "/api/simulateur/estimer",
            data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
            content_type="application/json",
        )
        self.resume_token = r.json()["resume_token"]

    def _payload(self, **overrides):
        base = {"resume_token": self.resume_token, "telephone": "0748643892", "nom": "Rita"}
        base.update(overrides)
        return base

    def test_premiere_reservation_reussie(self, mock_notify):
        response = self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["already_reserved"])
        self.assertEqual(data["status"], "reservee")

    def test_notification_ops_declenchee_a_la_premiere_reservation(self, mock_notify):
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        mock_notify.assert_called_once()

    def test_notification_non_redeclenchee_sur_rejeu(self, mock_notify):
        """Un rejeu identique ne doit jamais renvoyer une deuxieme alerte OPS."""
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        mock_notify.assert_called_once()

    def test_rejeu_identique_retourne_reservation_existante(self, mock_notify):
        """FOS-213 v1.3 point 3 - vraie idempotence, pas un 409 systematique."""
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        response = self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["already_reserved"])

    def test_rejeu_meme_telephone_format_different_reconnu_identique(self, mock_notify):
        """L'idempotence doit comparer des donnees NORMALISEES."""
        self.client.post("/api/simulateur/reserver", data=self._payload(telephone="0748643892"), content_type="application/json")
        response = self.client.post(
            "/api/simulateur/reserver",
            data=self._payload(telephone="+225 07 48 64 38 92"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["already_reserved"])

    def test_vrai_conflit_telephone_different_refuse(self, mock_notify):
        self.client.post("/api/simulateur/reserver", data=self._payload(telephone="0748643892"), content_type="application/json")
        response = self.client.post(
            "/api/simulateur/reserver",
            data=self._payload(telephone="0700000009"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)

    def test_resume_token_inconnu_404(self, mock_notify):
        response = self.client.post(
            "/api/simulateur/reserver",
            data=self._payload(resume_token="token-inexistant"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_reservation_cree_un_seul_abonnement(self, mock_notify):
        """Verifie qu'un seul Abonnement existe apres la reservation reelle."""
        from abonnements.models import Abonnement

        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        self.assertEqual(Abonnement.objects.count(), 1)

    def test_rejeu_ne_cree_pas_de_deuxieme_abonnement(self, mock_notify):
        """Critere de validation SE-06 : un abonnement maximum, meme sous rejeu."""
        from abonnements.models import Abonnement

        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")
        self.client.post("/api/simulateur/reserver", data=self._payload(), content_type="application/json")

        self.assertEqual(Abonnement.objects.count(), 1)


class ApiEvenementTests(TestCase):
    def setUp(self):
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")
        r = self.client.post(
            "/api/simulateur/estimer",
            data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
            content_type="application/json",
        )
        self.resume_token = r.json()["resume_token"]

    def test_evenement_type_autorise_enregistre(self):
        from .models import EvenementSimulation

        response = self.client.post(
            "/api/simulateur/evenement",
            data={"resume_token": self.resume_token, "type_evenement": "etape_1", "donnees": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EvenementSimulation.objects.count(), 1)

    def test_type_evenement_non_autorise_echec_silencieux(self):
        """FOS-213 v1.3 section 11 : allowlist stricte, jamais un 400 bloquant."""
        from .models import EvenementSimulation

        response = self.client.post(
            "/api/simulateur/evenement",
            data={"resume_token": self.resume_token, "type_evenement": "abandon", "donnees": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(EvenementSimulation.objects.count(), 0)

    def test_donnees_personnelles_filtrees(self):
        """FOS-213 v1.3 section 11 : telephone/nom/resume_token jamais dans la telemetrie."""
        from .models import EvenementSimulation

        self.client.post(
            "/api/simulateur/evenement",
            data={
                "resume_token": self.resume_token,
                "type_evenement": "reservation",
                "donnees": {"telephone": "0748643892", "nom": "Rita", "etape": "confirmee"},
            },
            content_type="application/json",
        )
        evt = EvenementSimulation.objects.get()
        self.assertNotIn("telephone", evt.donnees)
        self.assertNotIn("nom", evt.donnees)
        self.assertEqual(evt.donnees.get("etape"), "confirmee")

    def test_token_inconnu_echec_silencieux(self):
        """Ne revele jamais si un token existe ou non."""
        response = self.client.post(
            "/api/simulateur/evenement",
            data={"resume_token": "token-inexistant", "type_evenement": "etape_1", "donnees": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)


class ThrottlingTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # le cache de throttling DRF n'est pas reinitialise entre tests par defaut
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")

    def test_estimer_bloque_au_dela_du_seuil(self):
        payload = {"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"}
        for _ in range(20):
            r = self.client.post("/api/simulateur/estimer", data=payload, content_type="application/json")
            self.assertEqual(r.status_code, 200)

        r = self.client.post("/api/simulateur/estimer", data=payload, content_type="application/json")
        self.assertEqual(r.status_code, 429)


class ApiMonAbonnementTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")

    def test_telephone_sans_dossier_retourne_none(self):
        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000077")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["abonnement"])

    def test_dossier_sans_abonnement_retourne_none(self):
        from dossiers.services import ouvrir_dossier
        ouvrir_dossier("client", "Test", "0700000078")

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000078")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["abonnement"])

    def test_abonnement_existant_retourne_le_statut(self):
        with patch('simulateur.services._notifier_ops_v1'):
            r = self.client.post(
                "/api/simulateur/estimer",
                data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
                content_type="application/json",
            )
            resume_token = r.json()["resume_token"]
            self.client.post(
                "/api/simulateur/reserver",
                data={"resume_token": resume_token, "telephone": "0700000079", "nom": "Rita"},
                content_type="application/json",
            )

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000079")
        self.assertEqual(response.status_code, 200)
        data = response.json()["abonnement"]
        self.assertEqual(data["pack"], "Confort")
        self.assertEqual(data["statut"], "Actif")

    def test_telephone_format_different_reconnu(self):
        """Doit fonctionner peu importe le format saisi (normalisation)."""
        with patch('simulateur.services._notifier_ops_v1'):
            r = self.client.post(
                "/api/simulateur/estimer",
                data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
                content_type="application/json",
            )
            resume_token = r.json()["resume_token"]
            self.client.post(
                "/api/simulateur/reserver",
                data={"resume_token": resume_token, "telephone": "0700000080", "nom": "Rita"},
                content_type="application/json",
            )

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=+225 07 00 00 00 80")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["abonnement"])


class ApiMonAbonnementTests(TestCase):
    def setUp(self):
        definir_parametre("simulateur_zone_RIVIERA_3_active", "true")
        definir_parametre("simulateur_offre_pressing_confort_active", "true")
        definir_parametre("abonnement_prix_confort_M", "10900")

    def test_telephone_sans_dossier_retourne_none(self):
        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000077")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["abonnement"])

    def test_dossier_sans_abonnement_retourne_none(self):
        from dossiers.services import ouvrir_dossier
        ouvrir_dossier("client", "Test", "0700000078")

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000078")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["abonnement"])

    def test_abonnement_existant_retourne_le_statut(self):
        with patch('simulateur.services._notifier_ops_v1'):
            r = self.client.post(
                "/api/simulateur/estimer",
                data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
                content_type="application/json",
            )
            resume_token = r.json()["resume_token"]
            self.client.post(
                "/api/simulateur/reserver",
                data={"resume_token": resume_token, "telephone": "0700000079", "nom": "Rita"},
                content_type="application/json",
            )

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=0700000079")
        self.assertEqual(response.status_code, 200)
        data = response.json()["abonnement"]
        self.assertEqual(data["pack"], "Confort")
        self.assertEqual(data["statut"], "Actif")

    def test_telephone_format_different_reconnu(self):
        """Doit fonctionner peu importe le format saisi (normalisation)."""
        with patch('simulateur.services._notifier_ops_v1'):
            r = self.client.post(
                "/api/simulateur/estimer",
                data={"service": "pressing", "zone_code": "RIVIERA_3", "taille_sac": "M", "pack": "confort"},
                content_type="application/json",
            )
            resume_token = r.json()["resume_token"]
            self.client.post(
                "/api/simulateur/reserver",
                data={"resume_token": resume_token, "telephone": "0700000080", "nom": "Rita"},
                content_type="application/json",
            )

        response = self.client.get("/api/simulateur/mon-abonnement?telephone=+225 07 00 00 00 80")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["abonnement"])
