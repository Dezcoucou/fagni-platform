"""
Services internes du module accounts - FAGNI Platform (Lot 1, Sprint 12)

autoriser_action() est la seule fonction de decision de ce module - et
elle ne decide jamais une action metier elle-meme (FOS-211 section 9.1,
limite volontaire). Elle repond uniquement "ce role a-t-il le droit de
tenter cette action", jamais "cette action doit-elle avoir lieu".
"""
from .models import Compte

# Cartographie simple role -> actions autorisees. Volontairement plate
# et explicite - pas de heritage de permissions, pas de complexite non
# prouvee necessaire a ce stade (BOS chapitre 8).
PERMISSIONS_PAR_ROLE = {
    "membre": {"consulter"},
    "superviseur": {"consulter", "valider"},
    "administrateur": {"consulter", "valider", "gerer_organisation"},
}


def creer_compte(dossier, organisation=None, role="membre"):
    """Cree le Compte d'un Dossier - un seul Compte par Dossier (OneToOne)."""
    return Compte.objects.create(dossier=dossier, organisation=organisation, role=role)


def autoriser_action(compte, action_code):
    """
    Retourne True/False - ne declenche jamais l'action elle-meme, ne
    prend aucune decision metier. Un Compte inactif n'est jamais
    autorise pour rien, meme s'il porte le role administrateur.
    """
    if not compte.actif:
        return False

    actions_autorisees = PERMISSIONS_PAR_ROLE.get(compte.role, set())
    return action_code in actions_autorisees


def desactiver_compte(compte):
    """
    Desactive le Compte SANS jamais toucher au Dossier sous-jacent -
    la memoire (Dossier) et l'identite active (Compte) restent
    structurellement independantes.
    """
    compte.actif = False
    compte.save(update_fields=["actif"])
    return compte
