from .services import normaliser_telephone_ci
"""
Tests unitaires du module dossiers - FAGNI Platform (Lot 1, Sprint 1)
Chaque test verifie directement une regle du BOS ou de FOS-210/211, jamais
un simple detail d'implementation.
"""
from django.test import TestCase
from .models import Dossier
from .services import (
    ouvrir_dossier,
    modifier_niveau_confiance,
    suspendre_dossier,
    exclure_dossier,
    DossierDejaExistant,
)


class OuvertureDossierTests(TestCase):
    def test_ouverture_simple(self):
        """Un Dossier peut etre ouvert normalement."""
        d = ouvrir_dossier("client", "Rita", "0708963511")
        self.assertEqual(d.statut, "actif")
        self.assertEqual(d.niveau_confiance, 50)

    def test_refus_doublon_actif(self):
        """
        Regle centrale : un acteur ne peut avoir qu'un seul Dossier actif
        (FOS-211 section 2.1) - reproduit le vrai incident du doublon
        partenaire corrige en pilote V1.
        """
        ouvrir_dossier("partenaire", "L&O pressing", "0152025147")
        with self.assertRaises(DossierDejaExistant):
            ouvrir_dossier("partenaire", "L&O (doublon)", "0152025147")

    def test_meme_telephone_types_differents_autorise(self):
        """Le meme telephone peut correspondre a deux acteurs de types differents."""
        ouvrir_dossier("client", "Ange David (client)", "0788509933")
        d2 = ouvrir_dossier("livreur", "Ange David (livreur)", "0788509933")
        self.assertIsNotNone(d2.id)


class NiveauConfianceTests(TestCase):
    def test_modification_cree_historique(self):
        """
        Toute modification du niveau de confiance doit produire une trace
        immuable (BOS chapitre 9) - jamais un changement silencieux.
        """
        d = ouvrir_dossier("livreur", "Youande", "0799404886")
        modifier_niveau_confiance(d, 65, "Cinq livraisons sans incident")
        d.refresh_from_db()

        self.assertEqual(d.niveau_confiance, 65)
        self.assertEqual(d.historique_confiance.count(), 1)
        entree = d.historique_confiance.first()
        self.assertEqual(entree.ancien_niveau, 50)
        self.assertEqual(entree.nouveau_niveau, 65)


class StatutDossierTests(TestCase):
    def test_suspension_rend_inutilisable(self):
        """Un Dossier suspendu ne doit plus etre utilisable pour une nouvelle Mission."""
        d = ouvrir_dossier("livreur", "Test Livreur", "0700000001")
        self.assertTrue(d.est_utilisable())

        suspendre_dossier(d, "Retard repete non explique")
        d.refresh_from_db()
        self.assertFalse(d.est_utilisable())

    def test_exclusion_exige_validateur_humain(self):
        """
        BOS chapitre 7.2 : l'exclusion n'est jamais une decision automatique -
        elle doit toujours etre attribuable a une personne identifiee.
        """
        d = ouvrir_dossier("partenaire", "Test Partenaire", "0700000002")
        with self.assertRaises(ValueError):
            exclure_dossier(d, "Fraude averee", valide_par="")

        # Avec un validateur identifie, l'exclusion doit reussir
        exclure_dossier(d, "Fraude averee", valide_par="CEO")
        d.refresh_from_db()
        self.assertEqual(d.statut, "exclu")
        self.assertFalse(d.est_utilisable())


class NormaliserTelephoneCiTests(TestCase):
    def test_variantes_produisent_le_meme_resultat(self):
        variantes = [
            "0748643892",
            "+225 07 48 64 38 92",
            "225-0748643892",
            "225748643892",
        ]
        resultats = {normaliser_telephone_ci(v) for v in variantes}
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats.pop(), "0748643892")

    def test_telephone_vide_retourne_vide(self):
        self.assertEqual(normaliser_telephone_ci(""), "")

    def test_telephone_deja_normalise_inchange(self):
        self.assertEqual(normaliser_telephone_ci("0700000001"), "0700000001")
