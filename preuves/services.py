"""
Services internes du module preuves - FAGNI Platform (Lot 1, Sprint 5)

capturer_preuve() est le seul point d'entree legitime. Une Preuve doit
toujours etre rattachee a un Evenement precis - garantit que la preuve
n'existe jamais dans le vide, mais etaye toujours un fait date de la
chaine de tracabilite (FOS-210 section 9).
"""
from .models import Preuve


def capturer_preuve(type_preuve, mission, evenement, dossier_capturant,
                     fichier=None, contenu_texte="", metadonnees=None):
    """
    Capture une Preuve immuable, immediatement au moment de l'action -
    jamais reconstituee apres coup (BOS chapitre 3).
    """
    return Preuve.objects.create(
        type_preuve=type_preuve,
        mission=mission,
        evenement=evenement,
        dossier_capturant=dossier_capturant,
        fichier=fichier,
        contenu_texte=contenu_texte,
        metadonnees=metadonnees or {},
    )
