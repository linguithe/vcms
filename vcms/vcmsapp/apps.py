from django.apps import AppConfig
from vcmsapp.schedulers.sender import start

class VcmsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vcmsapp'

    def ready(self):
        from vcmsapp.blockchain import Blockchain
        start()
        Blockchain.load()