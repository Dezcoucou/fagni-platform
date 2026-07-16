from django.contrib import admin
from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "pourcentage_reduction", "usage_actuel", "usage_max", "actif")
    list_filter = ("actif", "premiere_commande_uniquement")


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ("coupon", "dossier_client", "commande", "montant_reduction", "created_at")
