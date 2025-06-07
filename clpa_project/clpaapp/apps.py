from django.apps import AppConfig
import threading

class ClpaappConfig(AppConfig):
    name = 'clpaapp'

    def ready(self):
        from .views import start_reminder_checker
        threading.Thread(target=start_reminder_checker, daemon=True).start()
