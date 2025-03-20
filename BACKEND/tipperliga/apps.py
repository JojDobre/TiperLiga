from django.apps import AppConfig


class TipperligaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tipperliga'

    def ready(self):
        import tipperliga.signals
