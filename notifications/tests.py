"""
Tests unitaires du module notifications - FAGNI Platform (Lot 1, Sprint 14
- dernier module du Core Domain)
Le test le plus important : rejouer le meme envoi ne doit jamais produire
un doublon - reproduit exactement la lecon apprise en pilote V1 sur
l'app driver, cette fois posee des le depart, pas corrigee apres coup.
"""
from django.test import TestCase
from dossiers.services import ouvrir_dossier
from evenements.services import emettre_evenement
from .models import Notification
from .services import envoyer_notification, marquer_envoyee, marquer_echouee


class EnvoiNotificationTests(TestCase):
    def setUp(self):
        self.dossier = ouvrir_dossier("livreur", "Youande", "0799404886")
        self.evenement = emettre_evenement(
            type_evenement="mission_creee", dossiers_concernes=[self.dossier],
            acteur_origine=self.dossier,
        )

    def test_envoi_simple(self):
        notif = envoyer_notification(
            self.dossier, "push", self.evenement, "Nouvelle mission disponible",
        )
        self.assertEqual(notif.statut_envoi, "en_attente")
        self.assertEqual(notif.canal, "push")


class AntiDoublonTests(TestCase):
    """
    Coeur de ce Sprint - reproduit la lecon retenue du pilote V1 : un
    tag anti-doublon avait du etre ajoute a posteriori sur l'app driver
    pour ce probleme exact.
    """
    def setUp(self):
        self.dossier = ouvrir_dossier("livreur", "Ange David", "0788509933")
        self.evenement = emettre_evenement(
            type_evenement="collecte_terminee", dossiers_concernes=[self.dossier],
            acteur_origine=self.dossier,
        )

    def test_rejeu_meme_envoi_ne_cree_pas_de_doublon(self):
        """
        Le test central : appeler envoyer_notification deux fois avec
        exactement les memes parametres (meme dossier, meme canal, meme
        evenement) ne doit produire qu'une seule Notification en base.
        """
        n1 = envoyer_notification(self.dossier, "push", self.evenement, "Collecte terminee")
        n2 = envoyer_notification(self.dossier, "push", self.evenement, "Collecte terminee")

        self.assertEqual(n1.id, n2.id)  # meme instance renvoyee
        self.assertEqual(
            Notification.objects.filter(
                dossier_destinataire=self.dossier, canal="push", evenement_declencheur=self.evenement,
            ).count(),
            1,
        )

    def test_canaux_differents_restent_distincts(self):
        """Le meme evenement peut legitimement declencher plusieurs canaux differents."""
        n_push = envoyer_notification(self.dossier, "push", self.evenement, "Collecte terminee")
        n_whatsapp = envoyer_notification(self.dossier, "whatsapp", self.evenement, "Collecte terminee")

        self.assertNotEqual(n_push.id, n_whatsapp.id)
        self.assertEqual(Notification.objects.filter(evenement_declencheur=self.evenement).count(), 2)

    def test_evenements_differents_restent_distincts(self):
        """Deux evenements differents, meme dossier et canal, produisent deux notifications distinctes."""
        evenement2 = emettre_evenement(
            type_evenement="livraison_effectuee", dossiers_concernes=[self.dossier],
            acteur_origine=self.dossier,
        )

        n1 = envoyer_notification(self.dossier, "push", self.evenement, "Collecte terminee")
        n2 = envoyer_notification(self.dossier, "push", evenement2, "Livraison effectuee")

        self.assertNotEqual(n1.id, n2.id)


class StatutEnvoiTests(TestCase):
    def test_marquage_envoyee(self):
        dossier = ouvrir_dossier("client", "Rita", "0708963511")
        evt = emettre_evenement(
            type_evenement="commande_creee", dossiers_concernes=[dossier], acteur_origine=dossier,
        )
        notif = envoyer_notification(dossier, "whatsapp", evt, "Votre commande est confirmee")

        marquer_envoyee(notif)
        notif.refresh_from_db()
        self.assertEqual(notif.statut_envoi, "envoyee")

    def test_marquage_echouee(self):
        dossier = ouvrir_dossier("client", "Wilson", "0749423747")
        evt = emettre_evenement(
            type_evenement="commande_creee", dossiers_concernes=[dossier], acteur_origine=dossier,
        )
        notif = envoyer_notification(dossier, "email", evt, "Votre commande est confirmee")

        marquer_echouee(notif)
        notif.refresh_from_db()
        self.assertEqual(notif.statut_envoi, "echouee")
