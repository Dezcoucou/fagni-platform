from django.contrib import admin
from .models import Commande, LigneCommande


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ("id", "dossier_client", "prix_engage", "created_at")
    list_filter = ("created_at",)
    search_fields = ("dossier_client__nom",)
    inlines = [LigneCommandeInline]


@admin.register(LigneCommande)
class LigneCommandeAdmin(admin.ModelAdmin):
    list_display = ("commande", "article", "service", "niveau_service", "quantite", "statut")
    list_filter = ("statut", "niveau_service")
