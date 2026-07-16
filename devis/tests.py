"""
Tests unitaires du module devis - FAGNI Platform (Lot 2, Sprint 17)
Verifie l'integration reelle avec le module decisions (Sprint 10) : un
devis reste toujours une decision humaine, meme quand les trois
conditions du BOS 12.3 sont parfaitement reunies.
"""
from decimal import Decimal
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from decisions.models import ReglaDecision, Decision
from .models import Devis
from .services import demander_devis, proposer_montant, repondre_devis


class DemandeDevisTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Devis", "0700000093")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chaussures", "service": "cordonnerie", "quantite": 1, "prix_unitaire": 0}],
        )

    def test_demande_simple(self):
        devis = demander_devis(self.commande, "Reparation semelle decollee")
        self.assertEqual(devis.statut, "en_attente")
        self.assertIsNone(devis.montant_propose)


class PropositionMontantTests(TestCase):
    """Coeur de ce Sprint : verifie l'integration reelle avec le module decisions."""

    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Devis 2", "0700000094")
        self.artisan = ouvrir_dossier("artisan", "Cordonnier X", "0700000095")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Sac a main", "service": "maroquinerie", "quantite": 1, "prix_unitaire": 0}],
        )
        self.devis = demander_devis(self.commande, "Reparation fermoir casse")

    def test_proposition_met_a_jour_devis(self):
        proposer_montant(self.devis, 2500, self.artisan)
        self.devis.refresh_from_db()
        self.assertEqual(self.devis.montant_propose, 2500)
        self.assertEqual(self.devis.propose_par, self.artisan)
        self.assertEqual(self.devis.statut, "propose")

    def test_proposition_cree_regle_toujours_humaine(self):
        """La regle 'devis_commande' doit exister avec toujours_humaine=True."""
        proposer_montant(self.devis, 2500, self.artisan)
        regle = ReglaDecision.objects.get(code="devis_commande")
        self.assertTrue(regle.toujours_humaine)

    def test_proposition_enregistre_decision_humaine(self):
        """
        Le test central : meme avec toutes les conditions d'automatisation
        reunies (verifie explicitement dans le service), la Decision
        enregistree doit rester 'humaine' - jamais 'automatique'.
        """
        proposer_montant(self.devis, 2500, self.artisan)

        decision = Decision.objects.filter(regle__code="devis_commande").latest("created_at")
        self.assertEqual(decision.niveau_applique, "humaine")
        self.assertEqual(decision.decideur, self.artisan)
        self.assertEqual(decision.objet_source, self.devis)


class ReponseDevisTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Client Reponse", "0700000096")
        self.artisan = ouvrir_dossier("artisan", "Cordonnier Y", "0700000097")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chaussures", "service": "cordonnerie", "quantite": 1, "prix_unitaire": 500}],
        )  # prix_engage = 500
        self.devis = demander_devis(self.commande, "Ressemelage complet")
        proposer_montant(self.devis, 3000, self.artisan)

    def test_acceptation_revise_le_prix(self):
        repondre_devis(self.devis, accepte=True)

        self.devis.refresh_from_db()
        self.commande.refresh_from_db()
        self.assertEqual(self.devis.statut, "accepte")
        self.assertEqual(self.commande.prix_engage, Decimal("3500"))  # 500 + 3000

    def test_refus_ne_touche_jamais_le_prix(self):
        prix_avant = self.commande.prix_engage
        repondre_devis(self.devis, accepte=False)

        self.devis.refresh_from_db()
        self.commande.refresh_from_db()
        self.assertEqual(self.devis.statut, "refuse")
        self.assertEqual(self.commande.prix_engage, prix_avant)
