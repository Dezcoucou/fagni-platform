"""
Pattern Strategy du module simulateur - FAGNI Platform (FOS-213 v1.3).

Ouvert a l'extension (une nouvelle strategie par service futur), ferme
a la modification - aucune strategie existante ne change quand une
nouvelle est ajoutee (principe Open/Closed, coherent avec FOS-211 :
configuration plutot que branches conditionnelles empilees).

IMPORTANT (FOS-213 v1.2 section 8) : ce registre est une decision
purement technique, invisible du produit. Meme avec une CordonnerieStrategy
codee ici demain, l'ecran d'entree du client ne proposera "Cordonnerie"
que le jour ou ce service est reellement commercialise - la capacite
technique et la capacite commerciale restent deux choses distinctes.
"""
from abc import ABC, abstractmethod


class OffreNonDisponible(Exception):
    """Levee quand une offre est techniquement valide mais pas commercialement active."""
    pass


class SimulationStrategy(ABC):
    VERSION = "1.0"

    @abstractmethod
    def estimer(self, **params) -> dict:
        """Retourne {prix, version_parametre, strategy_version}."""
        raise NotImplementedError

    @abstractmethod
    def valider_params(self, **params) -> None:
        """Leve ValueError si les parametres ne correspondent pas au service."""
        raise NotImplementedError


class PressingStrategy(SimulationStrategy):
    """Seule strategie reelle aujourd'hui - pack/taille_sac (module abonnements)."""

    VERSION = "pressing-v1"

    def valider_params(self, **params):
        if params.get("taille_sac") not in ("S", "M"):
            raise ValueError("taille_sac invalide")
        if params.get("pack") not in ("essentiel", "confort"):
            raise ValueError("pack invalide")

    def estimer(self, **params):
        from abonnements.services import obtenir_prix_pack_avec_version
        self.valider_params(**params)
        prix, version = obtenir_prix_pack_avec_version(params["pack"], params["taille_sac"])
        return {"prix": prix, "version_parametre": version, "strategy_version": self.VERSION}


class SimulationEngine:
    """
    Point d'entree unique. Choisit la strategie via un registre explicite,
    jamais une chaine de if/elif sur le nom du service.
    """
    _REGISTRY = {
        "pressing": PressingStrategy,
        # "cordonnerie": CordonnerieStrategy,  # a activer le jour ou ce service existe reellement
    }

    @classmethod
    def get_strategy(cls, service: str) -> SimulationStrategy:
        strategy_cls = cls._REGISTRY.get(service)
        if strategy_cls is None:
            raise ValueError(f"Aucune strategie de simulation pour le service '{service}'.")
        return strategy_cls()
