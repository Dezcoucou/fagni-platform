from django.contrib import admin
from .models import AjustementCommande


@admin.register(AjustementCommande)
class AjustementCommandeAdmin(admin.ModelAdmin):
    list_display = ("commande", "type_ajustement", "quantite_declaree", "quantite_reelle", "montant_ajustement", "statut")
    list_filter = ("type_ajustement", "statut")
