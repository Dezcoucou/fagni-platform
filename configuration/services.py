"""
Services internes du module configuration - FAGNI Platform (Lot 1, Sprint 11)

definir_parametre() est le seul point d'entree pour ecrire une nouvelle
valeur - ferme automatiquement la version precedente, ne l'ecrase jamais.
"""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Parametre, VersionParametre


class ParametreInconnu(Exception):
    """Leve quand on cherche une valeur pour une cle jamais definie ou jamais active a une date."""
    pass


@transaction.atomic
def definir_parametre(cle, valeur, description=""):
    """
    Definit (ou redefinit) la valeur d'un Parametre. Si une version
    courante existe deja, elle est fermee (valide_jusqu_a) - jamais
    supprimee ni ecrasee.
    """
    parametre, _ = Parametre.objects.get_or_create(
        cle=cle, defaults={"description": description},
    )

    version_courante = parametre.versions.filter(valide_jusqu_a__isnull=True).first()
    maintenant = timezone.now()

    if version_courante:
        version_courante.valide_jusqu_a = maintenant
        version_courante.save(update_fields=["valide_jusqu_a"])

    return VersionParametre.objects.create(parametre=parametre, valeur=valeur)


def obtenir_version_courante(cle):
    """
    Retourne l'objet VersionParametre actif, pas seulement sa valeur -
    necessaire quand l'appelant doit tracer PRECISEMENT quelle version
    tarifaire a produit un resultat (ex: Simulation.version_parametre_prix,
    FOS-213), pas juste connaitre le prix du moment.
    """
    try:
        parametre = Parametre.objects.get(cle=cle)
    except Parametre.DoesNotExist:
        raise ParametreInconnu(f"Aucun parametre defini pour la cle '{cle}'.")

    version = parametre.versions.filter(valide_jusqu_a__isnull=True).first()
    if not version:
        raise ParametreInconnu(f"Le parametre '{cle}' n'a jamais eu de version active.")
    return version


def obtenir_valeur_courante(cle):
    """Retourne la valeur active maintenant."""
    return obtenir_version_courante(cle).valeur


def obtenir_valeur_a_date(cle, date):
    """
    Retourne la valeur qui etait active a une date precise dans le passe -
    la garantie centrale de ce module : un changement recent ne doit
    jamais alterer ce qu'une commande passee avait reellement engage.
    """
    try:
        parametre = Parametre.objects.get(cle=cle)
    except Parametre.DoesNotExist:
        raise ParametreInconnu(f"Aucun parametre defini pour la cle '{cle}'.")

    version = parametre.versions.filter(
        valide_a_partir_de__lte=date,
    ).filter(
        Q(valide_jusqu_a__isnull=True) | Q(valide_jusqu_a__gt=date)
    ).order_by("-valide_a_partir_de").first()

    if not version:
        raise ParametreInconnu(f"Aucune version du parametre '{cle}' n'etait active a la date {date}.")
    return version.valeur
