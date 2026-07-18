"""
API endpoints pour les Drivers - Data réelle (Lot 1, Sprint 12).
GET /api/driver/missions - Missions du livreur connecté
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role
from missions.models import Mission
from dossiers.models import Dossier
from orchestrateur.services import etat_execution


@api_view(['GET'])
@require_role("membre")
def api_driver_missions(request):
    """
    GET /api/driver/missions
    Missions du livreur connecté (vraies données).
    """
    try:
        # Récupère le Dossier du driver
        dossier = Dossier.objects.get(email=request.email)
        
        # Récupère ses missions
        missions = Mission.objects.filter(acteur_assigne=dossier)
        
        # Stats
        total = missions.count()
        en_cours = missions.filter(statut__in=['en_attente', 'collecte', 'en_traitement']).count()
        completees = missions.filter(statut='livree').count()
        
        # Format response
        missions_data = [
            {
                'id': m.id,
                'type': m.type_mission,
                'statut': m.statut,
                'commande_id': m.commande_id,
                'created': m.created_at.isoformat(),
            }
            for m in missions[:20]  # Limit 20
        ]
        
        return Response({
            "livreur_id": dossier.id,
            "email": dossier.email,
            "nom": dossier.nom,
            "role": request.role,
            "total_missions": total,
            "missions_en_cours": en_cours,
            "missions_completees": completees,
            "missions": missions_data,
        }, status=status.HTTP_200_OK)
    
    except Dossier.DoesNotExist:
        return Response(
            {"error": "Dossier non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as err:
        return Response(
            {"error": str(err)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@require_role("membre")
def api_driver_mission_workflow(request, mission_id):
    """
    GET /api/driver/missions/<mission_id>/workflow
    Etat d'avancement du workflow pour une mission du livreur connecte
    uniquement - jamais une mission assignee a un autre acteur.
    """
    try:
        dossier = Dossier.objects.get(email=request.email)
        mission = Mission.objects.select_related("commande", "workflow").get(
            id=mission_id, acteur_assigne=dossier,
        )
    except Dossier.DoesNotExist:
        return Response({"error": "Dossier non trouve"}, status=status.HTTP_404_NOT_FOUND)
    except Mission.DoesNotExist:
        return Response({"error": "Mission introuvable ou non assignee a ce livreur"}, status=status.HTTP_404_NOT_FOUND)

    etat = etat_execution(mission)
    if etat is None:
        return Response({"mission_id": mission.id, "workflow": None}, status=status.HTTP_200_OK)

    return Response({
        "mission_id": mission.id,
        "workflow": etat["workflow"].nom,
        "termine": etat["termine"],
        "etape_courante": etat["etape_courante"].type_evenement if etat["etape_courante"] else None,
        "prochaine_etape": etat["prochaine_etape"].type_evenement if etat["prochaine_etape"] else None,
    }, status=status.HTTP_200_OK)
