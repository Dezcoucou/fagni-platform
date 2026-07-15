from django.contrib import admin
from .models import Dossier, EntreeHistoriqueConfiance


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_acteur", "statut", "niveau_confiance", "date_ouverture")
    list_filter = ("type_acteur", "statut")
    search_fields = ("nom", "telephone")
    readonly_fields = ("date_ouverture", "updated_at")


@admin.register(EntreeHistoriqueConfiance)
class EntreeHistoriqueConfianceAdmin(admin.ModelAdmin):
    list_display = ("dossier", "ancien_niveau", "nouveau_niveau", "raison", "created_at")
    list_filter = ("dossier__type_acteur",)
    readonly_fields = ("created_at",)
