from django.contrib import admin
from .models import Devis


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ("id", "commande", "montant_propose", "propose_par", "statut", "created_at")
    list_filter = ("statut",)
