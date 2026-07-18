"""
Tests unitaires du module orchestrateur - FAGNI Platform (Lot 3, Sprint 19)
Le test le plus important : verifie que le moteur de capacites, construit
au Sprint 8 et volontairement laisse inactif depuis, filtre reellement
les partenaires une fois active via configuration - jamais avant.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from missions.models import Mission
from capacites.services import declarer_capacite
from configuration.services import definir_parametre
from notifications.models import Notification
from workflows.services import creer_workflow
from .services import capacites_activees, suggerer_partenaires, orchestrer_mission, selectionner_workflow, etat_execution


class CapacitesActiveesTests(TestCase):
    def test_desactivees_par_defaut(self):
        """Aucun parametre defini - doit rester False, jamais suppose True."""
        self.assertFalse(capacites_activees())

    def test_activees_via_configuration(self):
        definir_parametre("orchestrateur_utiliser_capacites", "true")
        self.assertTrue(capacites_activees())

    def test_valeur_false_explicite(self):
        definir_parametre("orchestrateur_utiliser_capacites", "false")
        self.assertFalse(capacites_activees())


class SuggestionPartenairesTests(TestCase):
    """Coeur de ce Sprint : la premiere vraie connexion du moteur de capacites (Sprint 8)."""

    def setUp(self):
        self.atelier_lavage = ouvrir_dossier("partenaire", "Atelier Lavage", "0700000110")
        self.atelier_cordonnerie = ouvrir_dossier("partenaire", "Atelier Cordonnerie", "0700000111")
        declarer_capacite(self.atelier_lavage, "lavage")
        declarer_capacite(self.atelier_cordonnerie, "cordonnerie")

    def test_sans_capacites_retourne_tous_les_partenaires(self):
        """Capacites desactivees - comportement V1 : aucun filtrage."""
        suggestions = suggerer_partenaires("lavage")
        self.assertIn(self.atelier_lavage, suggestions)
        self.assertIn(self.atelier_cordonnerie, suggestions)  # pas filtre, meme incompatible

    def test_avec_capacites_filtre_reellement(self):
        """
        Le test central : une fois active, seul l'atelier reellement
        compatible avec 'lavage' doit etre suggere - l'atelier cordonnerie
        (sans capacite lavage declaree) ne doit jamais apparaitre.
        """
        definir_parametre("orchestrateur_utiliser_capacites", "true")
        suggestions = suggerer_partenaires("lavage")

        self.assertIn(self.atelier_lavage, suggestions)
        self.assertNotIn(self.atelier_cordonnerie, suggestions)


class OrchestrationMissionTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404886")
        self.partenaire = ouvrir_dossier("partenaire", "Atelier Test", "0700000112")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500}],
        )

    def test_orchestration_avec_acteur_manuel(self):
        mission = orchestrer_mission("collecte", self.commande, "lavage", acteur_assigne=self.livreur)
        self.assertEqual(mission.acteur_assigne, self.livreur)

    def test_orchestration_choisit_automatiquement(self):
        """Sans acteur fourni, l'orchestrateur doit choisir une suggestion valide."""
        mission = orchestrer_mission("collecte", self.commande, "lavage")
        self.assertIsNotNone(mission.acteur_assigne)

    def test_orchestration_declenche_notifications(self):
        """Chaque orchestration doit notifier l'acteur assigne ET le client (role Informe)."""
        nb_avant = Notification.objects.count()
        orchestrer_mission("collecte", self.commande, "lavage", acteur_assigne=self.livreur)
        nb_apres = Notification.objects.count()

        self.assertEqual(nb_apres, nb_avant + 2)  # une pour l'acteur, une pour le client

    def test_orchestration_relie_le_workflow_selectionne(self):
        """Une fois un workflow configure pour le service, il doit etre trace sur la Mission."""
        creer_workflow(
            "pressing_standard_orch", "lavage",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "cloture"}],
        )
        mission = orchestrer_mission("collecte", self.commande, "lavage", acteur_assigne=self.livreur)
        self.assertIsNotNone(mission.workflow)
        self.assertEqual(mission.workflow.nom, "pressing_standard_orch")

    def test_orchestration_sans_workflow_configure_reste_none(self):
        """Sans workflow configure pour ce service, la mission ne doit jamais lever d'erreur - juste rester non tracee."""
        mission = orchestrer_mission("collecte", self.commande, "service_sans_workflow", acteur_assigne=self.livreur)
        self.assertIsNone(mission.workflow)

    def test_orchestration_sans_partenaire_disponible_leve_erreur(self):
        """
        Avec capacites activees et aucun partenaire compatible, doit
        refuser explicitement plutot que d'assigner n'importe qui.
        """
        from configuration.services import definir_parametre
        definir_parametre("orchestrateur_utiliser_capacites", "true")

        with self.assertRaises(ValueError):
            orchestrer_mission("collecte", self.commande, "service_inexistant")

