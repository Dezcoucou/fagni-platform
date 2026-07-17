"""
Management command pour créer des Comptes de test.
Usage: python manage.py seed_test_comptes
"""
from django.core.management.base import BaseCommand
from dossiers.models import Dossier
from accounts.models import Compte


class Command(BaseCommand):
    help = "Crée des Comptes de test pour développement/démonstration"

    def handle(self, *args, **options):
        # Évite les doublons
        if Dossier.objects.filter(email="admin@fagni.test").exists():
            self.stdout.write("✓ Comptes de test existent déjà")
            return
        
        # Admin OPS
        dossier_admin = Dossier.objects.create(
            type_acteur="ops",
            nom="Admin OPS",
            telephone="225 01 42 29 99 49",
            email="admin@fagni.test",
        )
        compte_admin = Compte.objects.create(
            dossier=dossier_admin,
            role="administrateur",
            actif=True,
        )
        compte_admin.definir_mot_de_passe("fagni2025")
        self.stdout.write(f"✅ Admin créé: admin@fagni.test")
        
        # Driver test
        dossier_driver = Dossier.objects.create(
            type_acteur="livreur",
            nom="Youande Bonao",
            telephone="225 01 23 45 67",
            email="driver@fagni.test",
        )
        compte_driver = Compte.objects.create(
            dossier=dossier_driver,
            role="membre",
            actif=True,
        )
        compte_driver.definir_mot_de_passe("driver2025")
        self.stdout.write(f"✅ Driver créé: driver@fagni.test")
        
        self.stdout.write("✅ Seed complet")
