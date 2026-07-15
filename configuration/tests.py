"""
Tests unitaires du module configuration - FAGNI Platform (Lot 1, Sprint 11)
Le test le plus important : retrouver la valeur exacte qui etait active
a une date passee, meme apres plusieurs changements ulterieurs - c'est
la garantie centrale de ce module.
"""
import time
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from .models import Parametre, VersionParametre
from .services import (
    definir_parametre,
    obtenir_valeur_courante,
    obtenir_valeur_a_date,
    ParametreInconnu,
)


class DefinitionParametreTests(TestCase):
    def test_premiere_definition(self):
        definir_parametre("commission_pressing_pct", "50")
        self.assertEqual(obtenir_valeur_courante("commission_pressing_pct"), "50")

    def test_parametre_inconnu_leve_erreur(self):
        with self.assertRaises(ParametreInconnu):
            obtenir_valeur_courante("cle_qui_n_existe_pas")


class HistoriqueParametreTests(TestCase):
    """Coeur de ce Sprint : l'historique complet doit toujours rester intact."""

    def test_redefinition_ferme_ancienne_version_sans_la_supprimer(self):
        definir_parametre("frais_livraison_fcfa", "2000")
        definir_parametre("frais_livraison_fcfa", "2500")

        parametre = Parametre.objects.get(cle="frais_livraison_fcfa")
        self.assertEqual(parametre.versions.count(), 2)  # les deux versions existent toujours

        version_ancienne = parametre.versions.order_by("valide_a_partir_de").first()
        self.assertIsNotNone(version_ancienne.valide_jusqu_a)  # fermee, pas supprimee
        self.assertEqual(version_ancienne.valeur, "2000")

    def test_valeur_courante_toujours_la_derniere(self):
        definir_parametre("commission_pressing_pct", "40")
        definir_parametre("commission_pressing_pct", "45")
        definir_parametre("commission_pressing_pct", "50")

        self.assertEqual(obtenir_valeur_courante("commission_pressing_pct"), "50")


class ValeurADateTests(TestCase):
    """
    Le test central : un changement recent ne doit jamais alterer ce
    qu'une commande passee avait reellement engage - simule ici trois
    versions successives d'un meme parametre.
    """
    def test_retrouve_valeur_historique_apres_plusieurs_changements(self):
        v1 = definir_parametre("commission_pressing_pct", "40")
        date_v1 = timezone.now()

        # Simuler un ecoulement de temps reel entre les versions
        time.sleep(0.01)
        v2 = definir_parametre("commission_pressing_pct", "45")
        date_v2 = timezone.now()

        time.sleep(0.01)
        v3 = definir_parametre("commission_pressing_pct", "50")

        # Verification : chaque date historique doit retrouver sa propre valeur
        self.assertEqual(obtenir_valeur_a_date("commission_pressing_pct", date_v1), "40")
        self.assertEqual(obtenir_valeur_a_date("commission_pressing_pct", date_v2), "45")

        # La valeur courante reste la derniere
        self.assertEqual(obtenir_valeur_courante("commission_pressing_pct"), "50")

    def test_date_avant_toute_definition_leve_erreur(self):
        definir_parametre("nouveau_parametre", "10")
        date_avant = timezone.now() - timedelta(days=1)

        with self.assertRaises(ParametreInconnu):
            obtenir_valeur_a_date("nouveau_parametre", date_avant)
