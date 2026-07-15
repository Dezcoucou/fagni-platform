"""
Serializers du module dossiers - FAGNI Platform (Lot 1, Sprint 1)
"""
from rest_framework import serializers
from .models import Dossier, EntreeHistoriqueConfiance


class EntreeHistoriqueConfianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntreeHistoriqueConfiance
        fields = ["id", "ancien_niveau", "nouveau_niveau", "raison", "created_at"]
        read_only_fields = fields


class DossierSerializer(serializers.ModelSerializer):
    """
    Serializer expose publiquement (FOS-211 section 4.2 : "Consultation du
    Dossier propre"). Tous les champs sont en lecture seule ici - aucune
    modification n'est jamais possible via cette API, conformement a la
    regle FOS-211 section 5.3 : seuls les services internes ecrivent.
    """
    type_acteur_display = serializers.CharField(source="get_type_acteur_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = Dossier
        fields = [
            "id", "type_acteur", "type_acteur_display", "nom", "telephone",
            "statut", "statut_display", "niveau_confiance",
            "date_ouverture", "updated_at",
        ]
        read_only_fields = fields
