from django.contrib import admin
from .models import Simulation, EvenementSimulation


class EvenementSimulationInline(admin.TabularInline):
    model = EvenementSimulation
    extra = 0
    readonly_fields = ("type_evenement", "donnees", "horodatage")
    can_delete = False


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = ("sim_id", "zone_code", "pack", "taille_sac", "prix_calcule", "statut", "created_at")
    list_filter = ("statut", "zone_code", "pack", "service")
    search_fields = ("sim_id", "telephone", "nom")
    readonly_fields = ("sim_id", "resume_token", "created_at", "updated_at")
    inlines = [EvenementSimulationInline]


@admin.register(EvenementSimulation)
class EvenementSimulationAdmin(admin.ModelAdmin):
    list_display = ("simulation", "type_evenement", "horodatage")
    list_filter = ("type_evenement",)
    readonly_fields = ("horodatage",)
