"""
API endpoints pour les Partners - Data réelle (Lot 1, Sprint 12).
GET /api/partner/orders - Commandes assignées au partenaire
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role
from commandes.models import Commande
from dossiers.models import Dossier
from django.db.models import Q


@api_view(['GET'])
@require_role("membre")
def api_partner_orders(request):
    """
    GET /api/partner/orders
    Commandes avec missions assignées au partenaire (vraies données).
    """
    try:
        # Récupère le Dossier du partenaire
        dossier = Dossier.objects.get(email=request.email)
        
        # Récupère les commandes qui ont des missions assignées à ce partenaire
        commandes = Commande.objects.filter(
            missions__acteur_assigne=dossier
        ).distinct()
        
        # Stats
        total = commandes.count()
        total_revenue = sum(c.prix_engage for c in commandes)
        
        # Format response
        orders_data = [
            {
                'id': c.id,
                'prix': float(c.prix_engage),
                'client': c.dossier_client.nom,
                'created': c.created_at.isoformat(),
                'missions_count': c.missions.filter(acteur_assigne=dossier).count(),
            }
            for c in commandes[:20]
        ]
        
        return Response({
            "partenaire_id": dossier.id,
            "email": dossier.email,
            "nom": dossier.nom,
            "role": request.role,
            "total_orders": total,
            "revenus_total": float(total_revenue),
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
