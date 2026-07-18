from django.apps import AppConfig


class OrchestrateurConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orchestrateur'

    def ready(self):
        import orchestrateur.signals  # noqa: F401 - enregistre le signal post_save sur Evenement
