"""
API endpoints pour les Clients - Data réelle (Lot 1, Sprint 12).
GET /api/client/orders - Commandes du client connecté
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role
from commandes.models import Commande
from dossiers.models import Dossier


@api_view(['GET'])
@require_role("membre")
def api_client_orders(request):
    """
    GET /api/client/orders
    Commandes du client connecté (vraies données).
    """
    try:
        # Récupère le Dossier du client
        dossier = Dossier.objects.get(email=request.email)
        
        # Récupère ses commandes
        commandes = Commande.objects.filter(dossier_client=dossier)
        
        # Stats
        total = commandes.count()
        total_spent = sum(c.prix_engage for c in commandes)
        
        # Format response
        orders_data = [
            {
                'id': c.id,
                'prix': float(c.prix_engage),
                'delai': c.delai_annonce,
                'created': c.created_at.isoformat(),
                'lignes_count': c.lignes.count(),
            }
            for c in commandes[:20]
        ]
        
        return Response({
            "client_id": dossier.id,
            "email": dossier.email,
            "nom": dossier.nom,
            "role": request.role,
            "total_orders": total,
            "total_spent": float(total_spent),
            "orders": orders_data,
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
def api_client_order_workflow(request, commande_id):
    """
    GET /api/client/orders/<commande_id>/workflow
    Etat d'avancement du/des workflow(s) pour une commande du client
    connecte uniquement. Une commande peut avoir plusieurs Missions
    (FOS-211 section 2.2, statut par ligne) - chacune avec son propre
    etat de workflow trace.
    """
    from missions.models import Mission
    from orchestrateur.services import etat_execution

    try:
        dossier = Dossier.objects.get(email=request.email)
        commande = Commande.objects.get(id=commande_id, dossier_client=dossier)
    except Dossier.DoesNotExist:
        return Response({"error": "Dossier non trouve"}, status=status.HTTP_404_NOT_FOUND)
    except Commande.DoesNotExist:
        return Response({"error": "Commande introuvable ou non associee a ce client"}, status=status.HTTP_404_NOT_FOUND)

    missions = Mission.objects.filter(commande=commande).select_related("workflow")

    missions_data = []
    for mission in missions:
        etat = etat_execution(mission)
        missions_data.append({
            "mission_id": mission.id,
            "type_mission": mission.type_mission,
            "workflow": etat["workflow"].nom if etat else None,
            "termine": etat["termine"] if etat else None,
            "etape_courante": etat["etape_courante"].type_evenement if etat and etat["etape_courante"] else None,
            "prochaine_etape": etat["prochaine_etape"].type_evenement if etat and etat["prochaine_etape"] else None,
        })

    return Response({
        "commande_id": commande.id,
        "missions": missions_data,
    }, status=status.HTTP_200_OK)
