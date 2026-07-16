from django.contrib import admin
from .models import Wallet, TransactionWallet, Paiement


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("dossier", "solde")
    search_fields = ("dossier__nom",)


@admin.register(TransactionWallet)
class TransactionWalletAdmin(admin.ModelAdmin):
    list_display = ("wallet", "type_transaction", "montant", "raison", "created_at")
    list_filter = ("type_transaction",)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("id", "commande", "montant", "mode", "statut", "created_at")
    list_filter = ("mode", "statut")
