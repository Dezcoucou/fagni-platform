"""
Tests unitaires du module evenements - FAGNI Platform (Lot 1, Sprint 2)
Chaque test verifie directement une regle du BOS, notamment l'immutabilite
(chapitre 9) - y compris le cas de suppression en masse via QuerySet,
une vraie faille decouverte et corrigee pendant le developpement (voir
Pilot Book / Execution Book).
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from .models import Evenement


class ImmutabiliteEvenementTests(TestCase):
    def setUp(self):
        self.dossier = ouvrir_dossier("client", "Client Test", "0700000001")

    def test_creation_normale(self):
        """Un Evenement peut etre cree normalement."""
        e = Evenement.objects.create(
            type_evenement="commande_creee", acteur_origine=self.dossier,
        )
        e.dossiers_concernes.set([self.dossier])
        self.assertIsNotNone(e.id)

    def test_modification_instance_bloquee(self):
        """Un Evenement ne peut jamais etre modifie via son instance."""
        e = Evenement.objects.create(
            type_evenement="commande_creee", acteur_origine=self.dossier,
        )
        e.type_evenement = "cloture"
        with self.assertRaises(ValueError):
            e.save()

    def test_suppression_instance_bloquee(self):
        """Un Evenement ne peut jamais etre supprime via son instance."""
        e = Evenement.objects.create(
            type_evenement="commande_creee", acteur_origine=self.dossier,
        )
        with self.assertRaises(ValueError):
            e.delete()

    def test_suppression_masse_queryset_bloquee(self):
        """
        Regle critique : la suppression en masse via QuerySet
        (Evenement.objects.filter(...).delete()) doit etre bloquee comme
        la suppression individuelle - Django ne route pas .delete() sur un
        QuerySet vers .delete() sur chaque instance, d'ou un correctif
        dedie necessaire au niveau du Manager/QuerySet.
        """
        e = Evenement.objects.create(
            type_evenement="commande_creee", acteur_origine=self.dossier,
        )
        with self.assertRaises(ValueError):
            Evenement.objects.filter(id=e.id).delete()

        # Confirme que l'evenement existe toujours reellement
        self.assertTrue(Evenement.objects.filter(id=e.id).exists())


class RattachementDossierTests(TestCase):
    def test_evenement_toujours_rattache_a_un_dossier(self):
        """FOS-211 section 2.4 : un Evenement est toujours rattache a au moins un Dossier."""
        d1 = ouvrir_dossier("client", "Client", "0700000002")
        d2 = ouvrir_dossier("livreur", "Livreur", "0700000003")

        e = Evenement.objects.create(
            type_evenement="collecte_terminee", acteur_origine=d2,
        )
        e.dossiers_concernes.set([d1, d2])

        self.assertEqual(e.dossiers_concernes.count(), 2)
        self.assertIn(d1, e.dossiers_concernes.all())
        self.assertIn(d2, e.dossiers_concernes.all())
