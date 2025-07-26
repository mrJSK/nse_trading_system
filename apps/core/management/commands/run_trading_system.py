from django.core.management.base import BaseCommand
from apps.core.tasks import master_trading_orchestrator

class Command(BaseCommand):
    help = 'Run the trading system orchestrator'

    def handle(self, *args, **options):
        self.stdout.write("Starting NSE Trading System...")
        result = master_trading_orchestrator.delay()
        self.stdout.write(f"Task started with ID: {result.id}")
