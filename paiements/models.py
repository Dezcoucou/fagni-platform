"""
Module paiements - FAGNI Platform (Lot 1, Sprint 7)
Derive du BOS FAGNI 2035 v2.0 (chapitre 3, objets Paiement/Wallet) et de
FOS-211 v1.1 (section 2.5) et chapitre 11 (moteur economique).

Lecon retenue directement du pilote V1 : le garde-fou anti-fraude du
wallet (inspect.stack() sur les noms de fonction) etait fragile. Ici,
l'idempotence est garantie par une contrainte d'unicite en base sur
idempotency_key - mecanisme robuste, pas une convention de nommage.
"""
from django.db import models
from dossiers.models import Dossier
from commandes.models import Commande


class Wallet(models.Model):
    """Un Wallet par Dossier (BOS chapitre 3) - reserve de valeur propre a chaque acteur."""
    dossier = models.OneToOneField(
        Dossier, on_delete=models.PROTECT, related_name="wallet",
    )
    solde = models.DecimalField("Solde (FCFA)", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"Wallet de {self.dossier.nom} - {self.solde} FCFA"


class TransactionWallet(models.Model):
    """
    Chaque mouvement de Wallet. idempotency_key est UNIQUE en base -
    toute tentative de rejouer la meme operation est detectee au niveau
    de la contrainte, pas seulement par une verification applicative.
    """
    TYPE_CHOICES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="transactions",
    )
    type_transaction = models.CharField("Type", max_length=10, choices=TYPE_CHOICES)
    montant = models.DecimalField("Montant (FCFA)", max_digits=10, decimal_places=2)
    raison = models.CharField("Raison", max_length=255)
    idempotency_key = models.CharField(
        "Cle d'idempotence", max_length=255, unique=True,
        help_text="Garantit qu'une meme operation n'est jamais rejouee deux fois",
    )
    created_at = models.DateTimeField("Effectuee le", auto_now_add=True)

    class Meta:
        verbose_name = "Transaction Wallet"
        verbose_name_plural = "Transactions Wallet"
        ordering = ["-created_at"]

    def __str__(self):
        signe = "+" if self.type_transaction == "credit" else "-"
        return f"{self.wallet.dossier.nom} {signe}{self.montant} FCFA - {self.raison}"


class Paiement(models.Model):
    """Le mouvement d'argent effectif (BOS chapitre 3), distinct du prix engage sur la Commande."""
    MODE_CHOICES = [
        ("wave", "Wave"),
        ("wallet", "Wallet FAGNI"),
        ("especes", "Especes"),
    ]

    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("confirme", "Confirme"),
        ("echoue", "Echoue"),
    ]

    commande = models.ForeignKey(
        Commande, on_delete=models.PROTECT, related_name="paiements",
    )
    montant = models.DecimalField("Montant (FCFA)", max_digits=10, decimal_places=2)
    mode = models.CharField("Mode de paiement", max_length=20, choices=MODE_CHOICES)
    statut = models.CharField(
        "Statut", max_length=20, choices=STATUT_CHOICES, default="en_attente",
    )
    created_at = models.DateTimeField("Cree le", auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Paiement #{self.id} - Commande #{self.commande_id} - {self.montant} FCFA ({self.get_statut_display()})"
