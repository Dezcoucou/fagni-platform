"""
Services internes du module abonnements - FAGNI Platform.

generer_commande_depuis_abonnement() reutilise directement
commandes.services.creer_commande() - jamais une nouvelle chaine
d'evenements inventee (FOS-211 principe general), la Commande generee
suit exactement le meme cycle de vie qu'une Commande passee manuellement.

Volontairement PAS de declenchement automatique par tache planifiee a
ce stade - le service est appelable (OPS, script), l'automatisation par
cron sera une decision separee, une fois la fiabilite confirmee sur un
volume reel (meme principe que capacites_activees : construit, active
seulement sur decision explicite).
"""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from configuration.services import obtenir_valeur_courante, ParametreInconnu
from commandes.services import creer_commande
from commandes.models import Commande
from .models import Abonnement


class DossierNonUtilisable(Exception):
    """Leve quand on tente de creer un abonnement pour un Dossier suspendu ou exclu."""
    pass


class CommandeDejaGenereePourCetteEcheance(Exception):
    """
    Leve quand une Commande a deja ete generee pour cet abonnement dans
    les 6 derniers jours - protection anti-doublon avant automatisation
    par tache planifiee (evite une double facturation en cas de
    declenchement multiple, cf. decision de gouvernance du 19 juillet
    2026 : automatisation cron differee tant que cette protection et un
    volume reel ne sont pas confirmes).
    """
    pass


class PrixAbonnementNonConfigure(Exception):
    """Leve quand le prix du pack/taille demande n'a jamais ete defini dans configuration."""
    pass


def creer_abonnement(dossier_client, pack, taille_sac, jour_collecte, jour_livraison, date_debut=None):
    """
    Cree un Abonnement. Refuse explicitement si le Dossier n'est pas
    utilisable - meme regle que pour les Missions (BOS chapitre 7.2).
    """
    if not dossier_client.est_utilisable():
        raise DossierNonUtilisable(
            f"Le Dossier de {dossier_client.nom} n'est pas utilisable "
            f"(statut: {dossier_client.get_statut_display()}) - "
            f"aucun Abonnement ne peut lui etre associe."
        )

    return Abonnement.objects.create(
        dossier_client=dossier_client,
        pack=pack,
        taille_sac=taille_sac,
        jour_collecte=jour_collecte,
        jour_livraison=jour_livraison,
        date_debut=date_debut,
    )


def _cle_prix(pack, taille_sac):
    return f"abonnement_prix_{pack}_{taille_sac}"


def obtenir_prix_pack(pack, taille_sac):
    """
    Lit le prix courant du pack/taille depuis configuration - jamais
    code en dur (FOS-211 section 9.2). Leve explicitement si jamais
    defini, plutot que de supposer un prix par defaut arbitraire.
    """
    try:
        valeur = obtenir_valeur_courante(_cle_prix(pack, taille_sac))
        return float(valeur)
    except ParametreInconnu:
        raise PrixAbonnementNonConfigure(
            f"Aucun prix configure pour le pack '{pack}' / sac '{taille_sac}' "
            f"(cle attendue: '{_cle_prix(pack, taille_sac)}') - definir via "
            f"configuration.services.definir_parametre() avant de generer une commande."
        )


DELAI_MIN_ENTRE_GENERATIONS = timedelta(days=6)


@transaction.atomic
def generer_commande_depuis_abonnement(abonnement):
    """
    Genere une Commande a partir d'un Abonnement actif, pour l'echeance
    courante. Refuse si l'abonnement n'est pas actif - jamais de
    generation silencieuse pour un abonnement suspendu ou resilie.

    Anti-doublon : refuse si une Commande a deja ete generee pour cet
    abonnement il y a moins de 6 jours - protection ajoutee avant toute
    automatisation par tache planifiee, pour eviter une double
    facturation en cas de declenchement multiple.
    """
    if not abonnement.est_actif():
        raise ValueError(
            f"L'abonnement #{abonnement.id} n'est pas actif "
            f"(statut: {abonnement.get_statut_display()}) - aucune Commande ne peut en etre generee."
        )

    seuil = timezone.now() - DELAI_MIN_ENTRE_GENERATIONS
    derniere_commande = Commande.objects.filter(
        abonnement=abonnement, created_at__gte=seuil,
    ).order_by("-created_at").first()
    if derniere_commande:
        raise CommandeDejaGenereePourCetteEcheance(
            f"Une Commande (#{derniere_commande.id}) a deja ete generee pour "
            f"l'abonnement #{abonnement.id} le {derniere_commande.created_at.strftime('%d/%m/%Y')} "
            f"- prochaine generation possible a partir du "
            f"{(derniere_commande.created_at + DELAI_MIN_ENTRE_GENERATIONS).strftime('%d/%m/%Y')}."
        )

    prix = obtenir_prix_pack(abonnement.pack, abonnement.taille_sac)

    return creer_commande(
        dossier_client=abonnement.dossier_client,
        lignes_data=[{
            "article": f"Sac abonnement {abonnement.get_taille_sac_display()}",
            "service": "abonnement",
            "quantite": 1,
            "prix_unitaire": prix,
        }],
        delai_annonce=f"Collecte {abonnement.get_jour_collecte_display()}, livraison {abonnement.get_jour_livraison_display()}",
        abonnement=abonnement,
    )
