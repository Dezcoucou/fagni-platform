from django.contrib import admin
from .models import Organisation, Compte


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_organisation")
    list_filter = ("type_organisation",)


@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ("dossier", "organisation", "role", "actif")
    list_filter = ("role", "actif")
    exclude = ("mot_de_passe_hash",)
    readonly_fields = ("created_at",)
