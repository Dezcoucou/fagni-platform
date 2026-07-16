from django.contrib import admin
from .models import Parrainage


@admin.register(Parrainage)
class ParrainageAdmin(admin.ModelAdmin):
    list_display = ("parrain", "filleul", "montant_credit", "statut", "eligible_a_partir_de", "created_at")
    list_filter = ("statut",)
    search_fields = ("parrain__nom", "filleul__nom")
