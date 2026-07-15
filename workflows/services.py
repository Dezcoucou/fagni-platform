"""
Services internes du module workflows - FAGNI Platform (Lot 1, Sprint 9)
"""
from django.db import transaction
from .models import Workflow, EtapeWorkflow


@transaction.atomic
def creer_workflow(nom, service_associe, etapes, description=""):
    """
    Cree un Workflow avec sa sequence d'etapes.

    etapes : liste ordonnee de dict {type_evenement, obligatoire}
    - l'ordre est deduit de la position dans la liste, jamais suppose
      par ailleurs.
    """
    if not etapes:
        raise ValueError("Un Workflow doit contenir au moins une etape.")

    workflow = Workflow.objects.create(
        nom=nom, description=description, service_associe=service_associe,
    )

    for i, etape in enumerate(etapes, start=1):
        EtapeWorkflow.objects.create(
            workflow=workflow,
            type_evenement=etape["type_evenement"],
            ordre=i,
            obligatoire=etape.get("obligatoire", True),
        )

    return workflow


def obtenir_sequence(workflow):
    """Retourne les etapes dans leur ordre exact - jamais un ordre suppose."""
    return list(workflow.etapes.order_by("ordre"))
