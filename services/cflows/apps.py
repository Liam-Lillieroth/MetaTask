from django.apps import AppConfig


class CflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.cflows'
    
    def ready(self):
        import services.cflows.signals
