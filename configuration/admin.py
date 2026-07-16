from django.contrib import admin
from .models import Parametre, VersionParametre


class VersionParametreInline(admin.TabularInline):
    model = VersionParametre
    extra = 0
    readonly_fields = ("valide_a_partir_de",)


@admin.register(Parametre)
class ParametreAdmin(admin.ModelAdmin):
    list_display = ("cle", "description")
    inlines = [VersionParametreInline]
