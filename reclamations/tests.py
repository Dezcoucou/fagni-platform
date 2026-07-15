"""
Tests unitaires du module reclamations - FAGNI Platform (Lot 1, Sprint 6)
Verifie en particulier la nuance du BOS chapitre 4.2 : sans preuve, la
resolution est TOUJOURS favorable au client, jamais une simple option.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from commandes.services import creer_commande
from evenements.models import Evenement
from .models import Reclamation
from .services import ouvrir_reclamation, resoudre_reclamation


class OuvertureReclamationTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")
        self.partenaire = ouvrir_dossier("partenaire", "Atelier X", "0546562713")
        self.commande = creer_commande(
            self.client_dossier,
            [{"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500}],
        )

    def test_ouverture_sans_preuve_autorisee(self):
        """Ouvrir une reclamation ne necessite jamais de preuve prealable."""
        reclamation = ouvrir_reclamation(
            self.commande, [self.client_dossier, self.partenaire],
            "Article manquant a la livraison",
        )
        self.assertEqual(reclamation.statut, "ouverte")
        self.assertEqual(reclamation.dossiers_concernes.count(), 2)

    def test_ouverture_emet_evenement(self):
        nb_avant = Evenement.objects.count()
        ouvrir_reclamation(
            self.commande, [self.client_dossier], "Retard important",
        )
        self.assertEqual(Evenement.objects.count(), nb_avant + 1)
        self.assertTrue(Evenement.objects.filter(type_evenement="reclamation_ouverte").exists())


class ResolutionAvecPreuveNuanceTests(TestCase):
    """
    Coeur du BOS chapitre 4.2 : verifie precisement la nuance entre
    resolution avec preuve (suit la decision donnee) et sans preuve
    (toujours forcee en faveur du client).
    """
    def setUp(self):
        client_dossier = ouvrir_dossier("client", "Client Test", "0700000030")
        commande = creer_commande(
            client_dossier,
            [{"article": "Pantalon", "service": "lavage", "quantite": 1, "prix_unitaire": 500}],
        )
        self.reclamation = ouvrir_reclamation(
            commande, [client_dossier], "Tache non enlevee",
        )

    def test_resolution_avec_preuve_favorable_client(self):
        """Avec preuve, la decision suit ce qui est passe explicitement."""
        resoudre_reclamation(
            self.reclamation, decision="Preuve photo confirme la tache",
            preuves=["photo_evidence"], favorable_au_client=True,
        )
        self.reclamation.refresh_from_db()
        self.assertTrue(self.reclamation.favorable_au_client)
        self.assertTrue(self.reclamation.resolu_avec_preuve)

    def test_resolution_avec_preuve_defavorable_client(self):
        """Avec preuve, la decision peut aussi aller contre le client si les faits le montrent."""
        resoudre_reclamation(
            self.reclamation, decision="Photo de collecte ne montre aucune tache",
            preuves=["photo_collecte"], favorable_au_client=False,
        )
        self.reclamation.refresh_from_db()
        self.assertFalse(self.reclamation.favorable_au_client)

    def test_resolution_sans_preuve_toujours_favorable_client(self):
        """
        Regle centrale du BOS 4.2 : meme si favorable_au_client=False est
        explicitement passe, l'absence de preuve force True quand meme.
        """
        resoudre_reclamation(
            self.reclamation, decision="Aucune preuve disponible",
            preuves=None, favorable_au_client=False,  # tentative de forcer defavorable
        )
        self.reclamation.refresh_from_db()

        # Le systeme corrige : True l'emporte toujours sans preuve
        self.assertTrue(self.reclamation.favorable_au_client)
        self.assertFalse(self.reclamation.resolu_avec_preuve)

    def test_resolution_liste_preuves_vide_traitee_comme_absence(self):
        """Une liste vide de preuves doit etre traitee exactement comme None."""
        resoudre_reclamation(
            self.reclamation, decision="Liste vide", preuves=[], favorable_au_client=False,
        )
        self.reclamation.refresh_from_db()
        self.assertTrue(self.reclamation.favorable_au_client)
