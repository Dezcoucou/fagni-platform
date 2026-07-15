"""
Vues du module dossiers - FAGNI Platform (Lot 1, Sprint 1)

ReadOnlyModelViewSet uniquement : aucune ecriture n'est exposee via l'API
(FOS-211 section 5.3). La creation et la modification passent exclusivement
par services.py, appelees par d'autres modules internes - jamais par une
requete HTTP externe directe.
"""
from rest_framework import viewsets, permissions
from .models import Dossier
from .serializers import DossierSerializer


class DossierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/dossiers/       - liste (usage interne/OPS pour l'instant,
                                 sera restreint par le module accounts)
    GET /api/dossiers/{id}/  - consultation d'un Dossier precis
    """
    queryset = Dossier.objects.all()
    serializer_class = DossierSerializer
    permission_classes = [permissions.AllowAny]  # TODO: restreindre via module accounts (FOS-211 section 9.1)
    filterset_fields = ["type_acteur", "statut"]
