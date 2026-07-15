"""
Tests unitaires du module commandes - FAGNI Platform (Lot 1, Sprint 3)
Inclut le premier test d'integration reel entre deux modules : une
Commande creee doit produire un Evenement verifiable dans le module
evenements, jamais suppose.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from evenements.models import Evenement
from .models import Commande, LigneCommande
from .services import creer_commande, reviser_prix, changer_statut_ligne, RevisionPrixInterdite


class CreationCommandeTests(TestCase):
    def setUp(self):
        self.client_dossier = ouvrir_dossier("client", "Rita", "0708963511")

    def test_creation_simple(self):
        """Une Commande peut etre creee avec une ligne, prix calcule correctement."""
        lignes = [{"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500}]
        commande = creer_commande(self.client_dossier, lignes)

        self.assertEqual(commande.prix_engage, 1500)
        self.assertEqual(commande.lignes.count(), 1)

    def test_prix_engage_egale_somme_lignes(self):
        """Le prix engage est la somme exacte de toutes les lignes."""
        lignes = [
            {"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500},
            {"article": "Pantalon", "service": "repassage", "quantite": 2, "prix_unitaire": 400},
        ]
        commande = creer_commande(self.client_dossier, lignes)
        self.assertEqual(commande.prix_engage, 1500 + 800)

    def test_commande_sans_lignes_refusee(self):
        """Une Commande ne peut jamais exister sans au moins une ligne."""
        with self.assertRaises(ValueError):
            creer_commande(self.client_dossier, [])


class IntegrationEvenementsTests(TestCase):
    """
    Test d'integration reel entre les modules commandes et evenements -
    verifie que creer_commande() emet effectivement l'evenement attendu,
    pas seulement que la Commande existe.
    """
    def test_creation_commande_emet_evenement(self):
        d = ouvrir_dossier("client", "Wilson", "0749423747")
        lignes = [{"article": "Chemise", "service": "lavage", "quantite": 5, "prix_unitaire": 500}]

        nb_evenements_avant = Evenement.objects.count()
        commande = creer_commande(d, lignes)
        nb_evenements_apres = Evenement.objects.count()

        self.assertEqual(nb_evenements_apres, nb_evenements_avant + 1)

        evenement = Evenement.objects.filter(type_evenement="commande_creee").latest("horodatage")
        self.assertEqual(evenement.acteur_origine, d)
        self.assertIn(d, evenement.dossiers_concernes.all())
        self.assertEqual(evenement.objet_source, commande)
        self.assertEqual(evenement.donnees["nb_lignes"], 1)


class RevisionPrixTests(TestCase):
    def setUp(self):
        d = ouvrir_dossier("client", "Client Test", "0700000010")
        self.commande = creer_commande(
            d, [{"article": "Chemise", "service": "lavage", "quantite": 1, "prix_unitaire": 1000}],
        )

    def test_baisse_prix_toujours_autorisee(self):
        """Une baisse de prix ne necessite jamais d'accord explicite - favorable au client."""
        reviser_prix(self.commande, 800, accord_client=False)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.prix_engage, 800)

    def test_hausse_prix_sans_accord_refusee(self):
        """BOS chapitre 4.1 : une hausse sans accord explicite du client est interdite."""
        with self.assertRaises(RevisionPrixInterdite):
            reviser_prix(self.commande, 1500, accord_client=False)

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.prix_engage, 1000)  # inchange

    def test_hausse_prix_avec_accord_autorisee(self):
        """Avec accord explicite, la hausse devient possible."""
        reviser_prix(self.commande, 1500, accord_client=True)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.prix_engage, 1500)


class StatutParLigneTests(TestCase):
    def test_lignes_independantes(self):
        """
        Decision tranchee : chaque ligne progresse independamment - changer
        le statut d'une ligne ne doit jamais affecter les autres lignes de
        la meme Commande.
        """
        d = ouvrir_dossier("client", "Client Multi-Lignes", "0700000011")
        commande = creer_commande(d, [
            {"article": "Chemise", "service": "lavage", "quantite": 3, "prix_unitaire": 500},
            {"article": "Pantalon", "service": "retouche", "quantite": 1, "prix_unitaire": 1000},
        ])

        ligne1, ligne2 = commande.lignes.all()
        changer_statut_ligne(ligne1, "livree")

        ligne1.refresh_from_db()
        ligne2.refresh_from_db()

        self.assertEqual(ligne1.statut, "livree")
        self.assertEqual(ligne2.statut, "en_attente")  # inchangee
