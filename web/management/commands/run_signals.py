# web/management/commands/run_signals.py

from django.core.management.base import BaseCommand
import threading
import sys
import os

# Adding the project root to sys.path to import the signal file
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# from trade_signal import perform_trade_analysis  
# Import the main function for the script

class Command(BaseCommand):
    help = 'Runs the trading signals script'

    def handle(self, *args, **kwargs):
        # Start the signal script in a separate thread
        # thread = threading.Thread(target=perform_trade_analysis)
        # thread.start()
        self.stdout.write(self.style.SUCCESS('Script started.'))
