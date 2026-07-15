"""
Services internes du module decisions - FAGNI Platform (Lot 1, Sprint 10)

evaluer_niveau_decision() applique la logique exacte du BOS chapitre 12.3 :
trois conditions rendent une decision automatisable, MAIS toujours_humaine
sur la ReglaDecision l'emporte inconditionnellement (chapitre 7.2) -
verifiee EN PREMIER, avant meme d'examiner les conditions.
"""
from .models import ReglaDecision, Decision


class DecideurManquant(Exception):
    """Leve quand une decision humaine est enregistree sans decideur identifie."""
    pass


def evaluer_niveau_decision(regle, regle_connue, preuve_disponible, reversible):
    """
    Retourne 'automatique', 'assistee' ou 'humaine' selon le BOS 12.3.

    Ordre de verification strict :
    1. Si regle.toujours_humaine -> 'humaine', point final, sans exception.
    2. Sinon, les trois conditions doivent TOUTES etre reunies pour 'automatique'.
    3. L'absence d'une seule condition -> 'assistee' (jamais 'automatique').
    """
    if regle.toujours_humaine:
        return "humaine"

    if regle_connue and preuve_disponible and reversible:
        return "automatique"

    return "assistee"


def enregistrer_decision(regle_code, niveau_applique, decideur=None, objet_source=None, justification=""):
    """
    Enregistre une Decision. Refuse explicitement une decision 'humaine'
    sans decideur identifie (BOS chapitre 7.2 - jamais un seuil automatique
    aveugle se faisant passer pour une decision humaine).
    """
    regle = ReglaDecision.objects.get(code=regle_code)

    if niveau_applique == "humaine" and not decideur:
        raise DecideurManquant(
            f"La regle '{regle_code}' exige une decision humaine identifiee "
            f"(BOS chapitre 7.2) - decideur ne peut pas etre absent."
        )

    return Decision.objects.create(
        regle=regle,
        niveau_applique=niveau_applique,
        decideur=decideur,
        objet_source=objet_source,
        justification=justification,
    )
