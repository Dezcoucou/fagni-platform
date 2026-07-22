"""
Machine d'etats du module simulateur - FAGNI Platform (FOS-213 v1.3).

transitionner() est le SEUL point d'entree legitime pour changer
Simulation.statut - meme convention que Commande.prix_engage (jamais
modifie hors de reviser_prix()) ou Evenement (immuable hors de
emettre_evenement()). Une affectation directe simulation.statut = "..."
ailleurs dans le code est une violation de cette regle.
"""

TRANSITIONS_AUTORISEES = {
    "en_cours": {"resultat_affiche"},
    "resultat_affiche": {"envoyee_whatsapp", "reservee", "expiree"},
    "envoyee_whatsapp": {"reservee", "expiree"},
    "reservee": {"commande_creee"},
    "commande_creee": set(),  # etat terminal
    "expiree": set(),         # etat terminal
}

STATUTS_EXPIRABLES = {"resultat_affiche", "envoyee_whatsapp"}
# FOS-213 v1.3, precision de la revue finale : l'expiration a 7 jours ne
# s'applique JAMAIS a une reservation deja realisee (reservee,
# commande_creee) - une reservation ancienne reste consultable dans son
# etat reel, ne genere jamais une nouvelle estimation.


class TransitionInterdite(Exception):
    """Levee quand une transition de statut hors du graphe autorise est tentee."""
    pass


def transitionner(simulation, nouveau_statut: str) -> None:
    """
    Change Simulation.statut apres verification stricte contre
    TRANSITIONS_AUTORISEES. Toute transition hors graphe leve
    explicitement, plutot que d'etre acceptee silencieusement.
    """
    autorise = TRANSITIONS_AUTORISEES.get(simulation.statut, set())
    if nouveau_statut not in autorise:
        raise TransitionInterdite(
            f"Transition '{simulation.statut}' -> '{nouveau_statut}' non autorisee. "
            f"Transitions valides depuis '{simulation.statut}' : "
            f"{autorise or 'aucune (etat terminal)'}."
        )
    simulation.statut = nouveau_statut
    simulation.save(update_fields=["statut", "updated_at"])
