from django.contrib import admin
from .models import Mission


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("type_mission", "commande", "acteur_assigne", "statut", "created_at")
    list_filter = ("type_mission", "statut")
    search_fields = ("acteur_assigne__nom",)
