from django.contrib import admin
from .models import Capacite


@admin.register(Capacite)
class CapaciteAdmin(admin.ModelAdmin):
    list_display = ("dossier", "service", "niveau_confiance_service", "volume_disponible", "active")
    list_filter = ("service", "active")
    search_fields = ("dossier__nom",)