class SelectionWorkflowTests(TestCase):
    """Relie enfin orchestrateur au module workflows (Sprint 9), reste isole depuis sa creation."""

    def test_aucun_workflow_configure_retourne_none(self):
        """Un service sans workflow configure ne doit jamais lever d'erreur - juste None."""
        resultat = selectionner_workflow("service_jamais_configure")
        self.assertIsNone(resultat)

    def test_selection_workflow_pressing(self):
        creer_workflow(
            "pressing_standard_test", "lavage",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "cloture"}],
        )
        workflow = selectionner_workflow("lavage")
        self.assertEqual(workflow.nom, "pressing_standard_test")

    def test_selection_workflow_cordonnerie(self):
        creer_workflow(
            "cordonnerie_test", "cordonnerie",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "autre"}, {"type_evenement": "cloture"}],
        )
        workflow = selectionner_workflow("cordonnerie")
        self.assertEqual(workflow.nom, "cordonnerie_test")
        self.assertEqual(workflow.etapes.count(), 3)


class EtatExecutionTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963512")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404887")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage_exec", "quantite": 1, "prix_unitaire": 500}],
        )
        creer_workflow(
            "pressing_exec_test", "lavage_exec",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "mission_creee"}, {"type_evenement": "cloture"}],
        )

    def test_etat_none_sans_workflow_trace(self):
        mission = orchestrer_mission("collecte", self.commande, "service_sans_workflow_exec", acteur_assigne=self.livreur)
        self.assertIsNone(etat_execution(mission))

    def test_etat_derive_les_etapes_deja_realisees(self):
        mission = orchestrer_mission("collecte", self.commande, "lavage_exec", acteur_assigne=self.livreur)
        etat = etat_execution(mission)

        self.assertIsNotNone(etat)
        self.assertFalse(etat["termine"])
        self.assertEqual(etat["etape_courante"].type_evenement, "mission_creee")
        self.assertEqual(etat["prochaine_etape"].type_evenement, "cloture")

    def test_etat_termine_quand_toutes_etapes_realisees(self):
        from evenements.services import emettre_evenement
        mission = orchestrer_mission("collecte", self.commande, "lavage_exec", acteur_assigne=self.livreur)
        emettre_evenement(
            type_evenement="cloture",
            dossiers_concernes=[self.client_dossier],
            acteur_origine=self.client_dossier,
            objet_source=mission.commande,
        )
        etat = etat_execution(mission)
        self.assertTrue(etat["termine"])
        self.assertIsNone(etat["prochaine_etape"])


class NotificationEtapeFranchieTests(TestCase):
    """
    Verifie le signal post_save sur Evenement (orchestrateur/signals.py) :
    notification automatique quand une etape de workflow tracee est
    franchie - jamais de creation automatique de la mission suivante
    (decision de gouvernance, option 2 retenue plutot que l'option 1).
    """

    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963518")
        self.livreur = ouvrir_dossier("livreur", "Youande", "0799404892")
        self.ops = ouvrir_dossier("ops", "Amadou", "0700000300")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage_signal_test", "quantite": 1, "prix_unitaire": 500}],
        )
        creer_workflow(
            "pressing_signal_test", "lavage_signal_test",
            [{"type_evenement": "commande_creee"}, {"type_evenement": "mission_creee"}, {"type_evenement": "cloture"}],
        )

    def test_notifie_acteur_assigne_et_ops_a_la_creation_mission(self):
        """
        mission_creee est deja une etape de la sequence - orchestrer_mission
        emet cet evenement, le signal doit notifier le livreur ET l'OPS
        en plus des notifications deja envoyees par orchestrer_mission lui-meme.
        """
        nb_avant = Notification.objects.count()
        mission = orchestrer_mission("collecte", self.commande, "lavage_signal_test", acteur_assigne=self.livreur)
        nb_apres = Notification.objects.count()

        # orchestrer_mission notifie deja acteur + client (2) ; le signal ajoute livreur + ops (2 de plus)
        self.assertGreaterEqual(nb_apres, nb_avant + 3)
        self.assertTrue(
            Notification.objects.filter(dossier_destinataire=self.ops, evenement_declencheur__type_evenement="mission_creee").exists()
        )

    def test_aucune_notification_signal_si_pas_de_workflow_trace(self):
        """Sans workflow trace sur la mission, le signal ne doit rien declencher de supplementaire."""
        mission = orchestrer_mission("collecte", self.commande, "service_sans_workflow_signal", acteur_assigne=self.livreur)
        self.assertFalse(
            Notification.objects.filter(dossier_destinataire=self.ops).exists()
        )
