# web/management/commands/run_signals.py

from django.core.management.base import BaseCommand
import threading
import sys
import os

# Añadimos la raíz del proyecto al sys.path para poder importar el archivo de señales
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trade_signal import perform_trade_analysis  # Importamos la función principal de tu script

class Command(BaseCommand):
    help = 'Ejecuta el script de señales de trading'

    def handle(self, *args, **kwargs):
        # Inicia el script de señales en un hilo separado
        thread = threading.Thread(target=perform_trade_analysis)
        thread.start()
        self.stdout.write(self.style.SUCCESS('El script de señales se ha iniciado correctamente.'))
