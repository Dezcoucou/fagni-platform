from django.contrib import admin
from .models import ReglaDecision, Decision


@admin.register(ReglaDecision)
class ReglaDecisionAdmin(admin.ModelAdmin):
    list_display = ("code", "toujours_humaine")
    list_filter = ("toujours_humaine",)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("regle", "niveau_applique", "decideur", "created_at")
    list_filter = ("niveau_applique",)
