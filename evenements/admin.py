from django.contrib import admin
from .models import Evenement


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ("type_evenement", "acteur_origine", "horodatage")
    list_filter = ("type_evenement",)
    readonly_fields = [f.name for f in Evenement._meta.fields]
    filter_horizontal = ("dossiers_concernes",)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
