from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import api.signals  # We'll create this later if needed
        except ImportError:
            pass