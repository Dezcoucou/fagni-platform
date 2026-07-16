from django.contrib import admin
from .models import Reclamation


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ("id", "commande", "statut", "favorable_au_client", "created_at")
    list_filter = ("statut", "favorable_au_client")
    filter_horizontal = ("dossiers_concernes",)
