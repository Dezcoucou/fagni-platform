from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("dossier_destinataire", "canal", "evenement_declencheur", "statut_envoi", "created_at")
    list_filter = ("canal", "statut_envoi")
