"""
Tests unitaires du module workflows - FAGNI Platform (Lot 1, Sprint 9)
Reproduit l'exemple exact de FOS-210 v1.1 section 12.1 : le pressing suit
la chaine de reference sans ecart, la cordonnerie y insere une etape de
devis obligatoire avant la creation de Mission.
"""
from django.test import TestCase
from .models import Workflow, EtapeWorkflow
from .services import creer_workflow, obtenir_sequence


class CreationWorkflowTests(TestCase):
    def test_workflow_sans_etapes_refuse(self):
        with self.assertRaises(ValueError):
            creer_workflow("vide", "test", [])

    def test_ordre_deduit_de_la_position(self):
        """L'ordre est toujours deduit de la position dans la liste, jamais suppose."""
        workflow = creer_workflow("test_ordre", "test", [
            {"type_evenement": "commande_creee"},
            {"type_evenement": "collecte_commencee"},
            {"type_evenement": "collecte_terminee"},
        ])
        etapes = obtenir_sequence(workflow)
        self.assertEqual([e.ordre for e in etapes], [1, 2, 3])
        self.assertEqual([e.type_evenement for e in etapes], [
            "commande_creee", "collecte_commencee", "collecte_terminee",
        ])


class WorkflowPressingStandardTests(TestCase):
    """FOS-210 v1.1, section 12.1 : le pressing suit la sequence de reference sans ecart."""

    def test_pressing_suit_sequence_reference_complete(self):
        sequence_reference = [
            "commande_creee", "collecte_commencee", "collecte_terminee",
            "inspection_realisee", "paiement_confirme", "mission_creee",
            "mission_acceptee", "service_termine", "controle_qualite_realise",
            "livraison_effectuee", "avis_recu", "cloture",
        ]
        workflow = creer_workflow(
            "pressing_standard", "lavage",
            [{"type_evenement": t} for t in sequence_reference],
            description="Suit la sequence de reference sans ecart",
        )
        etapes = obtenir_sequence(workflow)
        self.assertEqual([e.type_evenement for e in etapes], sequence_reference)
        self.assertEqual(len(etapes), 12)


class WorkflowCordonnerieTests(TestCase):
    """
    FOS-210 v1.1, section 12.1 : la cordonnerie ajoute une etape de devis
    obligatoire avant 'mission_creee', par rapport au pressing standard.
    """
    def test_cordonnerie_insere_etape_devis_avant_mission_creee(self):
        workflow = creer_workflow(
            "cordonnerie", "cordonnerie",
            [
                {"type_evenement": "commande_creee"},
                {"type_evenement": "collecte_commencee"},
                {"type_evenement": "collecte_terminee"},
                {"type_evenement": "inspection_realisee"},
                {"type_evenement": "autre", "obligatoire": True},  # etape de devis
                {"type_evenement": "paiement_confirme"},
                {"type_evenement": "mission_creee"},
            ],
            description="Ajoute un devis obligatoire avant la creation de Mission",
        )
        etapes = obtenir_sequence(workflow)
        types_dans_ordre = [e.type_evenement for e in etapes]

        idx_devis = types_dans_ordre.index("autre")
        idx_mission = types_dans_ordre.index("mission_creee")

        # L'etape de devis doit precede strictement la creation de Mission
        self.assertLess(idx_devis, idx_mission)

    def test_workflows_pressing_et_cordonnerie_coexistent_sans_conflit(self):
        """Deux Workflows differents ne se marchent jamais dessus - contraintes independantes."""
        creer_workflow("pressing_isolee", "lavage", [{"type_evenement": "commande_creee"}])
        creer_workflow("cordonnerie_isolee", "cordonnerie", [{"type_evenement": "commande_creee"}])

        self.assertEqual(Workflow.objects.count(), 2)
        # Chacun garde son propre ordre 1 sans collision
        self.assertEqual(EtapeWorkflow.objects.filter(ordre=1).count(), 2)
