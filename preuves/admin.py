from django.contrib import admin
from .models import Preuve


@admin.register(Preuve)
class PreuveAdmin(admin.ModelAdmin):
    list_display = ("type_preuve", "mission", "dossier_capturant", "horodatage")
    list_filter = ("type_preuve",)
    readonly_fields = [f.name for f in Preuve._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
