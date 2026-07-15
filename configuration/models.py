"""
Module configuration - FAGNI Platform (Lot 1, Sprint 11)
Derive de FOS-211 v1.1 (section 9.2, module configuration).

Principe central : chaque parametre garde un historique complet de ses
versions precedentes. Un changement de commission aujourd'hui ne doit
jamais effacer la valeur qui s'appliquait a une commande deja engagee
hier - coherent avec le prix verrouille du module commandes (BOS 4.1).
"""
from django.db import models


class Parametre(models.Model):
    """Un parametre nomme - la valeur elle-meme vit dans VersionParametre."""
    cle = models.CharField("Cle", max_length=100, unique=True)
    description = models.TextField("Description", blank=True, default="")

    class Meta:
        verbose_name = "Parametre"
        verbose_name_plural = "Parametres"

    def __str__(self):
        return self.cle


class VersionParametre(models.Model):
    """
    Une version de la valeur d'un Parametre, avec sa periode de validite.
    valide_jusqu_a=None signifie que cette version est la version courante.
    """
    parametre = models.ForeignKey(
        Parametre, on_delete=models.CASCADE, related_name="versions",
    )
    valeur = models.CharField("Valeur", max_length=255)
    valide_a_partir_de = models.DateTimeField("Valide a partir de", auto_now_add=True)
    valide_jusqu_a = models.DateTimeField(
        "Valide jusqu'a", null=True, blank=True,
        help_text="None = version courante, encore active",
    )

    class Meta:
        verbose_name = "Version de parametre"
        verbose_name_plural = "Versions de parametre"
        ordering = ["-valide_a_partir_de"]

    def __str__(self):
        etat = "courante" if self.valide_jusqu_a is None else "historique"
        return f"{self.parametre.cle} = {self.valeur} ({etat})"
